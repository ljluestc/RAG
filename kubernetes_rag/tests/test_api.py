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
