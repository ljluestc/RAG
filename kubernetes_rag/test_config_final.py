"""Final comprehensive test configuration for 100% coverage."""

import os
from pathlib import Path
from unittest.mock import Mock

# Set environment variables for testing
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

# Mock configuration for testing
mock_config_data = {
    "embedding": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dim": 384,
        "batch_size": 32,
    },
    "vector_db": {
        "type": "chroma",
        "persist_directory": "/tmp/test_vector_db",
        "collection_name": "test_collection",
        "distance_metric": "cosine",
    },
    "document_processing": {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "separators": ["\n\n", "\n", " ", ""],
    },
    "retrieval": {
        "top_k": 5,
        "score_threshold": 0.7,
        "rerank": False,
        "rerank_top_k": 3,
    },
    "llm": {
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "temperature": 0.3,
        "max_tokens": 1000,
        "local_model_path": None,
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": False
    },
    "logging": {
        "level": "INFO",
        "format": "{time} {level} {message}"
    },
    "paths": {
        "raw_data": "./data/raw",
        "processed_data": "./data/processed",
        "vector_db": "./data/vector_db",
    },
}

# Create a mock config object that behaves like the real Config instance
mock_config = Mock()
for key, value in mock_config_data.items():
    setattr(mock_config, key, Mock(**value))

# Mock settings
mock_settings = Mock(
    openai_api_key="test-key-12345",
    anthropic_api_key="test-key-12345",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    llm_model="gpt-3.5-turbo",
    vector_db_path="/tmp/test_vector_db",
    collection_name="test_collection",
    debug=True,
    log_level="DEBUG",
)

# Test content
TEST_MARKDOWN_CONTENT = """# Kubernetes Overview

Kubernetes is a container orchestration platform.

## Key Concepts

### Pods
A pod is the smallest deployable unit in Kubernetes.

### Services
A service provides stable network access to pods.

## Best Practices

1. Use resource limits
2. Implement health checks
3. Use namespaces for organization
"""

TEST_TEXT_CONTENT = """This is a plain text document about Kubernetes.

It contains multiple paragraphs with information about container orchestration.

The content should be processed and chunked appropriately for the RAG system.
"""

# Mock documents for testing
def create_mock_documents(count=5):
    """Create mock documents for testing."""
    documents = []
    for i in range(count):
        documents.append({
            "content": f"Test document {i} content about Kubernetes and container orchestration.",
            "metadata": {
                "source": f"test_doc_{i}.md",
                "title": f"Test Document {i}",
                "chunk_id": f"chunk_{i}",
                "file_type": "markdown"
            },
            "chunk_id": f"chunk_{i}"
        })
    return documents

# Mock embeddings for testing
def create_mock_embeddings(count=5, dim=384):
    """Create mock embeddings for testing."""
    import numpy as np
    return np.random.rand(count, dim).astype(np.float32)

# Mock vector store results
def create_mock_vector_results(count=5):
    """Create mock vector store search results."""
    results = []
    for i in range(count):
        results.append({
            "content": f"Mock document {i} content",
            "metadata": {"source": f"mock_doc_{i}.md"},
            "distance": 0.1 + i * 0.1,
            "id": f"doc_{i}"
        })
    return results
