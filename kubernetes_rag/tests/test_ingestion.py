"""Unit tests for ingestion pipeline behavior and metadata policy."""

from __future__ import annotations

import numpy as np

from src.ingestion.pipeline import IngestionPipeline


class _Doc:
    def __init__(self, content: str, metadata: dict, chunk_id: str):
        self.content = content
        self.metadata = metadata
        self.chunk_id = chunk_id


def test_source_type_inference():
    pipeline = IngestionPipeline(vector_store=None, embedding_generator=None, doc_processor=None)
    assert pipeline._get_source_type("data/runbooks/db_failover.md") == "runbook"
    assert pipeline._get_source_type("data/incidents/2026-02-01-outage.md") == "incident"
    assert pipeline._get_source_type("data/configs/api.yaml") == "config"
    assert pipeline._get_source_type("docs/kubernetes/concepts.md") == "kubernetes_doc"


def test_ingest_from_text_flow():
    vector_store = type("VS", (), {"add_documents": lambda *args, **kwargs: None})()
    embedding_generator = type(
        "EG",
        (),
        {"encode_documents": lambda self, docs, show_progress=True: np.array([[0.1, 0.2, 0.3] for _ in docs])},
    )()
    doc_processor = type(
        "DP",
        (),
        {
            "chunker": type(
                "Chunker",
                (),
                {
                    "chunk_text": lambda self, text, metadata: [
                        _Doc("chunk-1", {"source": metadata["source"], "type": metadata["type"]}, "c1"),
                        _Doc("chunk-2", {"source": metadata["source"], "type": metadata["type"]}, "c2"),
                    ]
                },
            )()
        },
    )()

    pipeline = IngestionPipeline(
        vector_store=vector_store,
        embedding_generator=embedding_generator,
        doc_processor=doc_processor,
    )
    chunks = pipeline.ingest_from_text("hello world", source_name="inline-test")
    assert chunks == 2


def test_ingest_file_overrides_metadata_type(tmp_path):
    file_path = tmp_path / "runbook.md"
    file_path.write_text("# runbook")

    class _VectorStore:
        def __init__(self):
            self.calls = 0

        def add_documents(self, documents, embeddings):
            self.calls += 1
            assert len(documents) == 1
            assert documents[0].metadata["type"] == "incident"

    class _Embeddings:
        def encode_documents(self, documents, show_progress=False):
            return np.array([[0.1, 0.2, 0.3]])

    class _DocProcessor:
        def process_file(self, path):
            return [_Doc("incident timeline chunk", {"type": "kubernetes_doc"}, "doc-1")]

    pipeline = IngestionPipeline(
        vector_store=_VectorStore(),
        embedding_generator=_Embeddings(),
        doc_processor=_DocProcessor(),
    )

    count = pipeline.ingest_file(file_path, source_type="incident")
    assert count == 1
