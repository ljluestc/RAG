"""Comprehensive test configuration for Kubernetes RAG system."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Set up test environment variables
os.environ.update({
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
    "LOG_LEVEL": "DEBUG"
})

# Create a comprehensive test configuration
TEST_CONFIG_DATA = {
    "embedding": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dim": 384,
        "batch_size": 32
    },
    "vector_db": {
        "type": "chroma",
        "persist_directory": "/tmp/test_vector_db",
        "collection_name": "test_collection",
        "distance_metric": "cosine"
    },
    "document_processing": {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "separators": ["\n\n", "\n", " ", ""]
    },
    "retrieval": {
        "top_k": 5,
        "score_threshold": 0.7,
        "rerank": False,
        "rerank_top_k": 10
    },
    "llm": {
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 1000,
        "local_model_path": None
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "paths": {
        "raw_data": "./data/raw",
        "processed_data": "./data/processed",
        "vector_db": "./data/vector_db"
    }
}

# Create test fixtures
def create_mock_config():
    """Create a mock configuration object."""
    from src.utils.config_loader import Config
    return Config(**TEST_CONFIG_DATA)

def create_mock_settings():
    """Create a mock settings object."""
    from src.utils.config_loader import Settings
    return Settings()

def create_mock_document():
    """Create a mock document object."""
    from src.ingestion.document_processor import Document
    return Document(
        content="Test document content",
        metadata={"source": "test.md", "title": "Test Document"},
        chunk_id="test_chunk_1"
    )

def create_mock_documents(count=5):
    """Create multiple mock documents."""
    documents = []
    for i in range(count):
        doc = create_mock_document()
        doc.chunk_id = f"test_chunk_{i}"
        doc.content = f"Test document content {i}"
        documents.append(doc)
    return documents

def create_mock_vector_store():
    """Create a mock vector store."""
    mock_vs = MagicMock()
    mock_vs.add_documents.return_value = None
    mock_vs.similarity_search.return_value = {
        "documents": [["doc1", "doc2", "doc3"]],
        "distances": [[0.1, 0.2, 0.3]],
        "metadatas": [[{"source": "test1.md"}, {"source": "test2.md"}, {"source": "test3.md"}]]
    }
    mock_vs.get_collection_stats.return_value = {
        "name": "test_collection",
        "count": 5,
        "persist_directory": "/tmp/test"
    }
    mock_vs.delete_collection.return_value = None
    return mock_vs

def create_mock_embedding_generator():
    """Create a mock embedding generator."""
    mock_emb = MagicMock()
    mock_emb.encode.return_value = [[0.1, 0.2, 0.3, 0.4]] * 5  # 5 documents with 4-dim embeddings
    mock_emb.embedding_dim = 4
    return mock_emb

def create_mock_document_processor():
    """Create a mock document processor."""
    mock_proc = MagicMock()
    mock_proc.process_file.return_value = create_mock_documents(3)
    mock_proc.process_markdown.return_value = create_mock_documents(2)
    mock_proc.process_text.return_value = create_mock_documents(1)
    mock_proc.process_document.return_value = create_mock_documents(1)
    mock_proc._chunk_text.return_value = ["chunk1", "chunk2", "chunk3"]
    mock_proc._extract_metadata.return_value = {"source": "test.md", "title": "Test"}
    return mock_proc

def create_mock_llm():
    """Create a mock LLM."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "This is a test response"
    return mock_llm

def create_mock_retriever():
    """Create a mock retriever."""
    mock_ret = MagicMock()
    mock_ret.retrieve.return_value = [
        {
            "content": "Test document content",
            "metadata": {"source": "test.md"},
            "score": 0.9
        }
    ]
    return mock_ret

def create_mock_rag_generator():
    """Create a mock RAG generator."""
    mock_rag = MagicMock()
    mock_rag.generate_answer.return_value = {
        "answer": "Test answer",
        "query": "Test query",
        "documents": []
    }
    return mock_rag

# Create temporary directories for testing
def setup_test_directories():
    """Set up temporary directories for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    test_dirs = {
        "raw_data": temp_dir / "raw",
        "processed_data": temp_dir / "processed", 
        "vector_db": temp_dir / "vector_db"
    }
    
    for dir_path in test_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return test_dirs

def cleanup_test_directories(test_dirs):
    """Clean up test directories."""
    import shutil
    for dir_path in test_dirs.values():
        if dir_path.exists():
            shutil.rmtree(dir_path)

# Test data
TEST_MARKDOWN_CONTENT = """# Kubernetes Overview

Kubernetes is an open-source container orchestration platform.

## Features

- Container orchestration
- Service discovery
- Load balancing

## Getting Started

To get started with Kubernetes, you need to:

1. Install kubectl
2. Set up a cluster
3. Deploy your applications
"""

TEST_TEXT_CONTENT = """This is a plain text document about Kubernetes.

It contains information about container orchestration and management.

The document is structured with multiple paragraphs and sections.
"""

TEST_QUERY = "What is Kubernetes?"
TEST_ANSWER = "Kubernetes is an open-source container orchestration platform."
