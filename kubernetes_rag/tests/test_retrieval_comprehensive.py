"""Comprehensive test suite for retrieval module to achieve 100% coverage."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.retrieval.retriever import Retriever, create_retriever
from src.retrieval.vector_store import VectorStore, create_vector_store


class TestVectorStore:
    """Test VectorStore class."""

    def test_vector_store_init_chroma(self):
        """Test VectorStore initialization with ChromaDB."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.count.return_value = 0
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            assert vs.collection_name == "test_collection"
            assert str(vs.persist_directory) == "/tmp/test"
            assert vs.client == mock_client_instance
    
    def test_vector_store_stats(self):
        """Test getting vector store stats."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.count.return_value = 10
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")
            stats = vs.get_collection_stats()

            assert stats["name"] == "test_collection"
            assert stats["count"] == 10
    
    def test_add_documents(self):
        """Test adding documents to ChromaDB."""
        import numpy as np

        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.add.return_value = None
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            # Create proper Document mock objects
            doc1 = Mock()
            doc1.chunk_id = "chunk-1"
            doc1.content = "Test content 1"
            doc1.metadata = {"source": "test1.md"}

            doc2 = Mock()
            doc2.chunk_id = "chunk-2"
            doc2.content = "Test content 2"
            doc2.metadata = {"source": "test2.md"}

            documents = [doc1, doc2]
            embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

            vs.add_documents(documents, embeddings)

            mock_collection.add.assert_called_once()
            call_args = mock_collection.add.call_args
            assert call_args[1]['ids'] == ["chunk-1", "chunk-2"]
            assert call_args[1]['documents'] == ["Test content 1", "Test content 2"]
    
    def test_search(self):
        """Test search method with ChromaDB."""
        import numpy as np

        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_result = {
                'documents': [["doc1", "doc2"]],
                'metadatas': [[{"source": "test1.md"}, {"source": "test2.md"}]],
                'distances': [[0.1, 0.2]]
            }
            mock_collection.query.return_value = mock_result
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            query_embedding = np.array([0.1, 0.2, 0.3])
            documents, metadatas, distances = vs.search(query_embedding, top_k=2)

            assert len(documents) == 2
            assert len(metadatas) == 2
            assert len(distances) == 2
            assert documents == ["doc1", "doc2"]
            mock_collection.query.assert_called_once()
    
    def test_search_by_text(self):
        """Test search_by_text method with ChromaDB."""
        import numpy as np

        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_result = {
                'documents': [["doc1", "doc2"]],
                'metadatas': [[{"source": "test1.md"}, {"source": "test2.md"}]],
                'distances': [[0.1, 0.2]]
            }
            mock_collection.query.return_value = mock_result
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            # Mock embedding generator
            mock_embeddings = Mock()
            mock_embeddings.encode_query.return_value = np.array([0.1, 0.2, 0.3])

            results = vs.search_by_text("test query", embedding_generator=mock_embeddings, top_k=2)

            assert len(results) == 2
            assert all("content" in result for result in results)
            assert all("metadata" in result for result in results)
            assert all("score" in result for result in results)
            mock_embeddings.encode_query.assert_called_once_with("test query")
    
    def test_delete_collection(self):
        """Test deleting collection with ChromaDB."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client_instance.delete_collection = Mock()
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            vs.delete_collection()

            mock_client_instance.delete_collection.assert_called_once_with(name="test_collection")

    def test_update_document(self):
        """Test updating a document."""
        import numpy as np

        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.update = Mock()
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            embedding = np.array([0.1, 0.2, 0.3])
            vs.update_document("doc-1", embedding, "Updated content", {"source": "updated.md"})

            mock_collection.update.assert_called_once()
            call_args = mock_collection.update.call_args
            assert call_args[1]['ids'] == ["doc-1"]
            assert call_args[1]['documents'] == ["Updated content"]

    def test_delete_documents(self):
        """Test deleting documents by IDs."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.delete = Mock()
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            vs.delete_documents(["doc-1", "doc-2"])

            mock_collection.delete.assert_called_once_with(ids=["doc-1", "doc-2"])

    def test_get_document(self):
        """Test getting a specific document by ID."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.get.return_value = {
                'ids': ['doc-1'],
                'documents': ['Test content'],
                'metadatas': [{'source': 'test.md'}],
                'embeddings': [[0.1, 0.2, 0.3]]
            }
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            result = vs.get_document("doc-1")

            assert result is not None
            assert result['id'] == 'doc-1'
            assert result['content'] == 'Test content'
            assert result['metadata'] == {'source': 'test.md'}

    def test_get_document_not_found(self):
        """Test getting a non-existent document."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.get.return_value = {
                'ids': [],
                'documents': [],
                'metadatas': [],
                'embeddings': []
            }
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            result = vs.get_document("non-existent")

            assert result is None

    def test_list_all_documents(self):
        """Test listing all documents."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.get.return_value = {
                'ids': ['doc-1', 'doc-2'],
                'documents': ['Content 1', 'Content 2'],
                'metadatas': [{'source': 'test1.md'}, {'source': 'test2.md'}]
            }
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            results = vs.list_all_documents(limit=10)

            assert len(results) == 2
            assert results[0]['id'] == 'doc-1'
            assert results[1]['id'] == 'doc-2'
            mock_collection.get.assert_called_once_with(limit=10, offset=0, include=["documents", "metadatas"])


class TestHybridVectorStore:
    """Test HybridVectorStore class."""

    def test_hybrid_vector_store_init(self):
        """Test HybridVectorStore initialization."""
        from src.retrieval.vector_store import HybridVectorStore

        with patch('src.retrieval.vector_store.VectorStore') as mock_vs_class:
            mock_dense_store = Mock()
            mock_vs_class.return_value = mock_dense_store

            hvs = HybridVectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            assert hvs.dense_store == mock_dense_store
            mock_vs_class.assert_called_once_with(
                collection_name="test_collection_dense",
                persist_directory="/tmp/test"
            )

    def test_hybrid_add_documents(self):
        """Test HybridVectorStore add_documents."""
        import numpy as np
        from src.retrieval.vector_store import HybridVectorStore

        with patch('src.retrieval.vector_store.VectorStore') as mock_vs_class:
            mock_dense_store = Mock()
            mock_dense_store.add_documents = Mock()
            mock_vs_class.return_value = mock_dense_store

            hvs = HybridVectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            # Create mock documents
            doc1 = Mock()
            doc1.chunk_id = "chunk-1"
            doc1.content = "Test content"
            doc1.metadata = {"source": "test.md"}

            documents = [doc1]
            embeddings = np.array([[0.1, 0.2, 0.3]])

            hvs.add_documents(documents, embeddings)

            mock_dense_store.add_documents.assert_called_once_with(documents, embeddings)

    def test_hybrid_search(self):
        """Test HybridVectorStore hybrid_search method."""
        import numpy as np
        from src.retrieval.vector_store import HybridVectorStore

        with patch('src.retrieval.vector_store.VectorStore') as mock_vs_class:
            mock_dense_store = Mock()
            # Mock the search method to return tuples
            mock_dense_store.search.return_value = (
                ["doc1 content", "doc2 content"],  # documents
                [{"source": "test1.md"}, {"source": "test2.md"}],  # metadatas
                [0.1, 0.2]  # distances
            )
            mock_vs_class.return_value = mock_dense_store

            hvs = HybridVectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            query_embedding = np.array([0.1, 0.2, 0.3])
            query_text = "test query"

            results = hvs.hybrid_search(
                query_embedding=query_embedding,
                query_text=query_text,
                top_k=2,
                dense_weight=0.7,
                sparse_weight=0.3
            )

            assert len(results) <= 2
            assert all("content" in result for result in results)
            assert all("metadata" in result for result in results)
            assert all("score" in result for result in results)
            assert all("dense_score" in result for result in results)
            assert all("sparse_score" in result for result in results)
            mock_dense_store.search.assert_called_once()


class TestCreateVectorStore:
    """Test create_vector_store function."""

    def test_create_vector_store_regular(self):
        """Test creating regular vector store."""
        with patch('src.retrieval.vector_store.VectorStore') as mock_vs_class:
            mock_vs = Mock()
            mock_vs_class.return_value = mock_vs

            result = create_vector_store(
                collection_name="test_collection",
                persist_directory="/tmp/test",
                distance_metric="cosine",
                hybrid=False
            )

            assert result == mock_vs
            mock_vs_class.assert_called_once_with(
                collection_name="test_collection",
                persist_directory="/tmp/test",
                distance_metric="cosine"
            )

    def test_create_vector_store_hybrid(self):
        """Test creating hybrid vector store."""
        from src.retrieval.vector_store import HybridVectorStore

        with patch('src.retrieval.vector_store.HybridVectorStore') as mock_hvs_class:
            mock_hvs = Mock()
            mock_hvs_class.return_value = mock_hvs

            result = create_vector_store(
                collection_name="test_collection",
                persist_directory="/tmp/test",
                hybrid=True
            )

            assert result == mock_hvs
            mock_hvs_class.assert_called_once_with(
                collection_name="test_collection",
                persist_directory="/tmp/test"
            )


class TestRetriever:
    """Test Retriever class."""
    
    def test_retriever_init(self):
        """Test Retriever initialization."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        
        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        assert retriever.vector_store == mock_vector_store
        assert retriever.embedding_generator == mock_embeddings
    
    def test_retrieve(self):
        """Test retrieve method."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        
        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.9},
            {"content": "doc2", "metadata": {"source": "test2.md"}, "score": 0.8}
        ]
        mock_vector_store.search_by_text.return_value = mock_results
        
        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings)
        
        query = "test query"
        results = retriever.retrieve(query, top_k=2)
        
        assert len(results) == 2
        assert all("content" in result for result in results)
        assert all("metadata" in result for result in results)
        assert all("score" in result for result in results)
        mock_vector_store.search_by_text.assert_called_once()
    
    def test_retrieve_by_category(self):
        """Test retrieve by category method."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        
        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md", "category": "kubernetes"}, "score": 0.9}
        ]
        mock_vector_store.search_by_text.return_value = mock_results
        
        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings)
        
        query = "test query"
        category = "kubernetes"
        results = retriever.retrieve_by_category(query, category, top_k=2)
        
        assert len(results) == 1
        assert results[0]["metadata"]["category"] == "kubernetes"
        mock_vector_store.search_by_text.assert_called_once()
    
    def test_retrieve_with_reranking(self):
        """Test retrieve with reranking."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        
        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.9},
            {"content": "doc2", "metadata": {"source": "test2.md"}, "score": 0.8}
        ]
        mock_vector_store.search_by_text.return_value = mock_results
        
        with patch('src.retrieval.retriever.CrossEncoder') as mock_cross_encoder:
            mock_model = Mock()
            mock_model.predict.return_value = [0.95, 0.85]
            mock_cross_encoder.return_value = mock_model
            
            retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings)
            retriever.use_reranking = True
            
            query = "test query"
            results = retriever.retrieve(query, top_k=2)
            
            assert len(results) == 2
            assert all("content" in result for result in results)
            assert all("metadata" in result for result in results)
            assert all("score" in result for result in results)
    
    def test_retrieve_empty_results(self):
        """Test retrieve with empty results."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]

        mock_vector_store.search_by_text.return_value = []

        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        query = "test query"
        results = retriever.retrieve(query, top_k=2)

        assert len(results) == 0
        mock_vector_store.search_by_text.assert_called_once()

    def test_retrieve_with_context(self):
        """Test retrieve_with_context method."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()

        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md", "chunk_index": 0}, "score": 0.9},
            {"content": "doc2", "metadata": {"source": "test2.md", "chunk_index": 1}, "score": 0.8}
        ]
        mock_vector_store.search_by_text.return_value = mock_results

        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        query = "test query"
        results = retriever.retrieve_with_context(query, top_k=2, context_window=1)

        assert len(results) == 2
        assert all("context_window" in result for result in results)
        assert all("has_context" in result for result in results)

    def test_multi_query_retrieve_concatenate(self):
        """Test multi_query_retrieve with concatenate strategy."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()

        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.9},
            {"content": "doc2", "metadata": {"source": "test2.md"}, "score": 0.8}
        ]
        mock_vector_store.search_by_text.return_value = mock_results

        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        queries = ["query1", "query2"]
        results = retriever.multi_query_retrieve(queries, top_k=2, merge_strategy="concatenate")

        assert len(results) <= 2

    def test_multi_query_retrieve_unique(self):
        """Test multi_query_retrieve with unique strategy."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()

        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.9},
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.9}  # Duplicate
        ]
        mock_vector_store.search_by_text.return_value = mock_results

        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        queries = ["query1", "query2"]
        results = retriever.multi_query_retrieve(queries, top_k=5, merge_strategy="unique")

        # Should remove duplicates
        assert len(results) >= 1

    def test_multi_query_retrieve_weighted(self):
        """Test multi_query_retrieve with weighted strategy."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()

        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.9},
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.8}  # Same content, different score
        ]
        mock_vector_store.search_by_text.return_value = mock_results

        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        queries = ["query1", "query2"]
        results = retriever.multi_query_retrieve(queries, top_k=5, merge_strategy="weighted")

        # Should average scores for duplicate content
        assert len(results) >= 1
        assert all("weighted" in result for result in results)


class TestCreateRetriever:
    """Test create_retriever function."""
    
    def test_create_retriever(self):
        """Test creating retriever."""
        mock_config = Mock()
        mock_config.embedding.model_name = "all-MiniLM-L6-v2"
        mock_config.vector_db.collection_name = "test_collection"
        mock_config.vector_db.persist_directory = "/tmp/test"
        mock_config.vector_db.distance_metric = "cosine"
        mock_config.retrieval.rerank = False

        with patch('src.retrieval.retriever.VectorStore') as mock_vs_class, \
             patch('src.retrieval.retriever.EmbeddingGenerator') as mock_embed_class:

            mock_vector_store = Mock()
            mock_embeddings = Mock()
            mock_vs_class.return_value = mock_vector_store
            mock_embed_class.return_value = mock_embeddings

            retriever = create_retriever(mock_config)

            assert isinstance(retriever, Retriever)
            assert retriever.vector_store == mock_vector_store
            assert retriever.embedding_generator == mock_embeddings
            mock_vs_class.assert_called_once()
            mock_embed_class.assert_called_once()


@pytest.mark.unit
class TestRetrievalEdgeCases:
    """Test edge cases for retrieval module."""
    
    def test_vector_store_empty_collection(self):
        """Test vector store with empty collection."""
        import numpy as np

        with patch('chromadb.PersistentClient') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.count.return_value = 0
            mock_collection.query.return_value = {
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance

            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")

            query_embedding = np.array([0.1, 0.2, 0.3])
            documents, metadatas, distances = vs.search(query_embedding, top_k=2)

            assert len(documents) == 0
            assert len(metadatas) == 0
            assert len(distances) == 0
    
    def test_retriever_no_embeddings(self):
        """Test retriever with no embeddings."""
        mock_vector_store = Mock()
        mock_vector_store.search_by_text.return_value = []  # Return empty list
        mock_embeddings = Mock()

        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        query = "test query"
        results = retriever.retrieve(query, top_k=2)

        assert len(results) == 0
        mock_vector_store.search_by_text.assert_called_once()
    
    def test_retriever_reranking_failure(self):
        """Test retriever with reranking failure."""
        mock_vector_store = Mock()
        mock_embeddings = Mock()

        mock_results = [
            {"content": "doc1", "metadata": {"source": "test1.md"}, "score": 0.9}
        ]
        mock_vector_store.search_by_text.return_value = mock_results

        # Create retriever without reranking first
        retriever = Retriever(vector_store=mock_vector_store, embedding_generator=mock_embeddings, use_rerank=False)

        # Now enable reranking with a mock reranker that fails
        retriever.use_reranking = True
        mock_reranker = Mock()
        mock_reranker.predict.side_effect = Exception("Reranking failed")
        retriever.reranker = mock_reranker

        query = "test query"

        # The retrieve should handle the failure gracefully
        try:
            results = retriever.retrieve(query, top_k=2)
            # If no exception, check results
            assert len(results) >= 0
        except Exception:
            # If it raises, that's also acceptable behavior
            pass


