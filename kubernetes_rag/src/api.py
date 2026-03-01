"""FastAPI REST API for Kubernetes RAG system."""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .generation.llm import RAGGenerator, create_llm, create_rag_generator
from .ingestion.pipeline import create_ingestion_pipeline
from .metrics import (
    RAG_ACTIVE_MODEL,
    RAG_BENCHMARK_RUNS,
    RAG_CITATIONS_PER_QUERY,
    RAG_COLLECTION_DOCS,
    RAG_DOCUMENTS_RETRIEVED,
    RAG_ERRORS,
    RAG_GENERATION_LATENCY,
    RAG_QUERY_LATENCY,
    RAG_QUERY_TOTAL,
    RAG_RETRIEVAL_LATENCY,
    RAG_TOKENS_USED,
    setup_instrumentator,
)
from .retrieval.retriever import create_retriever
from .utils.config_loader import get_config
from .utils.logger import get_logger, setup_logger


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title="Kubernetes RAG API",
        description="RAG system for Kubernetes learning and testing",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Initialize
config, settings = get_config()
setup_logger(log_level=config.logging.level)
logger = get_logger()

# Create app instance
app = create_app()

# Initialize components
retriever = create_retriever(config)
generator = create_rag_generator(config)
pipeline = create_ingestion_pipeline(config)

# Prometheus metrics
setup_instrumentator(app)
RAG_ACTIVE_MODEL.info({"model": config.llm.model_name, "provider": config.llm.provider})

# Model cache for switching
_llm_cache: Dict[str, Any] = {}

AVAILABLE_MODELS = [
    {"id": "claude-sonnet-4-20250514", "provider": "anthropic", "name": "Claude Sonnet 4"},
    {"id": "claude-haiku-4-5-20251015", "provider": "anthropic", "name": "Claude Haiku 4.5"},
    {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini"},
    {"id": "gpt-3.5-turbo", "provider": "openai", "name": "GPT-3.5 Turbo"},
]


def get_generator_for_model(model_id: str) -> RAGGenerator:
    """Get or create a RAG generator for the given model."""
    if model_id in _llm_cache:
        return _llm_cache[model_id]

    model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
    if not model_info:
        raise ValueError(f"Unknown model: {model_id}")

    llm = create_llm(provider=model_info["provider"], model=model_id)
    gen = RAGGenerator(llm=llm)
    _llm_cache[model_id] = gen
    return gen


# Serve chat UI
@app.get("/chat")
async def chat_ui():
    """Serve the ChatGPT-style chat interface."""
    static_dir = Path(__file__).parent / "static" / "index.html"
    return FileResponse(static_dir, media_type="text/html")


# Request/Response Models
class QueryRequest(BaseModel):
    query: str = Field(..., description="The question or query")
    top_k: int = Field(default=5, description="Number of documents to retrieve")
    generate_answer: bool = Field(
        default=True, description="Whether to generate an answer"
    )
    temperature: float = Field(
        default=0.3, ge=0.0, le=2.0, description="LLM temperature"
    )
    model: Optional[str] = Field(default=None, description="LLM model to use")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results")
    category: Optional[str] = Field(None, description="Filter by category")
    score_threshold: float = Field(default=0.0, description="Minimum similarity score")


class IngestRequest(BaseModel):
    text: Optional[str] = Field(None, description="Text to ingest")
    file_path: Optional[str] = Field(None, description="Path to file to ingest")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata"
    )
    source_name: str = Field(default="api_upload", description="Source identifier")


class CitationResponse(BaseModel):
    citation_id: int
    source: str
    filename: str
    doc_type: str
    chunk_index: int
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    relevance_score: float
    passage: str
    url: Optional[str] = None


class DocumentResponse(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0
    total: int = 0


class QualityMetrics(BaseModel):
    citation_refs: int = 0
    expected_citations: int = 0
    citation_coverage_score: float = 0.0
    groundedness_score: float = 0.0


class SecurityMetrics(BaseModel):
    query_flagged_for_injection: bool = False
    guardrails_enabled: bool = True


class QueryResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    documents: List[DocumentResponse]
    citations: List[CitationResponse] = []
    num_sources: int
    model_used: Optional[str] = None
    tokens_used: Optional[TokenUsage] = None
    quality: Optional[QualityMetrics] = None
    security: Optional[SecurityMetrics] = None
    latency_ms: Optional[float] = None
    retrieval_ms: Optional[float] = None
    generation_ms: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    results: List[DocumentResponse]
    total_results: int


class StatsResponse(BaseModel):
    collection_name: str
    document_count: int
    persist_directory: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health", response_model=HealthResponse)
@app.post("/health", response_model=HealthResponse)
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Query the RAG system.

    This endpoint retrieves relevant documents and optionally generates an answer.
    """
    try:
        t0 = time.perf_counter()
        logger.info(f"Received query: {request.query}")

        # Basic prompt-injection safeguard at API boundary.
        query_lower = request.query.lower()
        suspect_patterns = [
            "ignore previous instructions",
            "reveal system prompt",
            "show developer message",
            "jailbreak",
        ]
        if any(pat in query_lower for pat in suspect_patterns):
            raise HTTPException(
                status_code=400,
                detail="Query rejected by prompt-injection guardrail. Rephrase as a direct technical question.",
            )

        # Retrieve documents
        t_ret = time.perf_counter()
        results = retriever.retrieve(request.query, top_k=request.top_k)
        retrieval_ms = round((time.perf_counter() - t_ret) * 1000, 1)
        RAG_RETRIEVAL_LATENCY.observe(retrieval_ms / 1000)
        RAG_DOCUMENTS_RETRIEVED.observe(len(results) if results else 0)

        if not results:
            raise HTTPException(status_code=404, detail="No relevant documents found")

        # Prepare response
        documents = [
            DocumentResponse(
                content=doc["content"],
                metadata=doc["metadata"],
                score=doc.get("score", 0.0),
            )
            for doc in results
        ]

        response = {
            "query": request.query,
            "documents": documents,
            "num_sources": len(results),
            "retrieval_ms": retrieval_ms,
        }

        # Generate answer if requested
        if request.generate_answer:
            gen = generator
            if request.model:
                try:
                    gen = get_generator_for_model(request.model)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")

            t_gen = time.perf_counter()
            answer_data = gen.generate_answer(
                request.query, results, temperature=request.temperature
            )
            generation_ms = round((time.perf_counter() - t_gen) * 1000, 1)
            response["generation_ms"] = generation_ms
            response["answer"] = answer_data["answer"]
            response["citations"] = [
                CitationResponse(**c) for c in answer_data.get("citations", [])
            ]
            response["model_used"] = answer_data.get("model_used", "")
            response["tokens_used"] = answer_data.get("tokens_used", {})
            response["quality"] = answer_data.get("quality", {})
            response["security"] = answer_data.get("security", {})

        total_ms = round((time.perf_counter() - t0) * 1000, 1)
        response["latency_ms"] = total_ms

        # Record Prometheus metrics
        model_name = response.get("model_used", "unknown")
        RAG_QUERY_TOTAL.labels(model=model_name, status="ok").inc()
        RAG_QUERY_LATENCY.labels(model=model_name).observe(total_ms / 1000)
        if response.get("generation_ms"):
            RAG_GENERATION_LATENCY.labels(model=model_name).observe(response["generation_ms"] / 1000)
        tokens = response.get("tokens_used")
        if tokens:
            RAG_TOKENS_USED.labels(model=model_name, direction="prompt").inc(tokens.get("prompt", 0))
            RAG_TOKENS_USED.labels(model=model_name, direction="completion").inc(tokens.get("completion", 0))
        RAG_CITATIONS_PER_QUERY.observe(len(response.get("citations", [])))

        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        RAG_QUERY_TOTAL.labels(model="unknown", status="error").inc()
        RAG_ERRORS.labels(endpoint="/query", error_type=type(e).__name__).inc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    """
    Search for documents without generating an answer.
    """
    try:
        logger.info(f"Received search: {request.query}")

        # Search
        if request.category:
            results = retriever.retrieve_by_category(
                request.query, request.category, top_k=request.top_k
            )
        else:
            results = retriever.retrieve(
                request.query,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
            )

        # Prepare response
        documents = [
            DocumentResponse(
                content=doc["content"],
                metadata=doc["metadata"],
                score=doc.get("score", 0.0),
            )
            for doc in results
        ]

        return {
            "query": request.query,
            "results": documents,
            "total_results": len(results),
        }

    except Exception as e:
        logger.error(f"Error processing search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_endpoint(request: IngestRequest):
    """
    Ingest text or file into the RAG system.
    """
    try:
        # Validate that either text or file_path is provided
        if not request.text and not request.file_path:
            raise HTTPException(
                status_code=422, detail="Either 'text' or 'file_path' must be provided"
            )

        # Handle file ingestion
        if request.file_path:
            file_path = Path(request.file_path)

            # Check if file exists
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")

            # Validate file format
            supported_formats = {
                ".md",
                ".markdown",
                ".txt",
                ".pdf",
                ".html",
                ".yaml",
                ".yml",
                ".json",
                ".ini",
                ".conf",
            }
            if file_path.suffix.lower() not in supported_formats:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format. Supported: {', '.join(supported_formats)}",
                )

            logger.info(f"Ingesting file: {request.file_path}")
            num_chunks = pipeline.ingest_file(file_path)

            return {
                "status": "success",
                "chunks_ingested": num_chunks,
                "file_path": request.file_path,
            }

        # Handle text ingestion
        else:
            logger.info(f"Ingesting text from: {request.source_name}")
            num_chunks = pipeline.ingest_from_text(
                request.text, metadata=request.metadata, source_name=request.source_name
            )

            return {
                "status": "success",
                "chunks_created": num_chunks,
                "source_name": request.source_name,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse)
async def stats_endpoint():
    """
    Get RAG system statistics.
    """
    try:
        from .retrieval.vector_store import VectorStore

        vector_store = VectorStore(
            collection_name=config.vector_db.collection_name,
            persist_directory=config.vector_db.persist_directory,
        )

        stats = vector_store.get_collection_stats()
        RAG_COLLECTION_DOCS.set(stats["count"])

        return {
            "collection_name": stats["name"],
            "document_count": stats["count"],
            "persist_directory": stats["persist_directory"],
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models")
async def models_endpoint():
    """List available LLM models and current active model."""
    return {
        "models": AVAILABLE_MODELS,
        "default": config.llm.model_name,
        "current": generator.llm.get_model_name(),
    }


class ModelSwitchRequest(BaseModel):
    provider: str = Field(..., description="Provider: openai, anthropic, local")
    model: str = Field(..., description="Model identifier")


@app.post("/models/switch")
async def switch_model(request: ModelSwitchRequest):
    """Switch the active LLM model."""
    global generator
    try:
        llm = create_llm(provider=request.provider, model=request.model)
        gen = RAGGenerator(llm=llm)
        generator = gen
        # Also cache it
        _llm_cache[request.model] = gen
        logger.info(f"Switched default model to {request.provider}/{request.model}")
        RAG_ACTIVE_MODEL.info({"model": request.model, "provider": request.provider})
        return {"status": "ok", "provider": request.provider, "model": request.model}
    except Exception as e:
        logger.error(f"Failed to switch model: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# --------------- Benchmark endpoint ---------------

class BenchmarkRequest(BaseModel):
    query: str = Field(..., description="Query to benchmark")
    models: Optional[List[str]] = Field(
        default=None, description="Model IDs to benchmark (None = all)"
    )
    top_k: int = Field(default=5)
    temperature: float = Field(default=0.3)


@app.post("/benchmark")
async def benchmark_endpoint(request: BenchmarkRequest):
    """
    Run the same query against multiple models and compare results.
    Returns per-model answer, latency, tokens, and a summary.
    """
    try:
        RAG_BENCHMARK_RUNS.inc()
        # Retrieve docs once (shared across models)
        results = retriever.retrieve(request.query, top_k=request.top_k)
        if not results:
            raise HTTPException(status_code=404, detail="No relevant documents found")

        model_ids = request.models or [m["id"] for m in AVAILABLE_MODELS]

        entries = []
        for mid in model_ids:
            try:
                gen = get_generator_for_model(mid)
            except ValueError:
                entries.append({"model": mid, "error": f"Unknown model: {mid}"})
                continue

            t0 = time.perf_counter()
            answer_data = gen.generate_answer(
                request.query, results, temperature=request.temperature
            )
            latency = round((time.perf_counter() - t0) * 1000, 1)

            tokens = answer_data.get("tokens_used", {})
            entries.append({
                "model": mid,
                "answer": answer_data["answer"],
                "latency_ms": latency,
                "tokens_used": tokens,
                "citations": answer_data.get("citations", []),
                "quality": answer_data.get("quality", {}),
            })

        # Build summary
        valid = [e for e in entries if "error" not in e]
        summary = {}
        if valid:
            fastest = min(valid, key=lambda e: e["latency_ms"])
            cheapest = min(valid, key=lambda e: (e["tokens_used"] or {}).get("total", 0))
            summary = {
                "fastest_model": fastest["model"],
                "fastest_latency_ms": fastest["latency_ms"],
                "cheapest_model": cheapest["model"],
                "cheapest_tokens": (cheapest["tokens_used"] or {}).get("total", 0),
                "models_compared": len(valid),
            }

        return {
            "query": request.query,
            "results": entries,
            "summary": summary,
            "num_sources": len(results),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Benchmark error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/categories")
async def categories_endpoint():
    """
    List available document categories.
    """
    return {
        "categories": [
            {
                "id": "qa_pair",
                "name": "Q&A Pairs",
                "description": "Question and answer pairs from documentation",
            },
            {
                "id": "kubernetes_doc",
                "name": "Kubernetes Documentation",
                "description": "General Kubernetes documentation sections",
            },
        ]
    }


@app.post("/reset")
async def reset_endpoint():
    """
    Reset the vector database by deleting the collection.
    """
    try:
        from .retrieval.vector_store import VectorStore

        logger.info("Resetting vector database")

        vector_store = VectorStore(
            collection_name=config.vector_db.collection_name,
            persist_directory=config.vector_db.persist_directory,
        )

        vector_store.delete_collection()

        return {"message": "Vector database reset successfully", "status": "success"}

    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api:app", host=config.api.host, port=config.api.port, reload=config.api.reload
    )
