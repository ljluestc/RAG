"""Simple working test suite for ingestion module."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.ingestion.document_processor import (
    Document,
    MarkdownProcessor,
    DocumentChunker,
    KubernetesDocProcessor
)
from src.ingestion.embeddings import EmbeddingGenerator
from src.ingestion.pipeline import IngestionPipeline


class TestDocument:
    """Test Document dataclass."""

    def test_document_creation(self):
        """Test Document creation."""
        doc = Document(
            content="Test content",
            metadata={"source": "test.md"},
            chunk_id="chunk_1"
        )
        assert doc.content == "Test content"
        assert doc.metadata == {"source": "test.md"}
        assert doc.chunk_id == "chunk_1"


class TestMarkdownProcessor:
    """Test MarkdownProcessor class."""

    def test_markdown_processor_init(self):
        """Test MarkdownProcessor initialization."""
        processor = MarkdownProcessor()
        assert processor is not None

    def test_markdown_processor_extract_sections(self):
        """Test MarkdownProcessor extract_sections method."""
        processor = MarkdownProcessor()
        content = """# Title

## Subtitle

Content here.

### Another subtitle

More content.
"""
        sections = processor.extract_sections(content)
        
        assert isinstance(sections, list)
        assert len(sections) >= 2
        assert sections[0]["title"] == "Subtitle"
        assert sections[1]["title"] == "Another subtitle"

    def test_markdown_processor_extract_code_blocks(self):
        """Test MarkdownProcessor extract_code_blocks method."""
        processor = MarkdownProcessor()
        content = """# Code Example

```python
def hello():
    print("world")
```

More text.

```bash
echo "test"
```
"""
        code_blocks = processor.extract_code_blocks(content)
        
        assert isinstance(code_blocks, list)
        assert len(code_blocks) >= 2
        assert "python" in code_blocks[0]["language"]
        assert "def hello():" in code_blocks[0]["code"]

    def test_markdown_processor_parse_qa_pairs(self):
        """Test MarkdownProcessor parse_qa_pairs method."""
        processor = MarkdownProcessor()
        content = """# FAQ

**Q: What is Kubernetes?**
A: Kubernetes is a container orchestration platform.

**Q: How do I create a pod?**
A: Use kubectl create pod command.
"""
        qa_pairs = processor.parse_qa_pairs(content)
        
        assert isinstance(qa_pairs, list)
        assert len(qa_pairs) >= 2
        assert "What is Kubernetes?" in qa_pairs[0]["question"]
        assert "container orchestration" in qa_pairs[0]["answer"]


class TestDocumentChunker:
    """Test DocumentChunker class."""

    def test_document_chunker_init_default(self):
        """Test DocumentChunker initialization with defaults."""
        chunker = DocumentChunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200

    def test_document_chunker_init_custom(self):
        """Test DocumentChunker initialization with custom parameters."""
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100

    def test_document_chunker_chunk_text(self):
        """Test DocumentChunker chunk_text method."""
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
        content = "This is a test sentence. " * 10  # Create text longer than chunk_size
        metadata = {"source": "test.txt"}
        
        documents = chunker.chunk_text(content, metadata)
        
        assert isinstance(documents, list)
        assert len(documents) > 1  # Should be chunked
        assert all(isinstance(doc, Document) for doc in documents)
        # Check that metadata includes additional fields
        for doc in documents:
            assert "source" in doc.metadata
            assert "chunk_index" in doc.metadata
            assert "total_chunks" in doc.metadata

    def test_document_chunker_chunk_text_short(self):
        """Test DocumentChunker with short text."""
        chunker = DocumentChunker()
        content = "Short text"
        metadata = {"source": "short.txt"}
        
        documents = chunker.chunk_text(content, metadata)
        
        assert isinstance(documents, list)
        assert len(documents) == 1
        assert documents[0].content == content
        assert documents[0].metadata["source"] == "short.txt"
        assert documents[0].metadata["chunk_index"] == 0
        assert documents[0].metadata["total_chunks"] == 1

    def test_document_chunker_chunk_by_section(self):
        """Test DocumentChunker chunk_by_section method."""
        chunker = DocumentChunker()
        sections = [
            {"title": "Section 1", "content": "Content 1", "level": 1},
            {"title": "Section 2", "content": "Content 2", "level": 2}
        ]
        metadata = {"source": "sections.md"}
        
        documents = chunker.chunk_by_section(sections, metadata)
        
        assert isinstance(documents, list)
        assert len(documents) == 2
        assert all(isinstance(doc, Document) for doc in documents)
        # Check that content includes the section title
        assert "Section 1" in documents[0].content
        assert "Content 1" in documents[0].content


class TestKubernetesDocProcessor:
    """Test KubernetesDocProcessor class."""

    def test_kubernetes_doc_processor_init_default(self):
        """Test KubernetesDocProcessor initialization with defaults."""
        processor = KubernetesDocProcessor()
        assert processor is not None
        assert processor.chunker is not None
        assert processor.md_processor is not None

    def test_kubernetes_doc_processor_init_custom(self):
        """Test KubernetesDocProcessor initialization with custom parameters."""
        processor = KubernetesDocProcessor(chunk_size=500, chunk_overlap=100)
        assert processor.chunker.chunk_size == 500
        assert processor.chunker.chunk_overlap == 100

    def test_kubernetes_doc_processor_process_file_markdown(self):
        """Test processing a markdown file."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""# Test Document

This is a test markdown document.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
""")
            temp_path = f.name
        
        try:
            documents = processor.process_file(Path(temp_path))
            
            assert isinstance(documents, list)
            assert len(documents) > 0
            
            for doc in documents:
                assert isinstance(doc, Document)
                assert doc.content
                assert doc.metadata
                assert doc.chunk_id
                assert doc.metadata["source"] == temp_path
        finally:
            os.unlink(temp_path)

    def test_kubernetes_doc_processor_process_file_text(self):
        """Test processing a text file."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is plain text content for testing.")
            temp_path = f.name
        
        try:
            documents = processor.process_file(Path(temp_path))
            
            assert isinstance(documents, list)
            assert len(documents) > 0
            
            for doc in documents:
                assert isinstance(doc, Document)
                assert doc.content
                assert doc.metadata
                assert doc.chunk_id
        finally:
            os.unlink(temp_path)

    def test_kubernetes_doc_processor_process_file_nonexistent(self):
        """Test processing a non-existent file."""
        processor = KubernetesDocProcessor()
        
        with pytest.raises(FileNotFoundError):
            processor.process_file(Path("nonexistent_file.md"))

    def test_kubernetes_doc_processor_process_directory(self):
        """Test processing a directory."""
        processor = KubernetesDocProcessor()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "doc1.md").write_text("# Document 1\n\nContent 1")
            (temp_path / "doc2.txt").write_text("Document 2 content")
            
            documents = processor.process_directory(temp_path)
            
            assert isinstance(documents, list)
            assert len(documents) >= 2


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_init_default(self, mock_transformer):
        """Test EmbeddingGenerator initialization with defaults."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator()
        
        assert generator.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert generator.device == "cpu"  # Default device is cpu
        mock_transformer.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_init_custom(self, mock_transformer):
        """Test EmbeddingGenerator initialization with custom parameters."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator(
            model_name="sentence-transformers/all-MiniLM-L6-v2",  # Use real model name
            device="cuda"
        )
        
        assert generator.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert generator.device == "cuda"
        mock_transformer.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2", device="cuda")

    def test_embedding_generator_encode_single_text(self):
        """Test encoding single text."""
        generator = EmbeddingGenerator()
        result = generator.encode("Test text")
        
        assert result.shape[0] == 1  # One text
        assert result.shape[1] == 384  # Standard embedding dimension

    def test_embedding_generator_encode_multiple_texts(self):
        """Test encoding multiple texts."""
        generator = EmbeddingGenerator()
        texts = ["Text 1", "Text 2"]
        result = generator.encode(texts)
        
        assert result.shape[0] == 2  # Two texts
        assert result.shape[1] == 384  # Standard embedding dimension

    def test_embedding_generator_encode_with_parameters(self):
        """Test encoding with custom parameters."""
        generator = EmbeddingGenerator()
        result = generator.encode(
            "Test text",
            batch_size=16,
            show_progress=False,
            normalize=True
        )
        
        assert result.shape[0] == 1
        assert result.shape[1] == 384

    def test_embedding_generator_encode_empty_list(self):
        """Test encoding empty list."""
        generator = EmbeddingGenerator()
        result = generator.encode([])
        
        assert len(result) == 0


class TestIngestionPipeline:
    """Test IngestionPipeline class."""

    def test_ingestion_pipeline_init(self):
        """Test IngestionPipeline initialization."""
        mock_vector_store = Mock()
        mock_embedding_generator = Mock()
        mock_doc_processor = Mock()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        assert pipeline.vector_store == mock_vector_store
        assert pipeline.embedding_generator == mock_embedding_generator
        assert pipeline.doc_processor == mock_doc_processor

    def test_ingestion_pipeline_ingest_file(self):
        """Test ingesting a single file."""
        mock_vector_store = Mock()
        mock_embedding_generator = Mock()
        mock_embedding_generator.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_doc_processor = Mock()
        mock_doc_processor.process_file.return_value = [
            Document(content="Test content", metadata={"source": "test.md"}, chunk_id="chunk_1")
        ]
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test\n\nContent")
            temp_path = f.name
        
        try:
            result = pipeline.ingest_file(Path(temp_path))
            
            # ingest_file returns an integer (number of chunks)
            assert isinstance(result, int)
            assert result == 1
            
            mock_doc_processor.process_file.assert_called_once()
            mock_embedding_generator.encode.assert_called_once()
            mock_vector_store.add_documents.assert_called_once()
        finally:
            os.unlink(temp_path)

    def test_ingestion_pipeline_ingest_directory(self):
        """Test ingesting a directory."""
        mock_vector_store = Mock()
        mock_embedding_generator = Mock()
        mock_embedding_generator.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_doc_processor = Mock()
        mock_doc_processor.process_file.return_value = [
            Document(content="Test content", metadata={"source": "test.md"}, chunk_id="chunk_1")
        ]
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test1.md").write_text("# Test 1\n\nContent 1")
            (temp_path / "test2.txt").write_text("Test 2 content")
            
            result = pipeline.ingest_directory(temp_path, "*.md")
            
            # ingest_directory returns a dictionary with stats
            assert isinstance(result, dict)
            assert "total_files" in result
            assert "processed_files" in result
            assert "total_chunks" in result
            assert "failed_files" in result
            assert result["total_files"] >= 1  # Should find at least 1 .md file


class TestIngestionIntegration:
    """Test integration scenarios for ingestion module."""

    def test_full_ingestion_workflow(self):
        """Test full ingestion workflow."""
        mock_vector_store = Mock()
        mock_embedding_generator = Mock()
        mock_embedding_generator.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_doc_processor = Mock()
        mock_doc_processor.process_file.return_value = [
            Document(content="Test content 1", metadata={"source": "test1.md"}, chunk_id="chunk_1"),
            Document(content="Test content 2", metadata={"source": "test1.md"}, chunk_id="chunk_2")
        ]
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "doc1.md").write_text("# Document 1\n\nContent 1")
            (temp_path / "doc2.txt").write_text("Document 2 content")
            
            # Ingest directory
            result = pipeline.ingest_directory(temp_path)
            
            assert isinstance(result, dict)
            assert result["total_files"] >= 2
            assert result["processed_files"] >= 2
            assert result["total_chunks"] >= 4  # 2 chunks per file
            
            # Verify mocks were called
            assert mock_doc_processor.process_file.call_count >= 2
            assert mock_embedding_generator.encode.call_count >= 2
            assert mock_vector_store.add_documents.call_count >= 2

    def test_document_processor_with_different_file_types(self):
        """Test document processor with different file types."""
        processor = KubernetesDocProcessor()
        
        # Test markdown
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Markdown\n\nContent")
            md_path = f.name
        
        # Test text
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Plain text content")
            txt_path = f.name
        
        try:
            # Process markdown
            md_docs = processor.process_file(Path(md_path))
            assert len(md_docs) > 0
            assert md_docs[0].metadata["source"] == md_path
            
            # Process text
            txt_docs = processor.process_file(Path(txt_path))
            assert len(txt_docs) > 0
            assert txt_docs[0].metadata["source"] == txt_path
        finally:
            os.unlink(md_path)
            os.unlink(txt_path)

    def test_embedding_generator_with_different_texts(self):
        """Test embedding generator with different text types."""
        generator = EmbeddingGenerator()
        
        # Test single text
        result1 = generator.encode("Single text")
        assert result1.shape == (1, 384)
        
        # Test multiple texts
        result2 = generator.encode(["Text 1", "Text 2"])
        assert result2.shape == (2, 384)
        
        # Test empty list
        result3 = generator.encode([])
        assert len(result3) == 0


class TestIngestionPerformance:
    """Test performance scenarios for ingestion module."""

    def test_document_processor_performance(self):
        """Test document processor performance with large content."""
        processor = KubernetesDocProcessor(chunk_size=500, chunk_overlap=100)
        
        # Create large content
        large_content = "# Large Document\n\n" + "This is a test sentence. " * 1000
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(large_content)
            temp_path = f.name
        
        try:
            import time
            start_time = time.time()
            
            documents = processor.process_file(Path(temp_path))
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert duration < 2.0  # Should complete in reasonable time
            assert len(documents) > 1  # Should be chunked
        finally:
            os.unlink(temp_path)

    def test_embedding_generator_performance(self):
        """Test embedding generator performance."""
        generator = EmbeddingGenerator()
        
        # Test with many texts
        texts = [f"Text {i}" for i in range(10)]  # Reduced from 100 for faster testing
        
        import time
        start_time = time.time()
        
        result = generator.encode(texts)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 2.0  # Should complete in reasonable time
        assert result.shape == (10, 384)
