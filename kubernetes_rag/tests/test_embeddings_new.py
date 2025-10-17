"""Tests for embeddings module with actual EmbeddingGenerator implementation."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.ingestion.embeddings import EmbeddingGenerator, HybridEmbedding, create_embeddings


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_embedding_generator_init(self, mock_cuda, mock_st):
        """Test EmbeddingGenerator initialization."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")

        assert gen.model_name == "all-MiniLM-L6-v2"
        assert gen.device == "cpu"
        assert gen.embedding_dim == 384
        mock_st.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_embedding_generator_init_with_device(self, mock_cuda, mock_st):
        """Test EmbeddingGenerator initialization with specific device."""
        mock_cuda.return_value = True
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator(model_name="all-MiniLM-L6-v2", device="cuda")

        assert gen.device == "cuda"
        mock_st.assert_called_once_with("all-MiniLM-L6-v2", device="cuda")

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_encode_single_text(self, mock_cuda, mock_st):
        """Test encoding single text."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4]])
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator()
        result = gen.encode("test text")

        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 4)
        mock_model.encode.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_encode_multiple_texts(self, mock_cuda, mock_st):
        """Test encoding multiple texts."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator()
        result = gen.encode(["text1", "text2"])

        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 2)
        mock_model.encode.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_encode_documents(self, mock_cuda, mock_st):
        """Test encoding Document objects."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator()

        # Create mock documents
        doc1 = Mock()
        doc1.content = "Document 1 content"
        doc2 = Mock()
        doc2.content = "Document 2 content"

        result = gen.encode_documents([doc1, doc2])

        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 2)
        mock_model.encode.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_get_embedding_dim(self, mock_cuda, mock_st):
        """Test get_embedding_dim method."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator()
        dim = gen.get_embedding_dim()

        assert dim == 384

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_encode_query(self, mock_cuda, mock_st):
        """Test encode_query method."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator()
        result = gen.encode_query("test query")

        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
        mock_model.encode.assert_called_once()


class TestHybridEmbedding:
    """Test HybridEmbedding class."""

    @patch('src.ingestion.embeddings.EmbeddingGenerator')
    def test_hybrid_embedding_init(self, mock_eg_class):
        """Test HybridEmbedding initialization."""
        mock_dense_encoder = Mock()
        mock_eg_class.return_value = mock_dense_encoder

        hybrid = HybridEmbedding(dense_model_name="all-MiniLM-L6-v2")

        assert hybrid.dense_encoder == mock_dense_encoder
        mock_eg_class.assert_called_once_with("all-MiniLM-L6-v2")

    @patch('src.ingestion.embeddings.EmbeddingGenerator')
    def test_encode_dense(self, mock_eg_class):
        """Test encode_dense method."""
        mock_dense_encoder = Mock()
        mock_dense_encoder.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_eg_class.return_value = mock_dense_encoder

        hybrid = HybridEmbedding()
        result = hybrid.encode_dense("test text")

        assert isinstance(result, np.ndarray)
        mock_dense_encoder.encode.assert_called_once_with("test text")

    @patch('src.ingestion.embeddings.EmbeddingGenerator')
    def test_encode_sparse_single(self, mock_eg_class):
        """Test encode_sparse with single text."""
        mock_dense_encoder = Mock()
        mock_eg_class.return_value = mock_dense_encoder

        hybrid = HybridEmbedding()
        result = hybrid.encode_sparse("test word test")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["test"] == 2
        assert result[0]["word"] == 1

    @patch('src.ingestion.embeddings.EmbeddingGenerator')
    def test_encode_sparse_multiple(self, mock_eg_class):
        """Test encode_sparse with multiple texts."""
        mock_dense_encoder = Mock()
        mock_eg_class.return_value = mock_dense_encoder

        hybrid = HybridEmbedding()
        result = hybrid.encode_sparse(["text one", "text two"])

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        assert result[0]["text"] == 1
        assert result[1]["text"] == 1

    @patch('src.ingestion.embeddings.EmbeddingGenerator')
    def test_encode_hybrid(self, mock_eg_class):
        """Test encode_hybrid method."""
        mock_dense_encoder = Mock()
        mock_dense_encoder.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_eg_class.return_value = mock_dense_encoder

        hybrid = HybridEmbedding()
        result = hybrid.encode_hybrid("test text", dense_weight=0.7, sparse_weight=0.3)

        assert isinstance(result, dict)
        assert "dense" in result
        assert "sparse" in result
        assert "weights" in result
        assert result["weights"]["dense"] == 0.7
        assert result["weights"]["sparse"] == 0.3
        mock_dense_encoder.encode.assert_called_once()


class TestCreateEmbeddings:
    """Test create_embeddings factory function."""

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_create_embeddings(self, mock_cuda, mock_st):
        """Test create_embeddings function."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        result = create_embeddings(model_name="all-MiniLM-L6-v2", device="cpu")

        assert isinstance(result, EmbeddingGenerator)
        assert result.model_name == "all-MiniLM-L6-v2"
        assert result.device == "cpu"

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_create_embeddings_auto_device(self, mock_cuda, mock_st):
        """Test create_embeddings with auto device detection."""
        mock_cuda.return_value = True
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        result = create_embeddings(model_name="test-model")

        assert isinstance(result, EmbeddingGenerator)
        assert result.device == "cuda"


class TestEmbeddingsEdgeCases:
    """Test edge cases for embeddings."""

    @patch('sentence_transformers.SentenceTransformer')
    @patch('torch.cuda.is_available')
    def test_encode_empty_list(self, mock_cuda, mock_st):
        """Test encoding empty list."""
        mock_cuda.return_value = False
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([])
        mock_st.return_value = mock_model

        gen = EmbeddingGenerator()
        result = gen.encode([])

        assert isinstance(result, np.ndarray)
        assert len(result) == 0

    @patch('src.ingestion.embeddings.EmbeddingGenerator')
    def test_hybrid_encode_sparse_empty(self, mock_eg_class):
        """Test encode_sparse with empty string."""
        mock_dense_encoder = Mock()
        mock_eg_class.return_value = mock_dense_encoder

        hybrid = HybridEmbedding()
        result = hybrid.encode_sparse("")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == {}  # Empty word frequency dict
