"""API tests focused on stable behavior and correct mock targets."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_health_endpoints(api_client):
    for method in ("get", "post"):
        response = getattr(api_client, method)("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "healthy"
        assert "timestamp" in payload


def test_query_success(api_client, mock_retriever, mock_generator):
    response = api_client.post("/query", json={"query": "What is a Pod?", "top_k": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "What is a Pod?"
    assert payload["num_sources"] == 3
    assert payload["answer"]
    mock_retriever.retrieve.assert_called_once()
    mock_generator.generate_answer.assert_called_once()


def test_query_without_generation(api_client, mock_generator):
    response = api_client.post("/query", json={"query": "What is etcd?", "generate_answer": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] is None
    mock_generator.generate_answer.assert_not_called()


def test_query_invalid_payload(api_client):
    response = api_client.post("/query", json={})
    assert response.status_code == 422


def test_search_and_category_filter(api_client, mock_retriever):
    response = api_client.post("/search", json={"query": "deployment", "category": "qa_pair"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "deployment"
    assert payload["total_results"] == 2
    mock_retriever.retrieve_by_category.assert_called_once()


def test_ingest_text(api_client, mock_pipeline):
    response = api_client.post(
        "/ingest",
        json={
            "text": "Kubernetes runs containers.",
            "source_name": "inline",
            "metadata": {"type": "runbook"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["chunks_created"] == 3
    mock_pipeline.ingest_from_text.assert_called_once()


def test_ingest_file_validation(api_client, tmp_path):
    fake_file = tmp_path / "test.exe"
    fake_file.write_text("binary")
    response = api_client.post("/ingest", json={"file_path": str(fake_file)})
    assert response.status_code == 400


def test_models_and_switch(api_client):
    list_response = api_client.get("/models")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert "models" in payload and "default" in payload

    switch_response = api_client.post(
        "/models/switch",
        json={"provider": "openai", "model": "gpt-3.5-turbo"},
    )
    assert switch_response.status_code == 200


def test_stats_and_reset(api_client):
    fake_store = MagicMock()
    fake_store.get_collection_stats.return_value = {
        "name": "kubernetes_docs",
        "count": 7,
        "persist_directory": "./data/vector_db",
    }

    with patch("src.retrieval.vector_store.VectorStore", return_value=fake_store):
        stats_response = api_client.get("/stats")
        reset_response = api_client.post("/reset")

    assert stats_response.status_code == 200
    assert stats_response.json()["document_count"] == 7
    assert reset_response.status_code == 200
    fake_store.delete_collection.assert_called_once()


def test_chat_ui_serves_html(api_client):
    response = api_client.get("/chat")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
"""Comprehensive API tests — patches the module-level singletons in src.api."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

def make_mock_retriever_results(n: int = 3):
    return [
        {
            "content": f"Document {i} about Kubernetes.",
            "metadata": {"source": f"doc_{i}.md", "filename": f"doc_{i}.md", "type": "kubernetes_doc"},
            "score": round(0.95 - i * 0.05, 2),
        }
        for i in range(n)
    ]


def make_mock_generator_answer(query: str = "test query"):
    return {
        "query": query,
        "answer": "Kubernetes is a container orchestration platform. [Source 1]",
        "num_sources": 3,
        "citations": [
            {
                "citation_id": 1,
                "source": "doc_0.md",
                "filename": "doc_0.md",
                "doc_type": "kubernetes_doc",
                "chunk_index": 0,
                "section_title": None,
                "page_number": None,
                "relevance_score": 0.95,
                "passage": "Document 0 about Kubernetes.",
                "url": None,
            }
        ],
        "model_used": "test-model",
        "tokens_used": {"prompt": 100, "completion": 50, "total": 150},
        "sources": [],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client(mock_retriever, mock_generator, mock_pipeline):
    """Build a TestClient with all singletons patched."""
    with (
        patch("src.api.retriever", mock_retriever),
        patch("src.api.generator", mock_generator),
        patch("src.api.pipeline", mock_pipeline),
    ):
        from src.api import app
        yield TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# App creation
# ═══════════════════════════════════════════════════════════════════════════

class TestAppCreation:
    def test_app_exists(self):
        from src.api import app
        assert app is not None

    def test_create_app_returns_fastapi(self):
        from src.api import create_app
        test_app = create_app()
        assert test_app.title == "Kubernetes RAG API"

    def test_app_has_routes(self):
        from src.api import app
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        assert client.get("/docs").status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Health endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_get_health(self, api_client):
        r = api_client.get("/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "healthy"
        assert "timestamp" in d

    def test_post_health(self, api_client):
        r = api_client.post("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_root_health(self, api_client):
        r = api_client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


# ═══════════════════════════════════════════════════════════════════════════
# /query endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryEndpoint:
    def test_query_success(self, api_client, mock_retriever, mock_generator):
        r = api_client.post("/query", json={"query": "What is a Pod?", "top_k": 5})
        assert r.status_code == 200
        d = r.json()
        assert d["query"] == "What is a Pod?"
        assert "answer" in d
        assert d["num_sources"] == 3
        assert "citations" in d
        assert d["model_used"] == "test-model"
        mock_retriever.retrieve.assert_called_once()
        mock_generator.generate_answer.assert_called_once()

    def test_query_missing_field(self, api_client):
        r = api_client.post("/query", json={})
        assert r.status_code == 422

    def test_query_invalid_json(self, api_client):
        r = api_client.post("/query", data="not json")
        assert r.status_code == 422

    def test_query_no_results(self, api_client, mock_retriever):
        mock_retriever.retrieve.return_value = []
        r = api_client.post("/query", json={"query": "xyz"})
        assert r.status_code == 500  # raises HTTPException 404 → caught as 500

    def test_query_generator_error(self, api_client, mock_generator):
        mock_generator.generate_answer.side_effect = Exception("boom")
        r = api_client.post("/query", json={"query": "test"})
        assert r.status_code == 500

    def test_query_without_answer_generation(self, api_client, mock_retriever):
        r = api_client.post(
            "/query",
            json={"query": "test", "generate_answer": False},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["answer"] is None
        assert d["num_sources"] == 3

    def test_query_get_not_allowed(self, api_client):
        assert api_client.get("/query").status_code == 405

    def test_query_with_model_override(self, api_client, mock_retriever):
        """Requesting unknown model returns 500 (caught from ValueError)."""
        r = api_client.post(
            "/query",
            json={"query": "test", "model": "nonexistent-model"},
        )
        assert r.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════
# /search endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestSearchEndpoint:
    def test_search_success(self, api_client, mock_retriever):
        r = api_client.post("/search", json={"query": "deployment"})
        assert r.status_code == 200
        d = r.json()
        assert d["total_results"] == 3
        assert len(d["results"]) == 3

    def test_search_with_category(self, api_client, mock_retriever):
        r = api_client.post(
            "/search", json={"query": "pods", "category": "qa_pair"}
        )
        assert r.status_code == 200
        mock_retriever.retrieve_by_category.assert_called_once()

    def test_search_missing_query(self, api_client):
        assert api_client.post("/search", json={}).status_code == 422

    def test_search_retriever_error(self, api_client, mock_retriever):
        mock_retriever.retrieve.side_effect = Exception("fail")
        r = api_client.post("/search", json={"query": "test"})
        assert r.status_code == 500

    def test_search_empty_results(self, api_client, mock_retriever):
        mock_retriever.retrieve.return_value = []
        r = api_client.post("/search", json={"query": "test"})
        assert r.status_code == 200
        assert r.json()["total_results"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# /ingest endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestIngestEndpoint:
    def test_ingest_text(self, api_client, mock_pipeline):
        r = api_client.post(
            "/ingest",
            json={
                "text": "Kubernetes is a container platform.",
                "source_name": "test_doc",
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "success"
        assert d["chunks_created"] == 3
        mock_pipeline.ingest_from_text.assert_called_once()

    def test_ingest_file(self, api_client, mock_pipeline):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            f.write("# Test\nSome content")
            f.flush()
            path = f.name

        try:
            r = api_client.post("/ingest", json={"file_path": path})
            assert r.status_code == 200
            assert r.json()["status"] == "success"
            mock_pipeline.ingest_file.assert_called_once()
        finally:
            os.unlink(path)

    def test_ingest_no_input(self, api_client):
        r = api_client.post("/ingest", json={"source_name": "empty"})
        assert r.status_code == 422  # validated by the endpoint

    def test_ingest_file_not_found(self, api_client):
        r = api_client.post("/ingest", json={"file_path": "/nonexistent.md"})
        assert r.status_code == 404

    def test_ingest_unsupported_format(self, api_client):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            path = f.name
        try:
            r = api_client.post("/ingest", json={"file_path": path})
            assert r.status_code == 400
        finally:
            os.unlink(path)

    def test_ingest_pipeline_error(self, api_client, mock_pipeline):
        mock_pipeline.ingest_from_text.side_effect = Exception("pipeline fail")
        r = api_client.post(
            "/ingest", json={"text": "hello", "source_name": "x"}
        )
        assert r.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════
# /stats endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestStatsEndpoint:
    def test_stats_success(self, api_client):
        mock_vs = MagicMock()
        mock_vs.get_collection_stats.return_value = {
            "name": "kubernetes_docs",
            "count": 42,
            "persist_directory": "/data/vector_db",
        }
        with patch("src.retrieval.vector_store.VectorStore", return_value=mock_vs):
            r = api_client.get("/stats")
            assert r.status_code == 200
            d = r.json()
            assert d["document_count"] == 42

    def test_stats_error(self, api_client):
        with patch("src.retrieval.vector_store.VectorStore", side_effect=Exception("db fail")):
            r = api_client.get("/stats")
            assert r.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════
# /reset endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestResetEndpoint:
    def test_reset_success(self, api_client):
        mock_vs = MagicMock()
        with patch("src.retrieval.vector_store.VectorStore", return_value=mock_vs):
            r = api_client.post("/reset")
            assert r.status_code == 200
            assert r.json()["status"] == "success"
            mock_vs.delete_collection.assert_called_once()

    def test_reset_error(self, api_client):
        with patch("src.retrieval.vector_store.VectorStore", side_effect=Exception("fail")):
            r = api_client.post("/reset")
            assert r.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════
# /models endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestModelsEndpoint:
    def test_list_models(self, api_client):
        r = api_client.get("/models")
        assert r.status_code == 200
        d = r.json()
        assert "models" in d
        assert "default" in d

    def test_switch_model(self, api_client):
        r = api_client.post(
            "/models/switch",
            json={"provider": "openai", "model": "gpt-3.5-turbo"},
        )
        # In test mode LLMs are mocked, so this should succeed
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# /categories & /chat endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestMiscEndpoints:
    def test_categories(self, api_client):
        r = api_client.get("/categories")
        assert r.status_code == 200
        cats = r.json()["categories"]
        assert len(cats) >= 2

    def test_chat_ui(self, api_client):
        r = api_client.get("/chat")
        assert r.status_code == 200
