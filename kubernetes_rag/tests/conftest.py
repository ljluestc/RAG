"""Shared test fixtures and dependency stubs for the RAG project."""

from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


os.environ.update(
    {
        "OPENAI_API_KEY": "test-key-12345",
        "ANTHROPIC_API_KEY": "test-key-12345",
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
    }
)


def _install_dependency_stubs() -> None:
    """Install lightweight stubs for optional heavy dependencies."""
    if "torch" not in sys.modules:
        torch_mod = types.ModuleType("torch")
        torch_mod.cuda = types.SimpleNamespace(is_available=lambda: False)
        sys.modules["torch"] = torch_mod

    if "sentence_transformers" not in sys.modules:
        st_mod = types.ModuleType("sentence_transformers")

        class SentenceTransformer:
            def __init__(self, model_name: str, device: str | None = None):
                self.model_name = model_name
                self.device = device

            def get_sentence_embedding_dimension(self) -> int:
                return 384

            def encode(
                self,
                texts,
                batch_size: int = 32,
                show_progress_bar: bool = False,
                normalize_embeddings: bool = True,
                convert_to_numpy: bool = True,
            ):
                if isinstance(texts, str):
                    texts = [texts]
                arr = np.array([[0.1] * 384 for _ in texts], dtype=float)
                return arr if convert_to_numpy else arr.tolist()

        class CrossEncoder:
            def __init__(self, model_name: str):
                self.model_name = model_name

            def predict(self, pairs):
                return [0.9 for _ in pairs]

        st_mod.SentenceTransformer = SentenceTransformer
        st_mod.CrossEncoder = CrossEncoder
        sys.modules["sentence_transformers"] = st_mod

    if "chromadb" not in sys.modules:
        chroma_mod = types.ModuleType("chromadb")

        class _Collection:
            def __init__(self):
                self._docs = []

            def add(self, ids, embeddings, documents, metadatas):
                for doc_id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
                    self._docs.append(
                        {
                            "id": doc_id,
                            "embedding": emb,
                            "document": doc,
                            "metadata": meta,
                        }
                    )

            def query(self, query_embeddings, n_results=5, where=None):
                docs = [d for d in self._docs if not where or all(d["metadata"].get(k) == v for k, v in where.items())]
                docs = docs[:n_results]
                return {
                    "documents": [[d["document"] for d in docs]],
                    "metadatas": [[d["metadata"] for d in docs]],
                    "distances": [[0.1 for _ in docs]],
                }

            def count(self):
                return len(self._docs)

            def update(self, ids, embeddings, documents, metadatas):
                for doc_id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
                    for stored in self._docs:
                        if stored["id"] == doc_id:
                            stored.update({"embedding": emb, "document": doc, "metadata": meta})

            def delete(self, ids):
                self._docs = [d for d in self._docs if d["id"] not in set(ids)]

            def get(self, ids=None, include=None, limit=None, offset=0):
                records = self._docs
                if ids:
                    records = [d for d in records if d["id"] in set(ids)]
                if limit is not None:
                    records = records[offset : offset + limit]
                return {
                    "ids": [d["id"] for d in records],
                    "documents": [d["document"] for d in records],
                    "metadatas": [d["metadata"] for d in records],
                    "embeddings": [d["embedding"] for d in records],
                }

        class PersistentClient:
            def __init__(self, path, settings=None):
                self.path = path
                self._collections = {}

            def get_or_create_collection(self, name, metadata=None):
                if name not in self._collections:
                    self._collections[name] = _Collection()
                return self._collections[name]

            def delete_collection(self, name):
                self._collections.pop(name, None)

        chroma_mod.PersistentClient = PersistentClient
        sys.modules["chromadb"] = chroma_mod

        chroma_config = types.ModuleType("chromadb.config")

        class Settings:
            def __init__(self, anonymized_telemetry=False, allow_reset=True):
                self.anonymized_telemetry = anonymized_telemetry
                self.allow_reset = allow_reset

        chroma_config.Settings = Settings
        sys.modules["chromadb.config"] = chroma_config

        chroma_utils = types.ModuleType("chromadb.utils")
        chroma_utils.embedding_functions = types.SimpleNamespace()
        sys.modules["chromadb.utils"] = chroma_utils


_install_dependency_stubs()


def make_mock_retriever_results(n: int = 3):
    return [
        {
            "content": f"Document {i} about Kubernetes.",
            "metadata": {
                "source": f"doc_{i}.md",
                "filename": f"doc_{i}.md",
                "type": "kubernetes_doc",
                "chunk_index": i,
            },
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


@pytest.fixture()
def mock_config():
    from src.utils.config_loader import (
        APIConfig,
        Config,
        DocumentProcessingConfig,
        EmbeddingConfig,
        LLMConfig,
        LoggingConfig,
        PathsConfig,
        RetrievalConfig,
        Settings,
        VectorDBConfig,
    )

    cfg = Config(
        embedding=EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dim=384,
            batch_size=8,
        ),
        vector_db=VectorDBConfig(
            type="chroma",
            persist_directory="./data/vector_db",
            collection_name="kubernetes_docs",
            distance_metric="cosine",
        ),
        document_processing=DocumentProcessingConfig(
            chunk_size=400,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""],
        ),
        retrieval=RetrievalConfig(top_k=5, score_threshold=0.0, rerank=False, rerank_top_k=3),
        llm=LLMConfig(provider="openai", model_name="gpt-3.5-turbo", temperature=0.3, max_tokens=500),
        api=APIConfig(host="127.0.0.1", port=8000, reload=False),
        logging=LoggingConfig(level="INFO", format="{message}"),
        paths=PathsConfig(raw_data="./data/raw", processed_data="./data/processed", vector_db="./data/vector_db"),
    )
    return cfg, Settings()


@pytest.fixture()
def mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = make_mock_retriever_results()
    r.retrieve_by_category.return_value = make_mock_retriever_results(2)
    return r


@pytest.fixture()
def mock_generator():
    g = MagicMock()
    g.generate_answer.return_value = make_mock_generator_answer()
    g.generate_with_followup.return_value = {
        "answer": "Follow-up answer",
        "conversation_history": [],
    }
    g.llm.get_model_name.return_value = "test-model"
    return g


@pytest.fixture()
def mock_pipeline():
    p = MagicMock()
    p.ingest_file.return_value = 5
    p.ingest_from_text.return_value = 3
    p.ingest_directory.return_value = {
        "total_files": 2,
        "processed_files": 2,
        "total_chunks": 10,
        "failed_files": [],
    }
    return p


@pytest.fixture()
def api_client(mock_config, mock_retriever, mock_generator, mock_pipeline):
    from fastapi.testclient import TestClient

    with (
        patch("src.utils.config_loader.get_config", return_value=mock_config),
        patch("src.retrieval.retriever.create_retriever", return_value=mock_retriever),
        patch("src.generation.llm.create_rag_generator", return_value=mock_generator),
        patch("src.ingestion.pipeline.create_ingestion_pipeline", return_value=mock_pipeline),
    ):
        import src.api as api_module

        importlib.reload(api_module)
        yield TestClient(api_module.app)
