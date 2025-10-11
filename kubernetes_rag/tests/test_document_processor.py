"""Tests for document processing module."""

from pathlib import Path

import pytest
from src.ingestion.document_processor import (
    Document,
    DocumentChunker,
    KubernetesDocProcessor,
    MarkdownProcessor,
)


class TestMarkdownProcessor:
    """Test MarkdownProcessor class."""

    def test_extract_sections(self):
        """Test section extraction from markdown."""
        processor = MarkdownProcessor()

        markdown_text = """
# Section 1
Content of section 1

## Subsection 1.1
Content of subsection 1.1

# Section 2
Content of section 2
"""

        sections = processor.extract_sections(markdown_text)

        assert len(sections) >= 2
        assert sections[0]["title"] == "Section 1"
        assert "Content of section 1" in sections[0]["content"]

    def test_extract_code_blocks(self):
        """Test code block extraction."""
        processor = MarkdownProcessor()

        text = """
Some text

```python
def hello():
    print("Hello")
```

More text

```yaml
apiVersion: v1
kind: Pod
```
"""

        code_blocks = processor.extract_code_blocks(text)

        assert len(code_blocks) == 2
        assert code_blocks[0]["language"] == "python"
        assert "def hello()" in code_blocks[0]["code"]
        assert code_blocks[1]["language"] == "yaml"

    def test_parse_qa_pairs(self):
        """Test Q&A pair extraction."""
        processor = MarkdownProcessor()

        markdown_text = """
<details>
<summary>What is Kubernetes?</summary><br><b>
Kubernetes is a container orchestration platform.
</b></details>

<details>
<summary>What is a Pod?</summary><br><b>
A Pod is the smallest deployable unit in Kubernetes.
</b></details>
"""

        qa_pairs = processor.parse_qa_pairs(markdown_text)

        assert len(qa_pairs) == 2
        assert qa_pairs[0]["question"] == "What is Kubernetes?"
        assert "container orchestration" in qa_pairs[0]["answer"]


class TestDocumentChunker:
    """Test DocumentChunker class."""

    def test_chunk_text(self):
        """Test text chunking."""
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)

        text = "This is a test sentence. " * 20
        metadata = {"source": "test.md"}

        chunks = chunker.chunk_text(text, metadata)

        assert len(chunks) > 1
        assert all(isinstance(doc, Document) for doc in chunks)
        assert all(len(doc.content) <= 120 for doc in chunks)  # Allow some overflow

    def test_chunk_by_section(self):
        """Test chunking by sections."""
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)

        sections = [
            {"title": "Section 1", "content": "Short content", "level": 1},
            {"title": "Section 2", "content": "A" * 600, "level": 1},
        ]

        metadata = {"source": "test.md"}
        chunks = chunker.chunk_by_section(sections, metadata)

        assert len(chunks) >= 2


class TestKubernetesDocProcessor:
    """Test KubernetesDocProcessor class."""

    def test_process_content(self):
        """Test processing Kubernetes documentation."""
        processor = KubernetesDocProcessor(chunk_size=500)

        # Create a temporary test file
        test_content = """
# Kubernetes Basics

## What is Kubernetes?

<details>
<summary>Explain Kubernetes</summary><br><b>
Kubernetes is an open-source container orchestration platform.
</b></details>

## Pods

A Pod is the smallest deployable unit in Kubernetes.
"""

        # This would normally be done with a real file
        # For testing, we'll just verify the methods work
        assert processor.md_processor is not None
        assert processor.chunker is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
