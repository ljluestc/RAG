"""Fixed comprehensive test suite for ingestion module to achieve 100% coverage."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test configuration
from test_config_comprehensive import (
    create_mock_config,
    create_mock_settings,
    create_mock_document,
    create_mock_documents,
    create_mock_vector_store,
    create_mock_embedding_generator,
    create_mock_document_processor,
    TEST_MARKDOWN_CONTENT,
    TEST_TEXT_CONTENT,
    TEST_CONFIG_DATA
)

from src.ingestion.document_processor import (
    Document,
    MarkdownProcessor,
    KubernetesDocProcessor
)
from src.ingestion.embeddings import EmbeddingGenerator, create_embeddings
from src.ingestion.pipeline import IngestionPipeline, create_ingestion_pipeline


class TestDocument:
    """Test Document class."""

    def test_document_init(self):
        """Test Document initialization."""
        doc = Document(
            content="Test content",
            metadata={"source": "test.md"},
            chunk_id="test_chunk_1"
        )
        assert doc.content == "Test content"
        assert doc.metadata == {"source": "test.md"}
        assert doc.chunk_id == "test_chunk_1"


class TestMarkdownProcessor:
    """Test MarkdownProcessor class."""

    def test_markdown_processor_init(self):
        """Test MarkdownProcessor initialization."""
        processor = MarkdownProcessor()
        assert processor.md is not None

    def test_extract_sections(self):
        """Test extract_sections method."""
        processor = MarkdownProcessor()
        sections = processor.extract_sections(TEST_MARKDOWN_CONTENT)
        
        assert len(sections) > 0
        assert any(section["title"] == "Kubernetes Overview" for section in sections)
        assert any(section["title"] == "Features" for section in sections)

    def test_extract_sections_empty(self):
        """Test extract_sections with empty content."""
        processor = MarkdownProcessor()
        sections = processor.extract_sections("")
        assert len(sections) == 0

    def test_extract_sections_no_headers(self):
        """Test extract_sections with no headers."""
        processor = MarkdownProcessor()
        content = "Just plain text without headers."
        sections = processor.extract_sections(content)
        assert len(sections) == 1
        assert sections[0]["content"].strip() == content


class TestKubernetesDocProcessor:
    """Test KubernetesDocProcessor class."""

    def test_kubernetes_doc_processor_init(self):
        """Test KubernetesDocProcessor initialization."""
        processor = KubernetesDocProcessor()
        assert processor is not None

    def test_process_file_markdown(self):
        """Test process_file with markdown file."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(TEST_MARKDOWN_CONTENT)
            f.flush()
            
            try:
                result = processor.process_file(Path(f.name))
                assert isinstance(result, list)
                assert len(result) > 0
                assert all(isinstance(doc, Document) for doc in result)
            finally:
                os.unlink(f.name)

    def test_process_file_text(self):
        """Test process_file with text file."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(TEST_TEXT_CONTENT)
            f.flush()
            
            try:
                result = processor.process_file(Path(f.name))
                assert isinstance(result, list)
                assert len(result) > 0
                assert all(isinstance(doc, Document) for doc in result)
            finally:
                os.unlink(f.name)

    def test_process_file_unsupported(self):
        """Test process_file with unsupported file type."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            f.write("Some content")
            f.flush()
            
            try:
                with pytest.raises(ValueError, match="Unsupported file type"):
                    processor.process_file(Path(f.name))
            finally:
                os.unlink(f.name)

    def test_chunk_text(self):
        """Test _chunk_text method."""
        processor = KubernetesDocProcessor()
        
        text = "This is a long text that should be chunked into smaller pieces. " * 10
        chunks = processor._chunk_text(text, chunk_size=100, overlap=20)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_extract_metadata(self):
        """Test _extract_metadata method."""
        processor = KubernetesDocProcessor()
        
        metadata = processor._extract_metadata(TEST_MARKDOWN_CONTENT, "test.md")
        
        assert isinstance(metadata, dict)
        assert "source" in metadata
        assert metadata["source"] == "test.md"


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    def test_embedding_generator_init(self):
        """Test EmbeddingGenerator initialization."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            generator = EmbeddingGenerator(model_name="test-model")
            assert generator.model_name == "test-model"
            assert generator.embedding_dim == 384

    def test_embedding_generator_init_with_device(self):
        """Test EmbeddingGenerator initialization with device."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            generator = EmbeddingGenerator(model_name="test-model", device="cpu")
            assert generator.device == "cpu"

    def test_encode_single_text(self):
        """Test encode with single text."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
            
            generator = EmbeddingGenerator()
            result = generator.encode("Test text")
            
            assert result.shape == (1, 4)

    def test_encode_multiple_texts(self):
        """Test encode with multiple texts."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
            
            generator = EmbeddingGenerator()
            result = generator.encode(["Text 1", "Text 2"])
            
            assert result.shape == (2, 2)

    def test_encode_with_parameters(self):
        """Test encode with parameters."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
            
            generator = EmbeddingGenerator()
            result = generator.encode(
                "Test text",
                batch_size=16,
                show_progress=False,
                normalize=True
            )
            
            assert result.shape == (1, 4)

    def test_embed_documents(self):
        """Test embed_documents method."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
            
            generator = EmbeddingGenerator()
            documents = create_mock_documents(2)
            result = generator.embed_documents(documents)
            
            assert result.shape == (2, 2)

    def test_embed_query(self):
        """Test embed_query method."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
            
            generator = EmbeddingGenerator()
            result = generator.embed_query("Test query")
            
            assert result.shape == (1, 4)


class TestCreateEmbeddings:
    """Test create_embeddings function."""

    def test_create_embeddings(self):
        """Test create_embeddings function."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            
            generator = create_embeddings(model_name="test-model")
            assert isinstance(generator, EmbeddingGenerator)


class TestIngestionPipeline:
    """Test IngestionPipeline class."""

    def test_ingestion_pipeline_init(self):
        """Test IngestionPipeline initialization."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        mock_doc_processor = create_mock_document_processor()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        assert pipeline.vector_store == mock_vector_store
        assert pipeline.embedding_generator == mock_embedding_generator
        assert pipeline.doc_processor == mock_doc_processor

    def test_ingest_file(self):
        """Test ingest_file method."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        mock_doc_processor = create_mock_document_processor()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(TEST_MARKDOWN_CONTENT)
            f.flush()
            
            try:
                result = pipeline.ingest_file(Path(f.name))
                assert isinstance(result, int)
                assert result > 0
            finally:
                os.unlink(f.name)

    def test_ingest_directory(self):
        """Test ingest_directory method."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        mock_doc_processor = create_mock_document_processor()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test1.md").write_text(TEST_MARKDOWN_CONTENT)
            (temp_path / "test2.txt").write_text(TEST_TEXT_CONTENT)
            
            result = pipeline.ingest_directory(temp_path)
            assert isinstance(result, int)
            assert result > 0

    def test_ingest_directory_with_pattern(self):
        """Test ingest_directory with file pattern."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        mock_doc_processor = create_mock_document_processor()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test1.md").write_text(TEST_MARKDOWN_CONTENT)
            (temp_path / "test2.txt").write_text(TEST_TEXT_CONTENT)
            (temp_path / "test3.xyz").write_text("Some content")
            
            result = pipeline.ingest_directory(temp_path, file_pattern="*.md")
            assert isinstance(result, int)
            assert result > 0


class TestCreateIngestionPipeline:
    """Test create_ingestion_pipeline function."""

    def test_create_ingestion_pipeline(self):
        """Test create_ingestion_pipeline function."""
        mock_config = create_mock_config()
        
        with patch("src.retrieval.vector_store.VectorStore") as mock_vs_class, \
             patch("src.ingestion.embeddings.EmbeddingGenerator") as mock_emb_class, \
             patch("src.ingestion.document_processor.KubernetesDocProcessor") as mock_doc_class:
            
            mock_vs_instance = create_mock_vector_store()
            mock_emb_instance = create_mock_embedding_generator()
            mock_doc_instance = create_mock_document_processor()
            
            mock_vs_class.return_value = mock_vs_instance
            mock_emb_class.return_value = mock_emb_instance
            mock_doc_class.return_value = mock_doc_instance
            
            pipeline = create_ingestion_pipeline(mock_config)
            
            assert isinstance(pipeline, IngestionPipeline)
            mock_vs_class.assert_called_once()
            mock_emb_class.assert_called_once()
            mock_doc_class.assert_called_once()


class TestIngestionEdgeCases:
    """Test edge cases for ingestion module."""

    def test_document_processor_empty_content(self):
        """Test document processor with empty content."""
        processor = KubernetesDocProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            f.flush()
            
            try:
                result = processor.process_file(Path(f.name))
                assert isinstance(result, list)
            finally:
                os.unlink(f.name)

    def test_embedding_generator_empty_documents(self):
        """Test embedding generator with empty documents."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = []
            
            generator = EmbeddingGenerator()
            result = generator.embed_documents([])
            
            assert result.shape == (0, 384)

    def test_ingestion_pipeline_file_not_found(self):
        """Test ingestion pipeline with non-existent file."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        mock_doc_processor = create_mock_document_processor()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with pytest.raises(FileNotFoundError):
            pipeline.ingest_file(Path("non_existent_file.md"))

    def test_ingestion_pipeline_empty_directory(self):
        """Test ingestion pipeline with empty directory."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        mock_doc_processor = create_mock_document_processor()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = pipeline.ingest_directory(temp_path)
            assert result == 0

    def test_markdown_processor_malformed_markdown(self):
        """Test markdown processor with malformed markdown."""
        processor = MarkdownProcessor()
        malformed_content = "# Header\n\nSome content\n\n### Another header without closing"
        
        sections = processor.extract_sections(malformed_content)
        assert isinstance(sections, list)

    def test_embedding_generator_large_batch(self):
        """Test embedding generator with large batch."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = [[0.1, 0.2]] * 1000
            
            generator = EmbeddingGenerator()
            texts = [f"Text {i}" for i in range(1000)]
            result = generator.encode(texts, batch_size=100)
            
            assert result.shape == (1000, 2)


class TestIngestionIntegration:
    """Test integration scenarios for ingestion module."""

    def test_full_ingestion_workflow(self):
        """Test full ingestion workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test1.md").write_text(TEST_MARKDOWN_CONTENT)
            (temp_path / "test2.txt").write_text(TEST_TEXT_CONTENT)
            
            # Create pipeline
            mock_vector_store = create_mock_vector_store()
            mock_embedding_generator = create_mock_embedding_generator()
            mock_doc_processor = create_mock_document_processor()
            
            pipeline = IngestionPipeline(
                vector_store=mock_vector_store,
                embedding_generator=mock_embedding_generator,
                doc_processor=mock_doc_processor
            )
            
            # Ingest directory
            result = pipeline.ingest_directory(temp_path)
            assert isinstance(result, int)
            assert result > 0

    def test_document_processor_with_various_formats(self):
        """Test document processor with various file formats."""
        processor = KubernetesDocProcessor()
        
        test_files = [
            ("test.md", TEST_MARKDOWN_CONTENT),
            ("test.txt", TEST_TEXT_CONTENT),
        ]
        
        for filename, content in test_files:
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{filename.split(".")[-1]}', delete=False) as f:
                f.write(content)
                f.flush()
                
                try:
                    result = processor.process_file(Path(f.name))
                    assert isinstance(result, list)
                    assert len(result) > 0
                finally:
                    os.unlink(f.name)


class TestIngestionPerformance:
    """Test performance scenarios for ingestion module."""

    def test_document_processing_performance(self):
        """Test document processing performance."""
        import time
        
        processor = KubernetesDocProcessor()
        
        # Create large content
        large_content = TEST_MARKDOWN_CONTENT * 100
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(large_content)
            f.flush()
            
            try:
                start_time = time.time()
                result = processor.process_file(Path(f.name))
                end_time = time.time()
                
                duration = end_time - start_time
                assert duration < 5.0  # Should complete in reasonable time
                assert isinstance(result, list)
            finally:
                os.unlink(f.name)

    def test_embedding_generation_performance(self):
        """Test embedding generation performance."""
        import time
        
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = [[0.1, 0.2, 0.3, 0.4]] * 100
            
            generator = EmbeddingGenerator()
            
            texts = [f"Text {i}" for i in range(100)]
            
            start_time = time.time()
            result = generator.encode(texts)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 2.0  # Should complete quickly
            assert result.shape == (100, 4)

    def test_pipeline_ingestion_performance(self):
        """Test pipeline ingestion performance."""
        import time
        
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        mock_doc_processor = create_mock_document_processor()
        
        pipeline = IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple test files
            for i in range(10):
                (temp_path / f"test_{i}.md").write_text(TEST_MARKDOWN_CONTENT)
            
            start_time = time.time()
            result = pipeline.ingest_directory(temp_path)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 3.0  # Should complete in reasonable time
            assert isinstance(result, int)
