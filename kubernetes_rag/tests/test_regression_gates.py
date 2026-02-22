"""Relevance and latency regression gates for the RAG system.

These tests verify that:
1. Retrieval relevance scores meet minimum thresholds for known queries
2. Retrieval + generation latency stays within acceptable bounds
3. Citation grounding is present and well-formed in responses

Run with: TESTING=true pytest tests/test_regression_gates.py -v
"""

import os
import time
from pathlib import Path

import pytest

# Ensure testing mode
os.environ["TESTING"] = "true"


@pytest.fixture(scope="module")
def config():
    """Load RAG config."""
    from src.utils.config_loader import load_config

    return load_config()


@pytest.fixture(scope="module")
def embedding_generator(config):
    """Create embedding generator."""
    from src.ingestion.embeddings import EmbeddingGenerator

    return EmbeddingGenerator(model_name=config.embedding.model_name)


@pytest.fixture(scope="module")
def ingested_store(config, embedding_generator):
    """Ingest sample docs and return the vector store + retriever."""
    from src.ingestion.document_processor import KubernetesDocProcessor, PDFProcessor
    from src.ingestion.embeddings import EmbeddingGenerator
    from src.retrieval.vector_store import VectorStore

    # Use a dedicated test collection
    vector_store = VectorStore(
        collection_name="regression_test_collection",
        persist_directory="./data/test_vector_db",
        distance_metric=config.vector_db.distance_metric,
    )

    # Ingest sample markdown
    md_path = Path("data/sample_docs/kubernetes_basics.md")
    if md_path.exists():
        md_proc = KubernetesDocProcessor(
            chunk_size=config.document_processing.chunk_size,
            chunk_overlap=config.document_processing.chunk_overlap,
        )
        docs = md_proc.process_file(md_path)
        if docs:
            embeddings = embedding_generator.encode_documents(docs, show_progress=False)
            vector_store.add_documents(docs, embeddings)

    # Ingest sample PDF
    pdf_path = Path("data/sample_docs/docker_guide.pdf")
    if pdf_path.exists():
        pdf_proc = PDFProcessor(
            chunk_size=config.document_processing.chunk_size,
            chunk_overlap=config.document_processing.chunk_overlap,
        )
        docs = pdf_proc.process_file(pdf_path)
        if docs:
            embeddings = embedding_generator.encode_documents(docs, show_progress=False)
            vector_store.add_documents(docs, embeddings)

    yield vector_store

    # Cleanup
    try:
        vector_store.delete_collection()
    except Exception:
        pass


@pytest.fixture(scope="module")
def retriever(config, ingested_store, embedding_generator):
    """Create retriever using the ingested test store."""
    from src.retrieval.retriever import Retriever

    return Retriever(
        vector_store=ingested_store,
        embedding_generator=embedding_generator,
        use_rerank=config.retrieval.rerank,
    )


@pytest.fixture(scope="module")
def generator(config):
    """Create RAG generator in test mode."""
    from src.generation.llm import create_rag_generator

    return create_rag_generator(config)


# ============================================================
# Relevance Regression Gates
# ============================================================

# Known queries with expected minimum relevance scores
RELEVANCE_TEST_CASES = [
    {
        "query": "What is a Pod in Kubernetes?",
        "min_score": 0.20,
        "expected_keywords": ["pod", "container"],
    },
    {
        "query": "What are Kubernetes Services?",
        "min_score": 0.15,
        "expected_keywords": ["service"],
    },
    {
        "query": "Docker container networking",
        "min_score": 0.15,
        "expected_keywords": ["docker", "network"],
    },
    {
        "query": "How to scale a deployment?",
        "min_score": 0.10,
        "expected_keywords": ["deployment", "scale"],
    },
]


class TestRelevanceGates:
    """Test that retrieval relevance meets minimum thresholds."""

    @pytest.mark.parametrize("test_case", RELEVANCE_TEST_CASES, ids=[t["query"][:40] for t in RELEVANCE_TEST_CASES])
    def test_retrieval_relevance_above_threshold(self, retriever, test_case):
        """Verify top-1 retrieval score meets minimum threshold."""
        results = retriever.retrieve(test_case["query"], top_k=5)

        assert len(results) > 0, f"No results returned for: {test_case['query']}"

        top_score = results[0].get("score", 0.0)
        # After reranking, score may be in rerank_score
        if "rerank_score" in results[0]:
            top_score = max(top_score, results[0]["rerank_score"])

        assert top_score >= test_case["min_score"], (
            f"Relevance too low for '{test_case['query']}': "
            f"got {top_score:.4f}, expected >= {test_case['min_score']}"
        )

    @pytest.mark.parametrize("test_case", RELEVANCE_TEST_CASES, ids=[t["query"][:40] for t in RELEVANCE_TEST_CASES])
    def test_retrieved_content_contains_keywords(self, retriever, test_case):
        """Verify retrieved content contains expected keywords."""
        results = retriever.retrieve(test_case["query"], top_k=5)
        assert len(results) > 0

        # Check that at least one result contains expected keywords
        all_content = " ".join(r["content"].lower() for r in results)
        for keyword in test_case["expected_keywords"]:
            assert keyword.lower() in all_content, (
                f"Expected keyword '{keyword}' not found in results for: {test_case['query']}"
            )

    def test_minimum_results_returned(self, retriever):
        """Verify that queries return a minimum number of results."""
        results = retriever.retrieve("Kubernetes basics", top_k=3)
        assert len(results) >= 1, "Expected at least 1 result for a broad query"


# ============================================================
# Latency Regression Gates
# ============================================================

# Maximum allowed latencies in seconds
MAX_RETRIEVAL_LATENCY = 5.0  # seconds
MAX_GENERATION_LATENCY = 10.0  # seconds (includes mock LLM)
MAX_EMBEDDING_LATENCY = 3.0  # seconds per query


class TestLatencyGates:
    """Test that operations complete within latency bounds."""

    def test_retrieval_latency(self, retriever):
        """Verify retrieval completes within latency bound."""
        query = "What is a Kubernetes Pod?"

        start = time.perf_counter()
        results = retriever.retrieve(query, top_k=5)
        elapsed = time.perf_counter() - start

        assert elapsed < MAX_RETRIEVAL_LATENCY, (
            f"Retrieval too slow: {elapsed:.2f}s > {MAX_RETRIEVAL_LATENCY}s"
        )
        assert len(results) > 0

    def test_embedding_latency(self, embedding_generator):
        """Verify embedding generation completes within latency bound."""
        query = "How does Kubernetes schedule pods?"

        start = time.perf_counter()
        embedding = embedding_generator.encode_query(query)
        elapsed = time.perf_counter() - start

        assert elapsed < MAX_EMBEDDING_LATENCY, (
            f"Embedding too slow: {elapsed:.2f}s > {MAX_EMBEDDING_LATENCY}s"
        )
        assert embedding is not None
        assert len(embedding) > 0

    def test_full_rag_latency(self, retriever, generator):
        """Verify full RAG pipeline (retrieve + generate) within latency bound."""
        query = "What is etcd used for?"

        start = time.perf_counter()
        results = retriever.retrieve(query, top_k=3)
        if results:
            answer = generator.generate_answer(query, results)
        elapsed = time.perf_counter() - start

        total_max = MAX_RETRIEVAL_LATENCY + MAX_GENERATION_LATENCY
        assert elapsed < total_max, (
            f"Full RAG pipeline too slow: {elapsed:.2f}s > {total_max}s"
        )


# ============================================================
# Citation Grounding Gates
# ============================================================


class TestCitationGrounding:
    """Test that citation grounding is present and well-formed."""

    def test_citations_present_in_response(self, retriever, generator):
        """Verify citations are included in generated answers."""
        results = retriever.retrieve("What is a Kubernetes Pod?", top_k=3)
        assert len(results) > 0

        answer_data = generator.generate_answer("What is a Kubernetes Pod?", results)

        assert "citations" in answer_data, "Response missing 'citations' field"
        assert len(answer_data["citations"]) > 0, "Citations list is empty"

    def test_citation_structure(self, retriever, generator):
        """Verify each citation has required fields."""
        results = retriever.retrieve("Kubernetes deployment", top_k=3)
        answer_data = generator.generate_answer("Kubernetes deployment", results)

        required_fields = {
            "citation_id", "source", "filename", "doc_type",
            "chunk_index", "relevance_score", "passage",
        }

        for citation in answer_data["citations"]:
            missing = required_fields - set(citation.keys())
            assert not missing, f"Citation missing fields: {missing}"

    def test_citation_relevance_scores_are_valid(self, retriever, generator):
        """Verify citation relevance scores are numeric and reasonable."""
        results = retriever.retrieve("Docker containers", top_k=3)
        answer_data = generator.generate_answer("Docker containers", results)

        for citation in answer_data["citations"]:
            score = citation["relevance_score"]
            assert isinstance(score, (int, float)), f"Score not numeric: {score}"

    def test_citation_passage_not_empty(self, retriever, generator):
        """Verify citation passages contain actual text."""
        results = retriever.retrieve("kubectl commands", top_k=3)
        answer_data = generator.generate_answer("kubectl commands", results)

        for citation in answer_data["citations"]:
            assert citation["passage"].strip(), "Citation passage is empty"
            assert len(citation["passage"]) > 10, "Citation passage too short"

    def test_pdf_citations_include_page_number(self, retriever, generator):
        """Verify PDF-sourced citations include page_number metadata."""
        results = retriever.retrieve("Docker networking bridge", top_k=5)
        answer_data = generator.generate_answer("Docker networking bridge", results)

        pdf_citations = [
            c for c in answer_data["citations"] if c["doc_type"] == "pdf"
        ]

        # If we got PDF results, they should have page numbers
        for citation in pdf_citations:
            assert citation.get("page_number") is not None, (
                "PDF citation missing page_number"
            )
