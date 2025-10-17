"""Comprehensive test suite for ingestion module to achieve 100% coverage."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.ingestion.document_processor import DocumentProcessor
from src.ingestion.embeddings import EmbeddingsManager, create_embeddings
from src.ingestion.pipeline import IngestionPipeline, create_ingestion_pipeline


class TestDocumentProcessor:
    """Test DocumentProcessor class."""
    
    def test_document_processor_init(self):
        """Test DocumentProcessor initialization."""
        processor = DocumentProcessor()
        assert processor is not None
    
    def test_process_markdown(self):
        """Test processing markdown documents."""
        processor = DocumentProcessor()
        
        markdown_content = """# Test Document
        
This is a test document with **bold** and *italic* text.

## Section 2

Some more content here.
"""
        
        result = processor.process_markdown(markdown_content, "test.md")
        
        assert len(result) > 0
        assert all("content" in chunk for chunk in result)
        assert all("metadata" in chunk for chunk in result)
    
    def test_process_text(self):
        """Test processing plain text documents."""
        processor = DocumentProcessor()
        
        text_content = "This is a plain text document with some content."
        
        result = processor.process_text(text_content, "test.txt")
        
        assert len(result) > 0
        assert all("content" in chunk for chunk in result)
        assert all("metadata" in chunk for chunk in result)
    
    def test_process_document_unsupported_format(self):
        """Test processing unsupported document format."""
        processor = DocumentProcessor()
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            processor.process_document("test.xyz", "some content")
    
    def test_chunk_text(self):
        """Test text chunking functionality."""
        processor = DocumentProcessor()
        
        text = "This is a very long text that should be chunked into smaller pieces. " * 100
        
        chunks = processor._chunk_text(text, chunk_size=100, overlap=20)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
    
    def test_extract_metadata(self):
        """Test metadata extraction."""
        processor = DocumentProcessor()
        
        content = """# Test Document
        
This is a test document.

## Section 1

Some content.
"""
        
        metadata = processor._extract_metadata(content, "test.md")
        
        assert "source" in metadata
        assert "title" in metadata
        assert metadata["source"] == "test.md"
        assert metadata["title"] == "Test Document"


class TestEmbeddingsManager:
    """Test EmbeddingsManager class."""
    
    def test_embeddings_manager_init_openai(self):
        """Test EmbeddingsManager initialization with OpenAI."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            manager = EmbeddingsManager(provider="openai", model="text-embedding-ada-002")
            assert manager.provider == "openai"
            assert manager.model == "text-embedding-ada-002"
    
    def test_embeddings_manager_init_sentence_transformers(self):
        """Test EmbeddingsManager initialization with SentenceTransformers."""
        manager = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
        assert manager.provider == "sentence_transformers"
        assert manager.model == "all-MiniLM-L6-v2"
    
    def test_embeddings_manager_init_unsupported(self):
        """Test EmbeddingsManager initialization with unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported embeddings provider"):
            EmbeddingsManager(provider="unsupported", model="test-model")
    
    @patch('openai.OpenAI')
    def test_embed_documents_openai(self, mock_openai):
        """Test embedding documents with OpenAI."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [Mock() for _ in range(3)]
            for i, item in enumerate(mock_response.data):
                item.embedding = [0.1, 0.2, 0.3]
            mock_client.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            manager = EmbeddingsManager(provider="openai", model="text-embedding-ada-002")
            documents = ["doc1", "doc2", "doc3"]
            
            embeddings = manager.embed_documents(documents)
            
            assert len(embeddings) == 3
            assert all(len(emb) == 3 for emb in embeddings)
            mock_client.embeddings.create.assert_called_once()
    
    @patch('sentence_transformers.SentenceTransformer')
    def test_embed_documents_sentence_transformers(self, mock_st):
        """Test embedding documents with SentenceTransformers."""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_st.return_value = mock_model
        
        manager = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
        documents = ["doc1", "doc2"]
        
        embeddings = manager.embed_documents(documents)
        
        assert len(embeddings) == 2
        assert all(len(emb) == 3 for emb in embeddings)
        mock_model.encode.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_embed_query_openai(self, mock_openai):
        """Test embedding query with OpenAI."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [Mock()]
            mock_response.data[0].embedding = [0.1, 0.2, 0.3]
            mock_client.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            manager = EmbeddingsManager(provider="openai", model="text-embedding-ada-002")
            query = "test query"
            
            embedding = manager.embed_query(query)
            
            assert len(embedding) == 3
            assert embedding == [0.1, 0.2, 0.3]
            mock_client.embeddings.create.assert_called_once()
    
    @patch('sentence_transformers.SentenceTransformer')
    def test_embed_query_sentence_transformers(self, mock_st):
        """Test embedding query with SentenceTransformers."""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_st.return_value = mock_model
        
        manager = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
        query = "test query"
        
        embedding = manager.embed_query(query)
        
        assert len(embedding) == 3
        assert embedding == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once()


class TestCreateEmbeddings:
    """Test create_embeddings function."""
    
    def test_create_embeddings_openai(self):
        """Test creating OpenAI embeddings."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            manager = create_embeddings(provider="openai", model="text-embedding-ada-002")
            assert isinstance(manager, EmbeddingsManager)
            assert manager.provider == "openai"
    
    def test_create_embeddings_sentence_transformers(self):
        """Test creating SentenceTransformers embeddings."""
        manager = create_embeddings(provider="sentence_transformers", model="all-MiniLM-L6-v2")
        assert isinstance(manager, EmbeddingsManager)
        assert manager.provider == "sentence_transformers"
    
    def test_create_embeddings_unsupported(self):
        """Test creating unsupported embeddings provider."""
        with pytest.raises(ValueError, match="Unsupported embeddings provider"):
            create_embeddings(provider="unsupported", model="test-model")


class TestIngestionPipeline:
    """Test IngestionPipeline class."""
    
    def test_ingestion_pipeline_init(self):
        """Test IngestionPipeline initialization."""
        mock_config = Mock()
        mock_config.embeddings.provider = "sentence_transformers"
        mock_config.embeddings.model_name = "all-MiniLM-L6-v2"
        mock_config.vector_store.type = "chroma"
        mock_config.vector_store.persist_directory = "/tmp/test"
        
        with patch('src.ingestion.embeddings.create_embeddings') as mock_create_embeddings, \
             patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            
            mock_embeddings = Mock()
            mock_vector_store = Mock()
            mock_create_embeddings.return_value = mock_embeddings
            mock_create_vs.return_value = mock_vector_store
            
            pipeline = IngestionPipeline(mock_config)
            
            assert pipeline.embeddings == mock_embeddings
            assert pipeline.vector_store == mock_vector_store
    
    def test_ingest_file(self):
        """Test ingesting a single file."""
        mock_config = Mock()
        mock_config.embeddings.provider = "sentence_transformers"
        mock_config.embeddings.model_name = "all-MiniLM-L6-v2"
        mock_config.vector_store.type = "chroma"
        mock_config.vector_store.persist_directory = "/tmp/test"
        
        with patch('src.ingestion.embeddings.create_embeddings') as mock_create_embeddings, \
             patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs, \
             patch('src.ingestion.document_processor.DocumentProcessor') as mock_processor_class:
            
            mock_embeddings = Mock()
            mock_vector_store = Mock()
            mock_processor = Mock()
            mock_processor.process_document.return_value = [
                {"content": "chunk1", "metadata": {}},
                {"content": "chunk2", "metadata": {}}
            ]
            mock_embeddings.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
            mock_vector_store.add_documents.return_value = ["doc1", "doc2"]
            
            mock_create_embeddings.return_value = mock_embeddings
            mock_create_vs.return_value = mock_vector_store
            mock_processor_class.return_value = mock_processor
            
            pipeline = IngestionPipeline(mock_config)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Test Document\n\nSome content.")
                f.flush()
                
                result = pipeline.ingest_file(Path(f.name))
                
                assert result == 2
                mock_processor.process_document.assert_called_once()
                mock_embeddings.embed_documents.assert_called_once()
                mock_vector_store.add_documents.assert_called_once()
    
    def test_ingest_directory(self):
        """Test ingesting a directory."""
        mock_config = Mock()
        mock_config.embeddings.provider = "sentence_transformers"
        mock_config.embeddings.model_name = "all-MiniLM-L6-v2"
        mock_config.vector_store.type = "chroma"
        mock_config.vector_store.persist_directory = "/tmp/test"
        
        with patch('src.ingestion.embeddings.create_embeddings') as mock_create_embeddings, \
             patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs, \
             patch('src.ingestion.document_processor.DocumentProcessor') as mock_processor_class:
            
            mock_embeddings = Mock()
            mock_vector_store = Mock()
            mock_processor = Mock()
            mock_processor.process_document.return_value = [
                {"content": "chunk1", "metadata": {}}
            ]
            mock_embeddings.embed_documents.return_value = [[0.1, 0.2]]
            mock_vector_store.add_documents.return_value = ["doc1"]
            
            mock_create_embeddings.return_value = mock_embeddings
            mock_create_vs.return_value = mock_vector_store
            mock_processor_class.return_value = mock_processor
            
            pipeline = IngestionPipeline(mock_config)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create test files
                (temp_path / "test1.md").write_text("# Test 1\nContent 1")
                (temp_path / "test2.md").write_text("# Test 2\nContent 2")
                
                result = pipeline.ingest_directory(temp_path, "*.md")
                
                assert result["processed_files"] == 2
                assert result["total_files"] == 2
                assert result["total_chunks"] == 2
                assert result["failed_files"] == []


class TestCreateIngestionPipeline:
    """Test create_ingestion_pipeline function."""
    
    def test_create_ingestion_pipeline(self):
        """Test creating ingestion pipeline."""
        mock_config = Mock()
        mock_config.embeddings.provider = "sentence_transformers"
        mock_config.embeddings.model_name = "all-MiniLM-L6-v2"
        mock_config.vector_store.type = "chroma"
        mock_config.vector_store.persist_directory = "/tmp/test"
        
        with patch('src.ingestion.embeddings.create_embeddings') as mock_create_embeddings, \
             patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            
            mock_embeddings = Mock()
            mock_vector_store = Mock()
            mock_create_embeddings.return_value = mock_embeddings
            mock_create_vs.return_value = mock_vector_store
            
            pipeline = create_ingestion_pipeline(mock_config)
            
            assert isinstance(pipeline, IngestionPipeline)
            mock_create_embeddings.assert_called_once()
            mock_create_vs.assert_called_once()


@pytest.mark.unit
class TestIngestionEdgeCases:
    """Test edge cases for ingestion module."""
    
    def test_document_processor_empty_content(self):
        """Test document processor with empty content."""
        processor = DocumentProcessor()
        
        result = processor.process_text("", "empty.txt")
        
        assert len(result) == 0
    
    def test_embeddings_manager_empty_documents(self):
        """Test embeddings manager with empty documents list."""
        manager = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
        
        with patch('sentence_transformers.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.return_value = []
            mock_st.return_value = mock_model
            
            embeddings = manager.embed_documents([])
            
            assert len(embeddings) == 0
    
    def test_ingestion_pipeline_file_not_found(self):
        """Test ingestion pipeline with non-existent file."""
        mock_config = Mock()
        mock_config.embeddings.provider = "sentence_transformers"
        mock_config.embeddings.model_name = "all-MiniLM-L6-v2"
        mock_config.vector_store.type = "chroma"
        mock_config.vector_store.persist_directory = "/tmp/test"
        
        with patch('src.ingestion.embeddings.create_embeddings') as mock_create_embeddings, \
             patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            
            mock_embeddings = Mock()
            mock_vector_store = Mock()
            mock_create_embeddings.return_value = mock_embeddings
            mock_create_vs.return_value = mock_vector_store
            
            pipeline = IngestionPipeline(mock_config)
            
            with pytest.raises(FileNotFoundError):
                pipeline.ingest_file(Path("non_existent_file.md"))
    
    def test_ingestion_pipeline_empty_directory(self):
        """Test ingestion pipeline with empty directory."""
        mock_config = Mock()
        mock_config.embeddings.provider = "sentence_transformers"
        mock_config.embeddings.model_name = "all-MiniLM-L6-v2"
        mock_config.vector_store.type = "chroma"
        mock_config.vector_store.persist_directory = "/tmp/test"
        
        with patch('src.ingestion.embeddings.create_embeddings') as mock_create_embeddings, \
             patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            
            mock_embeddings = Mock()
            mock_vector_store = Mock()
            mock_create_embeddings.return_value = mock_embeddings
            mock_create_vs.return_value = mock_vector_store
            
            pipeline = IngestionPipeline(mock_config)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                result = pipeline.ingest_directory(temp_path, "*.md")
                
                assert result["processed_files"] == 0
                assert result["total_files"] == 0
                assert result["total_chunks"] == 0
                assert result["failed_files"] == []


