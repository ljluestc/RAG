"""Comprehensive test suite for API module to achieve 100% coverage."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up test environment before importing API
os.environ.update(
    {
        "OPENAI_API_KEY": "test-key-12345",
        "ANTHROPIC_API_KEY": "test-key-12345",
        "PERPLEXITY_API_KEY": "test-key-12345",
        "GOOGLE_API_KEY": "test-key-12345",
        "MISTRAL_API_KEY": "test-key-12345",
        "XAI_API_KEY": "test-key-12345",
        "OPENROUTER_API_KEY": "test-key-12345",
        "AZURE_OPENAI_API_KEY": "test-key-12345",
        "OLLAMA_API_KEY": "test-key-12345",
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
    }
)

from src.api import app, create_app


class TestAPICreation:
    """Test API creation and initialization."""

    def test_app_exists(self):
        """Test that FastAPI app exists."""
        assert app is not None

    def test_create_app(self):
        """Test create_app function."""
        with patch("src.utils.config_loader.get_config") as mock_get_config:
            mock_config = Mock()
            mock_settings = Mock()
            mock_get_config.return_value = (mock_config, mock_settings)

            test_app = create_app()

            assert test_app is not None
            assert test_app.title == "Kubernetes RAG API"

    def test_app_routes(self):
        """Test that app has all required routes."""
        client = TestClient(app)

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200

        # Test docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200


class TestHealthEndpoint:
    """Test health endpoint."""

    def test_health_get(self):
        """Test GET /health endpoint."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_post(self):
        """Test POST /health endpoint."""
        client = TestClient(app)
        response = client.post("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestQueryEndpoint:
    """Test query endpoint."""

    def test_query_post_success(self):
        """Test successful POST /query endpoint."""
        client = TestClient(app)

        with patch("src.generation.llm.create_rag_generator") as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": [],
            }
            mock_create_generator.return_value = mock_generator

            response = client.post("/query", json={"query": "Test query", "top_k": 5})

            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "Test answer"
            assert data["query"] == "Test query"

    def test_query_post_missing_query(self):
        """Test POST /query with missing query."""
        client = TestClient(app)

        response = client.post("/query", json={})

        assert response.status_code == 422

    def test_query_post_invalid_json(self):
        """Test POST /query with invalid JSON."""
        client = TestClient(app)

        response = client.post("/query", data="invalid json")

        assert response.status_code == 422

    def test_query_post_generator_error(self):
        """Test POST /query with generator error."""
        client = TestClient(app)

        with patch("src.generation.llm.create_rag_generator") as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.side_effect = Exception("Generator error")
            mock_create_generator.return_value = mock_generator

            response = client.post("/query", json={"query": "Test query"})

            assert response.status_code == 500

    def test_query_get_method_not_allowed(self):
        """Test GET /query method not allowed."""
        client = TestClient(app)

        response = client.get("/query")

        assert response.status_code == 405


class TestSearchEndpoint:
    """Test search endpoint."""

    def test_search_post_success(self):
        """Test successful POST /search endpoint."""
        client = TestClient(app)

        with patch("src.retrieval.retriever.create_retriever") as mock_create_retriever:
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = [
                {
                    "content": "Test document",
                    "metadata": {"source": "test.md"},
                    "score": 0.9,
                }
            ]
            mock_create_retriever.return_value = mock_retriever

            response = client.post("/search", json={"query": "Test query", "top_k": 5})

            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["content"] == "Test document"

    def test_search_post_missing_query(self):
        """Test POST /search with missing query."""
        client = TestClient(app)

        response = client.post("/search", json={})

        assert response.status_code == 422

    def test_search_post_retriever_error(self):
        """Test POST /search with retriever error."""
        client = TestClient(app)

        with patch("src.retrieval.retriever.create_retriever") as mock_create_retriever:
            mock_retriever = Mock()
            mock_retriever.retrieve.side_effect = Exception("Retriever error")
            mock_create_retriever.return_value = mock_retriever

            response = client.post("/search", json={"query": "Test query"})

            assert response.status_code == 500

    def test_search_get_method_not_allowed(self):
        """Test GET /search method not allowed."""
        client = TestClient(app)

        response = client.get("/search")

        assert response.status_code == 405


class TestIngestEndpoint:
    """Test ingest endpoint."""

    def test_ingest_post_success(self):
        """Test successful POST /ingest endpoint."""
        client = TestClient(app)

        with patch(
            "src.ingestion.pipeline.create_ingestion_pipeline"
        ) as mock_create_pipeline:
            mock_pipeline = Mock()
            mock_pipeline.ingest_file.return_value = 5
            mock_create_pipeline.return_value = mock_pipeline

            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write("# Test Document\n\nSome content.")
                f.flush()

                try:
                    response = client.post("/ingest", json={"file_path": f.name})

                    assert response.status_code == 200
                    data = response.json()
                    assert data["chunks_ingested"] == 5
                finally:
                    os.unlink(f.name)

    def test_ingest_post_missing_file_path(self):
        """Test POST /ingest with missing file_path."""
        client = TestClient(app)

        response = client.post("/ingest", json={})

        assert response.status_code == 422

    def test_ingest_post_file_not_found(self):
        """Test POST /ingest with non-existent file."""
        client = TestClient(app)

        response = client.post("/ingest", json={"file_path": "non_existent_file.md"})

        assert response.status_code == 404

    def test_ingest_post_pipeline_error(self):
        """Test POST /ingest with pipeline error."""
        client = TestClient(app)

        with patch(
            "src.ingestion.pipeline.create_ingestion_pipeline"
        ) as mock_create_pipeline:
            mock_pipeline = Mock()
            mock_pipeline.ingest_file.side_effect = Exception("Pipeline error")
            mock_create_pipeline.return_value = mock_pipeline

            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write("# Test Document\n\nSome content.")
                f.flush()

                try:
                    response = client.post("/ingest", json={"file_path": f.name})

                    assert response.status_code == 500
                finally:
                    os.unlink(f.name)

    def test_ingest_get_method_not_allowed(self):
        """Test GET /ingest method not allowed."""
        client = TestClient(app)

        response = client.get("/ingest")

        assert response.status_code == 405


class TestStatsEndpoint:
    """Test stats endpoint."""

    def test_stats_get_success(self):
        """Test successful GET /stats endpoint."""
        client = TestClient(app)

        with patch("src.retrieval.vector_store.create_vector_store") as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.get_collection_stats.return_value = {
                "name": "test_collection",
                "count": 100,
                "persist_directory": "/tmp/test",
            }
            mock_create_vs.return_value = mock_vector_store

            response = client.get("/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["collection_name"] == "test_collection"
            assert data["document_count"] == 100

    def test_stats_get_vector_store_error(self):
        """Test GET /stats with vector store error."""
        client = TestClient(app)

        with patch("src.retrieval.vector_store.create_vector_store") as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.get_collection_stats.side_effect = Exception(
                "Vector store error"
            )
            mock_create_vs.return_value = mock_vector_store

            response = client.get("/stats")

            assert response.status_code == 500

    def test_stats_post_method_not_allowed(self):
        """Test POST /stats method not allowed."""
        client = TestClient(app)

        response = client.post("/stats")

        assert response.status_code == 405


class TestResetEndpoint:
    """Test reset endpoint."""

    def test_reset_post_success(self):
        """Test successful POST /reset endpoint."""
        client = TestClient(app)

        with patch("src.retrieval.vector_store.create_vector_store") as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.delete_collection.return_value = None
            mock_create_vs.return_value = mock_vector_store

            response = client.post("/reset")

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Vector database reset successfully"

    def test_reset_post_vector_store_error(self):
        """Test POST /reset with vector store error."""
        client = TestClient(app)

        with patch("src.retrieval.vector_store.create_vector_store") as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.delete_collection.side_effect = Exception(
                "Vector store error"
            )
            mock_create_vs.return_value = mock_vector_store

            response = client.post("/reset")

            assert response.status_code == 500

    def test_reset_get_method_not_allowed(self):
        """Test GET /reset method not allowed."""
        client = TestClient(app)

        response = client.get("/reset")

        assert response.status_code == 405


@pytest.mark.unit
class TestAPIEdgeCases:
    """Test edge cases for API module."""

    def test_query_with_empty_documents(self):
        """Test query with empty documents."""
        client = TestClient(app)

        with patch("src.generation.llm.create_rag_generator") as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "No documents found",
                "query": "Test query",
                "documents": [],
            }
            mock_create_generator.return_value = mock_generator

            response = client.post("/query", json={"query": "Test query"})

            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "No documents found"

    def test_search_with_empty_results(self):
        """Test search with empty results."""
        client = TestClient(app)

        with patch("src.retrieval.retriever.create_retriever") as mock_create_retriever:
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = []
            mock_create_retriever.return_value = mock_retriever

            response = client.post("/search", json={"query": "Test query"})

            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 0

    def test_ingest_with_unsupported_file_format(self):
        """Test ingest with unsupported file format."""
        client = TestClient(app)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write("Some content")
            f.flush()

            try:
                response = client.post("/ingest", json={"file_path": f.name})

                assert response.status_code == 400
            finally:
                os.unlink(f.name)

    def test_stats_with_empty_collection(self):
        """Test stats with empty collection."""
        client = TestClient(app)

        with patch("src.retrieval.vector_store.create_vector_store") as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.get_collection_stats.return_value = {
                "name": "test_collection",
                "count": 0,
                "persist_directory": "/tmp/test",
            }
            mock_create_vs.return_value = mock_vector_store

            response = client.get("/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["document_count"] == 0


@pytest.mark.integration
class TestAPIIntegration:
    """Test API integration scenarios."""

    def test_full_workflow(self):
        """Test full workflow: ingest -> search -> query."""
        client = TestClient(app)

        # Mock all dependencies
        with patch(
            "src.ingestion.pipeline.create_ingestion_pipeline"
        ) as mock_create_pipeline, patch(
            "src.retrieval.retriever.create_retriever"
        ) as mock_create_retriever, patch(
            "src.generation.llm.create_rag_generator"
        ) as mock_create_generator:

            # Setup mocks
            mock_pipeline = Mock()
            mock_pipeline.ingest_file.return_value = 3
            mock_create_pipeline.return_value = mock_pipeline

            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = [
                {
                    "content": "Test document",
                    "metadata": {"source": "test.md"},
                    "score": 0.9,
                }
            ]
            mock_create_retriever.return_value = mock_retriever

            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": [],
            }
            mock_create_generator.return_value = mock_generator

            # Test ingest
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write("# Test Document\n\nSome content.")
                f.flush()

                try:
                    response = client.post("/ingest", json={"file_path": f.name})
                    assert response.status_code == 200

                    # Test search
                    response = client.post("/search", json={"query": "Test query"})
                    assert response.status_code == 200

                    # Test query
                    response = client.post("/query", json={"query": "Test query"})
                    assert response.status_code == 200

                finally:
                    os.unlink(f.name)

    def test_error_handling_chain(self):
        """Test error handling across multiple endpoints."""
        client = TestClient(app)

        # Test with missing API keys
        with patch.dict(os.environ, {}, clear=True):
            response = client.get("/health")
            assert response.status_code == 200  # Health should still work

            response = client.post("/query", json={"query": "Test"})
            assert response.status_code == 500  # Query should fail
