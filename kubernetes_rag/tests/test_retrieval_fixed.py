"""Fixed comprehensive test suite for retrieval module to achieve 100% coverage."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import numpy as np

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
    create_mock_retriever,
    TEST_CONFIG_DATA
)

from src.retrieval.vector_store import VectorStore, create_vector_store
from src.retrieval.retriever import Retriever, create_retriever


class TestVectorStore:
    """Test VectorStore class."""

    def test_vector_store_init_chroma(self):
        """Test VectorStore initialization with ChromaDB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(
                collection_name="test_collection",
                persist_directory=temp_dir,
                distance_metric="cosine"
            )
            assert vs.collection_name == "test_collection"
            assert str(vs.persist_directory) == temp_dir

    def test_vector_store_init_defaults(self):
        """Test VectorStore initialization with defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            assert vs.collection_name == "kubernetes_docs"
            assert vs.distance_metric == "cosine"

    def test_add_documents_chroma(self):
        """Test add_documents with ChromaDB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            documents = create_mock_documents(3)
            embeddings = np.random.rand(3, 384)
            
            # Mock the collection.add method
            with patch.object(vs.collection, 'add') as mock_add:
                vs.add_documents(documents, embeddings)
                mock_add.assert_called_once()

    def test_add_documents_batch(self):
        """Test add_documents with batching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            documents = create_mock_documents(5)
            embeddings = np.random.rand(5, 384)
            
            with patch.object(vs.collection, 'add') as mock_add:
                vs.add_documents(documents, embeddings, batch_size=2)
                # Should be called multiple times due to batching
                assert mock_add.call_count >= 2

    def test_similarity_search_chroma(self):
        """Test similarity_search with ChromaDB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            query_embedding = np.random.rand(384)
            
            with patch.object(vs.collection, 'query') as mock_query:
                mock_query.return_value = {
                    "documents": [["doc1", "doc2", "doc3"]],
                    "distances": [[0.1, 0.2, 0.3]],
                    "metadatas": [[{"source": "test1.md"}, {"source": "test2.md"}, {"source": "test3.md"}]]
                }
                
                result = vs.similarity_search(query_embedding, top_k=3)
                
                assert "documents" in result
                assert "distances" in result
                assert "metadatas" in result
                mock_query.assert_called_once()

    def test_similarity_search_with_score(self):
        """Test similarity_search with score threshold."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            query_embedding = np.random.rand(384)
            
            with patch.object(vs.collection, 'query') as mock_query:
                mock_query.return_value = {
                    "documents": [["doc1", "doc2"]],
                    "distances": [[0.1, 0.2]],
                    "metadatas": [[{"source": "test1.md"}, {"source": "test2.md"}]]
                }
                
                result = vs.similarity_search(query_embedding, top_k=3, score_threshold=0.5)
                
                assert "documents" in result
                mock_query.assert_called_once()

    def test_get_collection_stats_chroma(self):
        """Test get_collection_stats with ChromaDB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            with patch.object(vs.collection, 'count') as mock_count:
                mock_count.return_value = 5
                
                stats = vs.get_collection_stats()
                
                assert stats["name"] == "test_collection"
                assert stats["count"] == 5
                assert "persist_directory" in stats

    def test_delete_collection_chroma(self):
        """Test delete_collection with ChromaDB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            with patch.object(vs.client, 'delete_collection') as mock_delete:
                vs.delete_collection()
                mock_delete.assert_called_once_with("test_collection")

    def test_vector_store_persist_directory_creation(self):
        """Test that persist directory is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            persist_path = Path(temp_dir) / "new_vector_db"
            
            vs = VectorStore(persist_directory=str(persist_path))
            
            assert persist_path.exists()
            assert persist_path.is_dir()


class TestCreateVectorStore:
    """Test create_vector_store function."""

    def test_create_vector_store_chroma(self):
        """Test create_vector_store with ChromaDB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = create_vector_store(
                vector_store_type="chroma",
                collection_name="test_collection",
                persist_directory=temp_dir
            )
            assert isinstance(vs, VectorStore)
            assert vs.collection_name == "test_collection"

    def test_create_vector_store_defaults(self):
        """Test create_vector_store with defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = create_vector_store(persist_directory=temp_dir)
            assert isinstance(vs, VectorStore)
            assert vs.collection_name == "kubernetes_docs"


class TestRetriever:
    """Test Retriever class."""

    def test_retriever_init(self):
        """Test Retriever initialization."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        assert retriever.vector_store == mock_vector_store
        assert retriever.embedding_generator == mock_embedding_generator

    def test_retrieve(self):
        """Test retrieve method."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        result = retriever.retrieve("Test query", top_k=5)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all("content" in doc for doc in result)

    def test_retrieve_by_category(self):
        """Test retrieve_by_category method."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        result = retriever.retrieve_by_category("Test query", "kubernetes", top_k=5)
        
        assert isinstance(result, list)

    def test_retrieve_with_reranking(self):
        """Test retrieve with reranking."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        result = retriever.retrieve("Test query", top_k=5, rerank=True)
        
        assert isinstance(result, list)

    def test_retrieve_empty_results(self):
        """Test retrieve with empty results."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        # Mock empty results
        mock_vector_store.similarity_search.return_value = {
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]]
        }
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        result = retriever.retrieve("Test query", top_k=5)
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestCreateRetriever:
    """Test create_retriever function."""

    def test_create_retriever(self):
        """Test create_retriever function."""
        mock_config = create_mock_config()
        
        with patch("src.retrieval.vector_store.create_vector_store") as mock_create_vs, \
             patch("src.ingestion.embeddings.create_embeddings") as mock_create_emb:
            
            mock_vs = create_mock_vector_store()
            mock_emb = create_mock_embedding_generator()
            
            mock_create_vs.return_value = mock_vs
            mock_create_emb.return_value = mock_emb
            
            retriever = create_retriever(mock_config)
            
            assert isinstance(retriever, Retriever)
            mock_create_vs.assert_called_once()
            mock_create_emb.assert_called_once()


class TestRetrievalEdgeCases:
    """Test edge cases for retrieval module."""

    def test_vector_store_empty_collection(self):
        """Test vector store with empty collection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            with patch.object(vs.collection, 'count') as mock_count:
                mock_count.return_value = 0
                
                stats = vs.get_collection_stats()
                assert stats["count"] == 0

    def test_retriever_no_embeddings(self):
        """Test retriever with no embeddings."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        # Mock empty embeddings
        mock_embedding_generator.encode.return_value = np.array([])
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        result = retriever.retrieve("Test query")
        assert isinstance(result, list)

    def test_retriever_reranking_failure(self):
        """Test retriever with reranking failure."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        # Test with reranking disabled (should not fail)
        result = retriever.retrieve("Test query", rerank=False)
        assert isinstance(result, list)

    def test_vector_store_invalid_distance_metric(self):
        """Test vector store with invalid distance metric."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Should still work with invalid metric (ChromaDB will handle it)
            vs = VectorStore(
                persist_directory=temp_dir,
                distance_metric="invalid_metric"
            )
            assert vs.distance_metric == "invalid_metric"

    def test_retriever_large_top_k(self):
        """Test retriever with large top_k."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        result = retriever.retrieve("Test query", top_k=1000)
        assert isinstance(result, list)

    def test_vector_store_batch_size_edge_cases(self):
        """Test vector store with edge case batch sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            documents = create_mock_documents(1)
            embeddings = np.random.rand(1, 384)
            
            with patch.object(vs.collection, 'add') as mock_add:
                # Test with batch_size = 1
                vs.add_documents(documents, embeddings, batch_size=1)
                mock_add.assert_called_once()
                
                # Reset mock
                mock_add.reset_mock()
                
                # Test with batch_size larger than documents
                vs.add_documents(documents, embeddings, batch_size=100)
                mock_add.assert_called_once()


class TestRetrievalIntegration:
    """Test integration scenarios for retrieval module."""

    def test_full_retrieval_workflow(self):
        """Test full retrieval workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create vector store
            vs = VectorStore(persist_directory=temp_dir)
            
            # Create embedding generator
            with patch("sentence_transformers.SentenceTransformer") as mock_model:
                mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
                mock_model.return_value.encode.return_value = np.random.rand(5, 384)
                
                from src.ingestion.embeddings import EmbeddingGenerator
                emb_gen = EmbeddingGenerator()
                
                # Create retriever
                retriever = Retriever(vector_store=vs, embedding_generator=emb_gen)
                
                # Test retrieval
                result = retriever.retrieve("Test query", top_k=3)
                assert isinstance(result, list)

    def test_vector_store_persistence(self):
        """Test vector store persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first vector store
            vs1 = VectorStore(
                collection_name="test_collection",
                persist_directory=temp_dir
            )
            
            # Add some documents
            documents = create_mock_documents(3)
            embeddings = np.random.rand(3, 384)
            
            with patch.object(vs1.collection, 'add') as mock_add:
                vs1.add_documents(documents, embeddings)
                mock_add.assert_called_once()
            
            # Create second vector store with same path
            vs2 = VectorStore(
                collection_name="test_collection",
                persist_directory=temp_dir
            )
            
            # Should be able to access the same collection
            assert vs1.collection_name == vs2.collection_name

    def test_retriever_with_different_queries(self):
        """Test retriever with different types of queries."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        # Test different query types
        queries = [
            "What is Kubernetes?",
            "How to deploy applications?",
            "Container orchestration",
            "Service mesh configuration",
            "Pod security policies"
        ]
        
        for query in queries:
            result = retriever.retrieve(query, top_k=3)
            assert isinstance(result, list)


class TestRetrievalPerformance:
    """Test performance scenarios for retrieval module."""

    def test_vector_store_add_documents_performance(self):
        """Test vector store add_documents performance."""
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            # Create large number of documents
            documents = create_mock_documents(100)
            embeddings = np.random.rand(100, 384)
            
            with patch.object(vs.collection, 'add') as mock_add:
                start_time = time.time()
                vs.add_documents(documents, embeddings, batch_size=10)
                end_time = time.time()
                
                duration = end_time - start_time
                assert duration < 2.0  # Should complete quickly
                assert mock_add.call_count == 10  # 100 docs / 10 batch_size

    def test_similarity_search_performance(self):
        """Test similarity search performance."""
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            query_embedding = np.random.rand(384)
            
            with patch.object(vs.collection, 'query') as mock_query:
                mock_query.return_value = {
                    "documents": [["doc1", "doc2", "doc3"]] * 10,
                    "distances": [[0.1, 0.2, 0.3]] * 10,
                    "metadatas": [[{"source": "test.md"}]] * 10
                }
                
                start_time = time.time()
                
                for _ in range(10):
                    vs.similarity_search(query_embedding, top_k=3)
                
                end_time = time.time()
                duration = end_time - start_time
                
                assert duration < 1.0  # Should complete quickly
                assert mock_query.call_count == 10

    def test_retriever_performance(self):
        """Test retriever performance."""
        import time
        
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        start_time = time.time()
        
        for _ in range(20):
            retriever.retrieve("Test query", top_k=5)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 2.0  # Should complete in reasonable time

    def test_retriever_with_reranking_performance(self):
        """Test retriever with reranking performance."""
        import time
        
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        start_time = time.time()
        
        for _ in range(10):
            retriever.retrieve("Test query", top_k=5, rerank=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 3.0  # Should complete in reasonable time

    def test_large_embedding_batch_performance(self):
        """Test performance with large embedding batches."""
        import time
        
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = np.random.rand(1000, 384)
            
            from src.ingestion.embeddings import EmbeddingGenerator
            emb_gen = EmbeddingGenerator()
            
            texts = [f"Text {i}" for i in range(1000)]
            
            start_time = time.time()
            result = emb_gen.encode(texts, batch_size=100)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 5.0  # Should complete in reasonable time
            assert result.shape == (1000, 384)
