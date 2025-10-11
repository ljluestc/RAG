"""FastAPI REST API for Kubernetes RAG system."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .generation.llm import create_rag_generator
from .ingestion.pipeline import create_ingestion_pipeline
from .retrieval.retriever import create_retriever
from .utils.config_loader import get_config
from .utils.logger import get_logger, setup_logger

# Initialize
config, settings = get_config()
setup_logger(log_level=config.logging.level)
logger = get_logger()

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

# Initialize components
retriever = create_retriever(config)
generator = create_rag_generator(config)
pipeline = create_ingestion_pipeline(config)


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


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results")
    category: Optional[str] = Field(None, description="Filter by category")
    score_threshold: float = Field(default=0.0, description="Minimum similarity score")


class IngestRequest(BaseModel):
    text: str = Field(..., description="Text to ingest")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata"
    )
    source_name: str = Field(default="api_upload", description="Source identifier")


class DocumentResponse(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float


class QueryResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    documents: List[DocumentResponse]
    num_sources: int


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


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check."""
    return {"status": "healthy", "version": "0.1.0"}


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Query the RAG system.

    This endpoint retrieves relevant documents and optionally generates an answer.
    """
    try:
        logger.info(f"Received query: {request.query}")

        # Retrieve documents
        results = retriever.retrieve(request.query, top_k=request.top_k)

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
        }

        # Generate answer if requested
        if request.generate_answer:
            answer_data = generator.generate_answer(
                request.query, results, temperature=request.temperature
            )
            response["answer"] = answer_data["answer"]

        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}")
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
    Ingest text directly into the RAG system.
    """
    try:
        logger.info(f"Ingesting text from: {request.source_name}")

        num_chunks = pipeline.ingest_from_text(
            request.text, metadata=request.metadata, source_name=request.source_name
        )

        return {
            "status": "success",
            "chunks_created": num_chunks,
            "source_name": request.source_name,
        }

    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
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

        return {
            "collection_name": stats["name"],
            "document_count": stats["count"],
            "persist_directory": stats["persist_directory"],
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
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


# Run server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app", host=config.api.host, port=config.api.port, reload=config.api.reload
    )
