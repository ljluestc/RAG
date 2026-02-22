"""Prometheus metrics for the RAG API.

Exposes:
  - Default FastAPI request metrics (latency histogram, request count, in-progress)
  - Custom RAG metrics: query latency breakdown, token usage, citation counts, errors
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# --------------- RAG-specific metrics ---------------

RAG_QUERY_TOTAL = Counter(
    "rag_query_total",
    "Total RAG queries processed",
    ["model", "status"],
)

RAG_QUERY_LATENCY = Histogram(
    "rag_query_latency_seconds",
    "End-to-end query latency",
    ["model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

RAG_RETRIEVAL_LATENCY = Histogram(
    "rag_retrieval_latency_seconds",
    "Vector retrieval + reranking latency",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

RAG_GENERATION_LATENCY = Histogram(
    "rag_generation_latency_seconds",
    "LLM generation latency",
    ["model"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

RAG_TOKENS_USED = Counter(
    "rag_tokens_total",
    "Total tokens consumed",
    ["model", "direction"],  # direction: prompt | completion
)

RAG_CITATIONS_PER_QUERY = Histogram(
    "rag_citations_per_query",
    "Number of deduplicated citations per query",
    buckets=(0, 1, 2, 3, 5, 8, 10),
)

RAG_DOCUMENTS_RETRIEVED = Histogram(
    "rag_documents_retrieved",
    "Number of documents retrieved per query",
    buckets=(0, 1, 2, 3, 5, 8, 10, 20),
)

RAG_ERRORS = Counter(
    "rag_errors_total",
    "Total errors by type",
    ["endpoint", "error_type"],
)

RAG_BENCHMARK_RUNS = Counter(
    "rag_benchmark_total",
    "Total benchmark comparison runs",
)

RAG_ACTIVE_MODEL = Info(
    "rag_active_model",
    "Currently active default LLM model",
)

RAG_COLLECTION_DOCS = Gauge(
    "rag_collection_document_count",
    "Number of documents in the vector store",
)


def setup_instrumentator(app):
    """Attach Prometheus FastAPI instrumentator + custom metrics to the app."""
    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/metrics", "/health"],
        inprogress_name="rag_http_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(app, include_in_schema=False)
    return instrumentator
