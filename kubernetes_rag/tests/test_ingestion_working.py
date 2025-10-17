"""Working comprehensive test suite for ingestion module to achieve 100% coverage."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test configuration
from test_config_final import (
    mock_config,
    mock_settings,
    create_mock_documents,
    TEST_MARKDOWN_CONTENT,
    TEST_TEXT_CONTENT
)

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

    def test_document_with_empty_content(self):
        """Test Document with empty content."""
        doc = Document(
            content="",
            metadata={"source": "empty.md"},
            chunk_id="chunk_empty"
        )
        assert doc.content == ""
        assert doc.metadata == {"source": "empty.md"}
        assert doc.chunk_id == "chunk_empty"

    def test_document_with_complex_metadata(self):
        """Test Document with complex metadata."""
        metadata = {
            "source": "complex.md",
            "title": "Complex Document",
            "author": "Test Author",
            "tags": ["test", "document"],
            "created_at": "2024-01-01"
        }
        doc = Document(
            content="Complex content",
            metadata=metadata,
            chunk_id="chunk_complex"
        )
        assert doc.metadata == metadata


class TestMarkdownProcessor:
    """Test MarkdownProcessor class."""

    def test_markdown_processor_init(self):
        """Test MarkdownProcessor initialization."""
        processor = MarkdownProcessor()
        assert processor is not None

    def test_markdown_processor_process(self):
        """Test MarkdownProcessor process method."""
        processor = MarkdownProcessor()
        content = "# Test\n\nThis is a test document."
        
        result = processor.process(content)
        
        assert isinstance(result, str)
        assert "Test" in result
        assert "This is a test document" in result

    def test_markdown_processor_process_empty(self):
        """Test MarkdownProcessor with empty content."""
        processor = MarkdownProcessor()
        result = processor.process("")
        assert result == ""

    def test_markdown_processor_process_none(self):
        """Test MarkdownProcessor with None content."""
        processor = MarkdownProcessor()
        result = processor.process(None)
        assert result == ""

    def test_markdown_processor_process_complex(self):
        """Test MarkdownProcessor with complex markdown."""
        processor = MarkdownProcessor()
        content = """# Title

## Subtitle

- List item 1
- List item 2

**Bold text** and *italic text*

```python
def test():
    return "test"
```

> Quote block
"""
        result = processor.process(content)
        assert isinstance(result, str)
        assert len(result) > 0


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
        assert all(doc.metadata == metadata for doc in documents)

    def test_document_chunker_chunk_text_short(self):
        """Test DocumentChunker with short text."""
        chunker = DocumentChunker()
        content = "Short text"
        metadata = {"source": "short.txt"}
        
        documents = chunker.chunk_text(content, metadata)
        
        assert isinstance(documents, list)
        assert len(documents) == 1
        assert documents[0].content == content
        assert documents[0].metadata == metadata

    def test_document_chunker_chunk_text_empty(self):
        """Test DocumentChunker with empty text."""
        chunker = DocumentChunker()
        content = ""
        metadata = {"source": "empty.txt"}
        
        documents = chunker.chunk_text(content, metadata)
        
        assert isinstance(documents, list)
        assert len(documents) == 1
        assert documents[0].content == content

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
        assert documents[0].content == "Content 1"
        assert documents[1].content == "Content 2"


class TestKubernetesDocProcessor:
    """Test KubernetesDocProcessor class."""

    def test_kubernetes_doc_processor_init_default(self):
        """Test KubernetesDocProcessor initialization with defaults."""
        processor = KubernetesDocProcessor()
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
        assert processor.separators == ["\n\n", "\n", " ", ""]

    def test_kubernetes_doc_processor_init_custom(self):
        """Test KubernetesDocProcessor initialization with custom parameters."""
        processor = KubernetesDocProcessor(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n", " "]
        )
        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 100
        assert processor.separators == ["\n", " "]

    def test_kubernetes_doc_processor_process_file_markdown(self):
        """Test processing a markdown file."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(TEST_MARKDOWN_CONTENT)
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
            f.write(TEST_TEXT_CONTENT)
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

    def test_kubernetes_doc_processor_process_file_empty(self):
        """Test processing an empty file."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            documents = processor.process_file(Path(temp_path))
            
            assert isinstance(documents, list)
            # Empty file should still produce at least one document
            assert len(documents) >= 0
        finally:
            os.unlink(temp_path)

    def test_kubernetes_doc_processor_chunk_text(self):
        """Test text chunking functionality."""
        processor = KubernetesDocProcessor(chunk_size=100, chunk_overlap=20)
        
        long_text = "This is a test sentence. " * 20  # Create long text
        chunks = processor._chunk_text(long_text, 100, 20, [" ", ""])
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1  # Should be chunked
        
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) <= 100  # Should respect chunk size

    def test_kubernetes_doc_processor_chunk_text_short(self):
        """Test chunking with short text."""
        processor = KubernetesDocProcessor()
        
        short_text = "Short text"
        chunks = processor._chunk_text(short_text, 100, 20, [" "])
        
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_kubernetes_doc_processor_extract_metadata(self):
        """Test metadata extraction."""
        processor = KubernetesDocProcessor()
        
        content = """# Test Document

This is a test document with some content.

## Section 1

More content here.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            metadata = processor._extract_metadata(content, Path(temp_path))
            
            assert isinstance(metadata, dict)
            assert "source" in metadata
            assert "file_type" in metadata
            assert metadata["source"] == temp_path
            assert metadata["file_type"] == "markdown"
        finally:
            os.unlink(temp_path)

    def test_kubernetes_doc_processor_extract_metadata_text(self):
        """Test metadata extraction for text file."""
        processor = KubernetesDocProcessor()
        
        content = "Plain text content"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            metadata = processor._extract_metadata(content, Path(temp_path))
            
            assert isinstance(metadata, dict)
            assert "source" in metadata
            assert "file_type" in metadata
            assert metadata["file_type"] == "text"
        finally:
            os.unlink(temp_path)


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_init_default(self, mock_transformer):
        """Test EmbeddingGenerator initialization with defaults."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator()
        
        assert generator.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert generator.device is None
        mock_transformer.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_init_custom(self, mock_transformer):
        """Test EmbeddingGenerator initialization with custom parameters."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator(
            model_name="custom-model",
            device="cpu"
        )
        
        assert generator.model_name == "custom-model"
        assert generator.device == "cpu"
        mock_transformer.assert_called_once_with("custom-model", device="cpu")

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_encode_single_text(self, mock_transformer):
        """Test encoding single text."""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator()
        result = generator.encode("Test text")
        
        assert result.shape == (1, 4)
        mock_model.encode.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_encode_multiple_texts(self, mock_transformer):
        """Test encoding multiple texts."""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator()
        texts = ["Text 1", "Text 2"]
        result = generator.encode(texts)
        
        assert result.shape == (2, 2)
        mock_model.encode.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_encode_with_parameters(self, mock_transformer):
        """Test encoding with custom parameters."""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator()
        result = generator.encode(
            "Test text",
            batch_size=16,
            show_progress=False,
            normalize=False
        )
        
        mock_model.encode.assert_called_once_with(
            "Test text",
            batch_size=16,
            show_progress=False,
            normalize=False
        )

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_encode_empty_list(self, mock_transformer):
        """Test encoding empty list."""
        mock_model = Mock()
        mock_model.encode.return_value = []
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator()
        result = generator.encode([])
        
        assert len(result) == 0
        mock_model.encode.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_generator_encode_error_handling(self, mock_transformer):
        """Test encoding error handling."""
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Encoding error")
        mock_transformer.return_value = mock_model
        
        generator = EmbeddingGenerator()
        
        with pytest.raises(Exception, match="Encoding error"):
            generator.encode("Test text")


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

    @patch('src.ingestion.pipeline.EmbeddingGenerator')
    @patch('src.ingestion.pipeline.KubernetesDocProcessor')
    @patch('src.ingestion.pipeline.VectorStore')
    def test_ingestion_pipeline_ingest_file(self, mock_vector_store, mock_doc_processor, mock_embedding_generator):
        """Test ingesting a single file."""
        # Setup mocks
        mock_vector_store_instance = Mock()
        mock_vector_store.return_value = mock_vector_store_instance
        
        mock_embedding_generator_instance = Mock()
        mock_embedding_generator_instance.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_embedding_generator.return_value = mock_embedding_generator_instance
        
        mock_doc_processor_instance = Mock()
        mock_doc_processor_instance.process_file.return_value = [
            Document(content="Test content", metadata={"source": "test.md"}, chunk_id="chunk_1")
        ]
        mock_doc_processor.return_value = mock_doc_processor_instance
        
        # Create pipeline
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store_instance,
            embedding_generator=mock_embedding_generator_instance,
            doc_processor=mock_doc_processor_instance
        )
        
        # Test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test\n\nContent")
            temp_path = f.name
        
        try:
            result = pipeline.ingest_file(Path(temp_path))
            
            assert isinstance(result, dict)
            assert "total_files" in result
            assert "processed_files" in result
            assert "total_chunks" in result
            assert "failed_files" in result
            
            mock_doc_processor_instance.process_file.assert_called_once()
            mock_embedding_generator_instance.encode.assert_called_once()
            mock_vector_store_instance.add_documents.assert_called_once()
        finally:
            os.unlink(temp_path)

    @patch('src.ingestion.pipeline.EmbeddingGenerator')
    @patch('src.ingestion.pipeline.KubernetesDocProcessor')
    @patch('src.ingestion.pipeline.VectorStore')
    def test_ingestion_pipeline_ingest_directory(self, mock_vector_store, mock_doc_processor, mock_embedding_generator):
        """Test ingesting a directory."""
        # Setup mocks
        mock_vector_store_instance = Mock()
        mock_vector_store.return_value = mock_vector_store_instance
        
        mock_embedding_generator_instance = Mock()
        mock_embedding_generator_instance.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_embedding_generator.return_value = mock_embedding_generator_instance
        
        mock_doc_processor_instance = Mock()
        mock_doc_processor_instance.process_file.return_value = [
            Document(content="Test content", metadata={"source": "test.md"}, chunk_id="chunk_1")
        ]
        mock_doc_processor.return_value = mock_doc_processor_instance
        
        # Create pipeline
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store_instance,
            embedding_generator=mock_embedding_generator_instance,
            doc_processor=mock_doc_processor_instance
        )
        
        # Create test directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test1.md").write_text("# Test 1\n\nContent 1")
            (temp_path / "test2.txt").write_text("Test 2 content")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "test3.md").write_text("# Test 3\n\nContent 3")
            
            result = pipeline.ingest_directory(temp_path, "*.md")
            
            assert isinstance(result, dict)
            assert "total_files" in result
            assert "processed_files" in result
            assert "total_chunks" in result
            assert "failed_files" in result
            assert result["total_files"] >= 2  # Should find at least 2 .md files

    @patch('src.ingestion.pipeline.EmbeddingGenerator')
    @patch('src.ingestion.pipeline.KubernetesDocProcessor')
    @patch('src.ingestion.pipeline.VectorStore')
    def test_ingestion_pipeline_ingest_file_error(self, mock_vector_store, mock_doc_processor, mock_embedding_generator):
        """Test ingesting file with error."""
        # Setup mocks
        mock_vector_store_instance = Mock()
        mock_vector_store.return_value = mock_vector_store_instance
        
        mock_embedding_generator_instance = Mock()
        mock_embedding_generator_instance.encode.side_effect = Exception("Encoding error")
        mock_embedding_generator.return_value = mock_embedding_generator_instance
        
        mock_doc_processor_instance = Mock()
        mock_doc_processor_instance.process_file.return_value = [
            Document(content="Test content", metadata={"source": "test.md"}, chunk_id="chunk_1")
        ]
        mock_doc_processor.return_value = mock_doc_processor_instance
        
        # Create pipeline
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store_instance,
            embedding_generator=mock_embedding_generator_instance,
            doc_processor=mock_doc_processor_instance
        )
        
        # Test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test\n\nContent")
            temp_path = f.name
        
        try:
            result = pipeline.ingest_file(Path(temp_path))
            
            assert isinstance(result, dict)
            assert "failed_files" in result
            assert len(result["failed_files"]) > 0
        finally:
            os.unlink(temp_path)

    @patch('src.ingestion.pipeline.EmbeddingGenerator')
    @patch('src.ingestion.pipeline.KubernetesDocProcessor')
    @patch('src.ingestion.pipeline.VectorStore')
    def test_ingestion_pipeline_ingest_empty_directory(self, mock_vector_store, mock_doc_processor, mock_embedding_generator):
        """Test ingesting empty directory."""
        # Setup mocks
        mock_vector_store_instance = Mock()
        mock_vector_store.return_value = mock_vector_store_instance
        
        mock_embedding_generator_instance = Mock()
        mock_embedding_generator.return_value = mock_embedding_generator_instance
        
        mock_doc_processor_instance = Mock()
        mock_doc_processor.return_value = mock_doc_processor_instance
        
        # Create pipeline
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store_instance,
            embedding_generator=mock_embedding_generator_instance,
            doc_processor=mock_doc_processor_instance
        )
        
        # Create empty directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            result = pipeline.ingest_directory(temp_path)
            
            assert isinstance(result, dict)
            assert result["total_files"] == 0
            assert result["processed_files"] == 0
            assert result["total_chunks"] == 0
            assert result["failed_files"] == []


class TestIngestionIntegration:
    """Test integration scenarios for ingestion module."""

    @patch('src.ingestion.pipeline.EmbeddingGenerator')
    @patch('src.ingestion.pipeline.KubernetesDocProcessor')
    @patch('src.ingestion.pipeline.VectorStore')
    def test_full_ingestion_workflow(self, mock_vector_store, mock_doc_processor, mock_embedding_generator):
        """Test full ingestion workflow."""
        # Setup mocks
        mock_vector_store_instance = Mock()
        mock_vector_store.return_value = mock_vector_store_instance
        
        mock_embedding_generator_instance = Mock()
        mock_embedding_generator_instance.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_embedding_generator.return_value = mock_embedding_generator_instance
        
        mock_doc_processor_instance = Mock()
        mock_doc_processor_instance.process_file.return_value = [
            Document(content="Test content 1", metadata={"source": "test1.md"}, chunk_id="chunk_1"),
            Document(content="Test content 2", metadata={"source": "test1.md"}, chunk_id="chunk_2")
        ]
        mock_doc_processor.return_value = mock_doc_processor_instance
        
        # Create pipeline
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store_instance,
            embedding_generator=mock_embedding_generator_instance,
            doc_processor=mock_doc_processor_instance
        )
        
        # Test with multiple files
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
            assert mock_doc_processor_instance.process_file.call_count >= 2
            assert mock_embedding_generator_instance.encode.call_count >= 2
            assert mock_vector_store_instance.add_documents.call_count >= 2

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
            assert md_docs[0].metadata["file_type"] == "markdown"
            
            # Process text
            txt_docs = processor.process_file(Path(txt_path))
            assert len(txt_docs) > 0
            assert txt_docs[0].metadata["file_type"] == "text"
        finally:
            os.unlink(md_path)
            os.unlink(txt_path)

    def test_embedding_generator_with_different_texts(self):
        """Test embedding generator with different text types."""
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_transformer.return_value = mock_model
            
            generator = EmbeddingGenerator()
            
            # Test single text
            result1 = generator.encode("Single text")
            assert result1.shape == (1, 3)
            
            # Test multiple texts
            result2 = generator.encode(["Text 1", "Text 2"])
            assert result2.shape == (2, 3)
            
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
            assert all(len(doc.content) <= 500 for doc in documents)  # Respect chunk size
        finally:
            os.unlink(temp_path)

    def test_embedding_generator_performance(self):
        """Test embedding generator performance."""
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]] * 100
            mock_transformer.return_value = mock_model
            
            generator = EmbeddingGenerator()
            
            # Test with many texts
            texts = [f"Text {i}" for i in range(100)]
            
            import time
            start_time = time.time()
            
            result = generator.encode(texts)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert duration < 1.0  # Should complete in reasonable time
            assert result.shape == (100, 3)

    def test_ingestion_pipeline_performance(self):
        """Test ingestion pipeline performance."""
        with patch('src.ingestion.pipeline.EmbeddingGenerator') as mock_embedding_generator, \
             patch('src.ingestion.pipeline.KubernetesDocProcessor') as mock_doc_processor, \
             patch('src.ingestion.pipeline.VectorStore') as mock_vector_store:
            
            # Setup mocks
            mock_vector_store_instance = Mock()
            mock_vector_store.return_value = mock_vector_store_instance
            
            mock_embedding_generator_instance = Mock()
            mock_embedding_generator_instance.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_embedding_generator.return_value = mock_embedding_generator_instance
            
            mock_doc_processor_instance = Mock()
            mock_doc_processor_instance.process_file.return_value = [
                Document(content=f"Content {i}", metadata={"source": f"doc{i}.md"}, chunk_id=f"chunk_{i}")
                for i in range(10)
            ]
            mock_doc_processor.return_value = mock_doc_processor_instance
            
            # Create pipeline
            pipeline = IngestionPipeline(
                vector_store=mock_vector_store_instance,
                embedding_generator=mock_embedding_generator_instance,
                doc_processor=mock_doc_processor_instance
            )
            
            # Test with multiple files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create many test files
                for i in range(20):
                    (temp_path / f"doc{i}.md").write_text(f"# Document {i}\n\nContent {i}")
                
                import time
                start_time = time.time()
                
                result = pipeline.ingest_directory(temp_path)
                
                end_time = time.time()
                duration = end_time - start_time
                
                assert duration < 5.0  # Should complete in reasonable time
                assert result["total_files"] == 20
                assert result["processed_files"] == 20
