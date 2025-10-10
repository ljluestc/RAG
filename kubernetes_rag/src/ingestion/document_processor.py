"""Document processing and chunking for Kubernetes documentation."""

import re
from typing import List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import markdown
from bs4 import BeautifulSoup


@dataclass
class Document:
    """Represents a processed document chunk."""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str


class MarkdownProcessor:
    """Process and parse markdown files."""

    def __init__(self):
        self.md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc'])

    def extract_sections(self, markdown_text: str) -> List[Dict[str, str]]:
        """Extract sections from markdown based on headers."""
        sections = []
        current_section = {"title": "", "content": "", "level": 0}

        lines = markdown_text.split('\n')
        for line in lines:
            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                # Save previous section if it has content
                if current_section["content"].strip():
                    sections.append(current_section.copy())

                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    "title": title,
                    "content": "",
                    "level": level
                }
            else:
                current_section["content"] += line + '\n'

        # Add last section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown."""
        code_blocks = []
        pattern = r'```(\w+)?\n(.*?)```'

        for match in re.finditer(pattern, text, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            code_blocks.append({
                "language": language,
                "code": code
            })

        return code_blocks

    def parse_qa_pairs(self, markdown_text: str) -> List[Dict[str, str]]:
        """Extract question-answer pairs from the markdown."""
        qa_pairs = []

        # Pattern to match <summary> and content within <details>
        pattern = r'<details>\s*<summary>(.*?)</summary><br><b>\s*(.*?)\s*</b></details>'

        for match in re.finditer(pattern, markdown_text, re.DOTALL):
            question = match.group(1).strip()
            answer = match.group(2).strip()

            # Clean up the answer
            answer = re.sub(r'<[^>]+>', '', answer)  # Remove HTML tags
            answer = re.sub(r'\s+', ' ', answer).strip()  # Normalize whitespace

            qa_pairs.append({
                "question": question,
                "answer": answer
            })

        return qa_pairs


class DocumentChunker:
    """Chunk documents intelligently for RAG."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """Chunk text into smaller pieces with overlap."""
        if metadata is None:
            metadata = {}

        chunks = []
        current_chunk = ""
        sentences = self._split_text(text)

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + sentence

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Create Document objects
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy()
            doc_metadata['chunk_index'] = i
            doc_metadata['total_chunks'] = len(chunks)

            documents.append(Document(
                content=chunk,
                metadata=doc_metadata,
                chunk_id=f"{metadata.get('source', 'unknown')}_{i}"
            ))

        return documents

    def _split_text(self, text: str) -> List[str]:
        """Split text using the defined separators."""
        for separator in self.separators:
            if separator in text:
                parts = text.split(separator)
                return [p + separator for p in parts if p]

        return [text]

    def _get_overlap(self, text: str) -> str:
        """Get the overlap portion from the end of text."""
        if len(text) <= self.chunk_overlap:
            return text

        # Try to find a good breaking point
        overlap = text[-self.chunk_overlap:]
        for separator in self.separators:
            if separator in overlap:
                parts = overlap.split(separator)
                return separator.join(parts[1:])

        return overlap

    def chunk_by_section(
        self,
        sections: List[Dict[str, str]],
        metadata: Dict[str, Any] = None
    ) -> List[Document]:
        """Chunk by maintaining section boundaries when possible."""
        if metadata is None:
            metadata = {}

        documents = []

        for section in sections:
            section_text = f"# {section['title']}\n\n{section['content']}"

            # If section is small enough, keep it as one chunk
            if len(section_text) <= self.chunk_size:
                doc_metadata = metadata.copy()
                doc_metadata['section_title'] = section['title']
                doc_metadata['section_level'] = section['level']

                documents.append(Document(
                    content=section_text,
                    metadata=doc_metadata,
                    chunk_id=f"{metadata.get('source', 'unknown')}_{section['title']}"
                ))
            else:
                # Chunk large sections
                section_metadata = metadata.copy()
                section_metadata['section_title'] = section['title']
                section_metadata['section_level'] = section['level']

                chunked_docs = self.chunk_text(section_text, section_metadata)
                documents.extend(chunked_docs)

        return documents


class KubernetesDocProcessor:
    """Specialized processor for Kubernetes documentation."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.md_processor = MarkdownProcessor()
        self.chunker = DocumentChunker(chunk_size, chunk_overlap)

    def process_file(self, file_path: Path) -> List[Document]:
        """Process a Kubernetes documentation file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        metadata = {
            'source': str(file_path),
            'filename': file_path.name,
            'type': 'kubernetes_doc'
        }

        # Extract Q&A pairs
        qa_pairs = self.md_processor.parse_qa_pairs(content)

        # Extract sections
        sections = self.md_processor.extract_sections(content)

        documents = []

        # Process Q&A pairs as individual documents
        for i, qa in enumerate(qa_pairs):
            qa_metadata = metadata.copy()
            qa_metadata['type'] = 'qa_pair'
            qa_metadata['question'] = qa['question']

            qa_text = f"Question: {qa['question']}\n\nAnswer: {qa['answer']}"

            documents.append(Document(
                content=qa_text,
                metadata=qa_metadata,
                chunk_id=f"{file_path.stem}_qa_{i}"
            ))

        # Process sections
        section_docs = self.chunker.chunk_by_section(sections, metadata)
        documents.extend(section_docs)

        return documents

    def process_directory(self, directory: Path) -> List[Document]:
        """Process all markdown files in a directory."""
        all_documents = []

        for md_file in directory.rglob("*.md"):
            try:
                docs = self.process_file(md_file)
                all_documents.extend(docs)
            except Exception as e:
                print(f"Error processing {md_file}: {e}")

        return all_documents
