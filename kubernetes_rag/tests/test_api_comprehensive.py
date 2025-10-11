"""Comprehensive test suite for API module to achieve 100% coverage."""

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.api import app, create_app
from src.utils.config_loader import get_config


class TestAPICreation:
    """Test API creation and initialization."""

    def test_create_app(self):
        """Test app creation."""
        test_app = create_app()

        assert test_app is not None
        assert isinstance(test_app, FastAPI)

    def test_app_instance(self):
        """Test app instance."""
        assert app is not None
        assert isinstance(app, FastAPI)

    def test_app_title(self):
        """Test app title."""
        assert app.title is not None
        assert isinstance(app.title, str)
        assert len(app.title) > 0

    def test_app_version(self):
        """Test app version."""
        assert app.version is not None
        assert isinstance(app.version, str)


class TestAPIEndpoints:
    """Test API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test health endpoint."""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_stats_endpoint(self):
        """Test stats endpoint."""
        response = self.client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @patch("src.api.create_retriever")
    @patch("src.api.create_rag_generator")
    def test_query_endpoint_success(self, mock_generator, mock_retriever):
        """Test successful query endpoint."""
        # Mock retriever and generator
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        mock_generator_instance = Mock()
        mock_generator_instance.generate_answer.return_value = {
            "answer": "Test answer",
            "sources": [],
            "metadata": {},
        }
        mock_generator.return_value = mock_generator_instance

        query_data = {
            "query": "What is Kubernetes?",
            "top_k": 5,
            "generate_answer": True,
        }

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "metadata" in data

    def test_query_endpoint_missing_query(self):
        """Test query endpoint with missing query."""
        query_data = {"top_k": 5, "generate_answer": True}

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 422  # Validation error

    def test_query_endpoint_invalid_query(self):
        """Test query endpoint with invalid query."""
        query_data = {"query": "", "top_k": 5, "generate_answer": True}  # Empty query

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 422  # Validation error

    @patch("src.api.create_retriever")
    def test_search_endpoint_success(self, mock_retriever):
        """Test successful search endpoint."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        search_data = {
            "query": "Kubernetes deployment",
            "top_k": 5,
            "category": "qa_pair",
            "score_threshold": 0.7,
        }

        response = self.client.post("/search", json=search_data)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_search_endpoint_missing_query(self):
        """Test search endpoint with missing query."""
        search_data = {"top_k": 5, "category": "qa_pair"}

        response = self.client.post("/search", json=search_data)

        assert response.status_code == 422  # Validation error

    @patch("src.api.create_ingestion_pipeline")
    def test_ingest_endpoint_success(self, mock_pipeline):
        """Test successful ingest endpoint."""
        # Mock pipeline
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.ingest_from_text.return_value = {
            "chunks_created": 1,
            "source_name": "test_source",
        }
        mock_pipeline.return_value = mock_pipeline_instance

        ingest_data = {
            "text": "Test Kubernetes content",
            "metadata": {"source": "test"},
            "source_name": "test_document",
        }

        response = self.client.post("/ingest", json=ingest_data)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "chunks_created" in data

    def test_ingest_endpoint_missing_text(self):
        """Test ingest endpoint with missing text."""
        ingest_data = {"metadata": {"source": "test"}, "source_name": "test_document"}

        response = self.client.post("/ingest", json=ingest_data)

        assert response.status_code == 422  # Validation error

    def test_ingest_endpoint_empty_text(self):
        """Test ingest endpoint with empty text."""
        ingest_data = {
            "text": "",  # Empty text
            "metadata": {"source": "test"},
            "source_name": "test_document",
        }

        response = self.client.post("/ingest", json=ingest_data)

        assert response.status_code == 422  # Validation error


class TestAPIErrorHandling:
    """Test API error handling."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("src.api.create_retriever")
    def test_query_endpoint_retriever_error(self, mock_retriever):
        """Test query endpoint with retriever error."""
        # Mock retriever to raise exception
        mock_retriever.side_effect = Exception("Retriever error")

        query_data = {
            "query": "What is Kubernetes?",
            "top_k": 5,
            "generate_answer": True,
        }

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    @patch("src.api.create_rag_generator")
    def test_query_endpoint_generator_error(self, mock_generator):
        """Test query endpoint with generator error."""
        # Mock generator to raise exception
        mock_generator.side_effect = Exception("Generator error")

        query_data = {
            "query": "What is Kubernetes?",
            "top_k": 5,
            "generate_answer": True,
        }

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    @patch("src.api.create_retriever")
    def test_search_endpoint_retriever_error(self, mock_retriever):
        """Test search endpoint with retriever error."""
        # Mock retriever to raise exception
        mock_retriever.side_effect = Exception("Retriever error")

        search_data = {"query": "Kubernetes deployment", "top_k": 5}

        response = self.client.post("/search", json=search_data)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    @patch("src.api.create_ingestion_pipeline")
    def test_ingest_endpoint_pipeline_error(self, mock_pipeline):
        """Test ingest endpoint with pipeline error."""
        # Mock pipeline to raise exception
        mock_pipeline.side_effect = Exception("Pipeline error")

        ingest_data = {
            "text": "Test content",
            "metadata": {"source": "test"},
            "source_name": "test_document",
        }

        response = self.client.post("/ingest", json=ingest_data)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data


class TestAPIValidation:
    """Test API request validation."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_query_validation_top_k_range(self):
        """Test query validation for top_k range."""
        query_data = {
            "query": "What is Kubernetes?",
            "top_k": -1,  # Invalid negative value
            "generate_answer": True,
        }

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 422  # Validation error

    def test_query_validation_top_k_type(self):
        """Test query validation for top_k type."""
        query_data = {
            "query": "What is Kubernetes?",
            "top_k": "invalid",  # Invalid type
            "generate_answer": True,
        }

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 422  # Validation error

    def test_search_validation_score_threshold_range(self):
        """Test search validation for score_threshold range."""
        search_data = {
            "query": "Kubernetes deployment",
            "top_k": 5,
            "score_threshold": 1.5,  # Invalid range (> 1.0)
        }

        response = self.client.post("/search", json=search_data)

        assert response.status_code == 422  # Validation error

    def test_search_validation_score_threshold_type(self):
        """Test search validation for score_threshold type."""
        search_data = {
            "query": "Kubernetes deployment",
            "top_k": 5,
            "score_threshold": "invalid",  # Invalid type
        }

        response = self.client.post("/search", json=search_data)

        assert response.status_code == 422  # Validation error

    def test_ingest_validation_metadata_type(self):
        """Test ingest validation for metadata type."""
        ingest_data = {
            "text": "Test content",
            "metadata": "invalid",  # Should be dict
            "source_name": "test_document",
        }

        response = self.client.post("/ingest", json=ingest_data)

        assert response.status_code == 422  # Validation error


class TestAPIPerformance:
    """Test API performance."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_endpoint_performance(self):
        """Test health endpoint performance."""
        import time

        start_time = time.time()
        response = self.client.get("/health")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 0.1  # Should be very fast

    def test_stats_endpoint_performance(self):
        """Test stats endpoint performance."""
        import time

        start_time = time.time()
        response = self.client.get("/stats")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should be fast

    @patch("src.api.create_retriever")
    def test_query_endpoint_performance(self, mock_retriever):
        """Test query endpoint performance."""
        import time

        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = []
        mock_retriever.return_value = mock_retriever_instance

        query_data = {
            "query": "What is Kubernetes?",
            "top_k": 5,
            "generate_answer": False,  # Faster without generation
        }

        start_time = time.time()
        response = self.client.post("/query", json=query_data)
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should be reasonably fast


class TestAPIIntegration:
    """Test API integration scenarios."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @patch("src.api.create_retriever")
    @patch("src.api.create_rag_generator")
    def test_full_query_workflow(self, mock_generator, mock_retriever):
        """Test full query workflow."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "score": 0.9,
                "metadata": {},
            }
        ]
        mock_retriever.return_value = mock_retriever_instance

        # Mock generator
        mock_generator_instance = Mock()
        mock_generator_instance.generate_answer.return_value = {
            "answer": "Kubernetes is a container orchestration platform that automates deployment, scaling, and management of containerized applications.",
            "sources": ["source1"],
            "metadata": {"model": "gpt-3.5-turbo"},
        }
        mock_generator.return_value = mock_generator_instance

        # Test query
        query_data = {
            "query": "What is Kubernetes?",
            "top_k": 5,
            "generate_answer": True,
            "temperature": 0.3,
        }

        response = self.client.post("/query", json=query_data)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "metadata" in data
        assert len(data["answer"]) > 0

    @patch("src.api.create_ingestion_pipeline")
    def test_full_ingest_workflow(self, mock_pipeline):
        """Test full ingest workflow."""
        # Mock pipeline
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.ingest_from_text.return_value = {
            "chunks_created": 3,
            "source_name": "test_document",
            "metadata": {"source": "api_test"},
        }
        mock_pipeline.return_value = mock_pipeline_instance

        # Test ingest
        ingest_data = {
            "text": "Kubernetes is a container orchestration platform. It helps manage containerized applications.",
            "metadata": {"source": "api_test", "category": "introduction"},
            "source_name": "kubernetes_intro",
        }

        response = self.client.post("/ingest", json=ingest_data)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "chunks_created" in data
        assert data["chunks_created"] == 3


class TestAPIConfiguration:
    """Test API configuration."""

    def test_api_configuration(self):
        """Test API configuration."""
        config, settings = get_config()

        assert config is not None
        assert settings is not None

        # Test that config has required sections
        assert hasattr(config, "llm")
        assert hasattr(config, "retrieval")
        assert hasattr(config, "vector_db")

    def test_api_cors_configuration(self):
        """Test API CORS configuration."""
        # Test that CORS is properly configured
        client = TestClient(app)

        # Test OPTIONS request (CORS preflight)
        response = client.options("/query")

        # Should handle CORS properly
        assert response.status_code in [
            200,
            405,
        ]  # Either success or method not allowed


# Test markers for pytest
@pytest.mark.unit
class TestUnitAPI(TestAPICreation, TestAPIValidation):
    """Unit tests for API module."""

    pass


@pytest.mark.integration
class TestIntegrationAPI(TestAPIEndpoints, TestAPIIntegration):
    """Integration tests for API module."""

    pass


@pytest.mark.api
class TestAPISpecific(TestAPIErrorHandling, TestAPIPerformance):
    """API-specific tests."""

    pass


@pytest.mark.slow
class TestSlowAPI(TestAPIPerformance):
    """Slow tests for API module."""

    pass
