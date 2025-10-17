"""Integration tests for API endpoints."""

import json

# Set up test environment before importing API
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

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

from src.api import app
from src.generation.llm import RAGGenerator
from src.ingestion.document_processor import Document
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore


class TestAPIIntegration:
    """Test API integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_store = VectorStore(
                collection_name="test_api", persist_directory=temp_dir
            )

            # Add some test documents
            documents = [
                Document(
                    content="Kubernetes is a container orchestration platform",
                    metadata={"source": "test.md", "type": "kubernetes_doc"},
                    chunk_id="test_1",
                ),
                Document(
                    content="Question: What is a Pod? Answer: A Pod is the smallest deployable unit in Kubernetes.",
                    metadata={"source": "test.md", "type": "qa_pair"},
                    chunk_id="test_2",
                ),
            ]

            # Mock embeddings
            import numpy as np

            embeddings = np.random.rand(len(documents), 384)
            vector_store.add_documents(documents, embeddings)

            yield {"vector_store": vector_store, "documents": documents}

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_health_detailed_endpoint(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    @patch("src.api.retriever")
    @patch("src.api.generator")
    def test_query_endpoint(
        self, mock_generator, mock_retriever, client, mock_components
    ):
        """Test query endpoint."""
        # Mock retriever response
        mock_retriever.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md", "type": "kubernetes_doc"},
                "score": 0.9,
            }
        ]

        # Mock generator response
        mock_generator.generate_answer.return_value = {
            "query": "What is Kubernetes?",
            "answer": "Kubernetes is a container orchestration platform.",
            "num_sources": 1,
        }

        # Test query request
        request_data = {
            "query": "What is Kubernetes?",
            "top_k": 3,
            "generate_answer": True,
            "temperature": 0.3,
        }

        response = client.post("/query", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "What is Kubernetes?"
        assert "answer" in data
        assert "documents" in data
        assert "num_sources" in data
        assert len(data["documents"]) > 0

    @patch("src.api.retriever")
    def test_query_endpoint_no_answer(self, mock_retriever, client):
        """Test query endpoint without generating answer."""
        # Mock retriever response
        mock_retriever.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md", "type": "kubernetes_doc"},
                "score": 0.9,
            }
        ]

        # Test query request without answer generation
        request_data = {
            "query": "What is Kubernetes?",
            "top_k": 3,
            "generate_answer": False,
        }

        response = client.post("/query", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "What is Kubernetes?"
        assert "answer" not in data
        assert "documents" in data
        assert "num_sources" in data

    @patch("src.api.retriever")
    def test_query_endpoint_no_results(self, mock_retriever, client):
        """Test query endpoint when no results are found."""
        # Mock empty retriever response
        mock_retriever.retrieve.return_value = []

        request_data = {
            "query": "Non-existent topic",
            "top_k": 3,
            "generate_answer": True,
        }

        response = client.post("/query", json=request_data)
        assert response.status_code == 404

        data = response.json()
        assert "No relevant documents found" in data["detail"]

    @patch("src.api.retriever")
    def test_search_endpoint(self, mock_retriever, client):
        """Test search endpoint."""
        # Mock retriever response
        mock_retriever.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md", "type": "kubernetes_doc"},
                "score": 0.9,
            },
            {
                "content": "Docker is a containerization platform",
                "metadata": {"source": "test.md", "type": "kubernetes_doc"},
                "score": 0.8,
            },
        ]

        request_data = {
            "query": "container platform",
            "top_k": 5,
            "score_threshold": 0.5,
        }

        response = client.post("/search", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "container platform"
        assert "results" in data
        assert "total_results" in data
        assert len(data["results"]) == 2
        assert data["total_results"] == 2

    @patch("src.api.retriever")
    def test_search_endpoint_with_category(self, mock_retriever, client):
        """Test search endpoint with category filtering."""
        # Mock retriever response
        mock_retriever.retrieve_by_category.return_value = [
            {
                "content": "Question: What is a Pod? Answer: A Pod is the smallest deployable unit.",
                "metadata": {"source": "test.md", "type": "qa_pair"},
                "score": 0.9,
            }
        ]

        request_data = {"query": "What is a Pod?", "top_k": 5, "category": "qa_pair"}

        response = client.post("/search", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "What is a Pod?"
        assert len(data["results"]) == 1
        assert data["results"][0]["metadata"]["type"] == "qa_pair"

    @patch("src.api.pipeline")
    def test_ingest_endpoint(self, mock_pipeline, client):
        """Test ingest endpoint."""
        # Mock pipeline response
        mock_pipeline.ingest_from_text.return_value = 3

        request_data = {
            "text": "Kubernetes is a container orchestration platform. It automates deployment and scaling.",
            "metadata": {"source": "api_test"},
            "source_name": "api_upload",
        }

        response = client.post("/ingest", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["chunks_created"] == 3
        assert data["source_name"] == "api_upload"

    @patch("src.api.VectorStore")
    def test_stats_endpoint(self, mock_vector_store_class, client):
        """Test stats endpoint."""
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store.get_collection_stats.return_value = {
            "name": "test_collection",
            "count": 150,
            "persist_directory": "/tmp/test_db",
        }
        mock_vector_store_class.return_value = mock_vector_store

        response = client.get("/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["collection_name"] == "test_collection"
        assert data["document_count"] == 150
        assert data["persist_directory"] == "/tmp/test_db"

    def test_categories_endpoint(self, client):
        """Test categories endpoint."""
        response = client.get("/categories")
        assert response.status_code == 200

        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 2

        # Check category structure
        categories = data["categories"]
        qa_category = next(cat for cat in categories if cat["id"] == "qa_pair")
        doc_category = next(cat for cat in categories if cat["id"] == "kubernetes_doc")

        assert qa_category["name"] == "Q&A Pairs"
        assert doc_category["name"] == "Kubernetes Documentation"

    def test_invalid_query_request(self, client):
        """Test invalid query request."""
        # Missing required field
        request_data = {"top_k": 3}

        response = client.post("/query", json=request_data)
        assert response.status_code == 422

    def test_invalid_search_request(self, client):
        """Test invalid search request."""
        # Invalid score threshold
        request_data = {
            "query": "test",
            "score_threshold": 2.0,  # Should be between 0 and 1
        }

        response = client.post("/search", json=request_data)
        assert response.status_code == 422

    def test_invalid_ingest_request(self, client):
        """Test invalid ingest request."""
        # Missing required text field
        request_data = {"metadata": {"source": "test"}}

        response = client.post("/ingest", json=request_data)
        assert response.status_code == 422

    @patch("src.api.retriever")
    def test_query_endpoint_error_handling(self, mock_retriever, client):
        """Test query endpoint error handling."""
        # Mock retriever to raise an exception
        mock_retriever.retrieve.side_effect = Exception("Database connection failed")

        request_data = {"query": "What is Kubernetes?", "top_k": 3}

        response = client.post("/query", json=request_data)
        assert response.status_code == 500

        data = response.json()
        assert "Database connection failed" in data["detail"]

    @patch("src.api.pipeline")
    def test_ingest_endpoint_error_handling(self, mock_pipeline, client):
        """Test ingest endpoint error handling."""
        # Mock pipeline to raise an exception
        mock_pipeline.ingest_from_text.side_effect = Exception("Processing failed")

        request_data = {"text": "Test content", "source_name": "test"}

        response = client.post("/ingest", json=request_data)
        assert response.status_code == 500

        data = response.json()
        assert "Processing failed" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
