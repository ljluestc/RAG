"""
Test configuration for comprehensive testing.
This module provides mock configurations and test utilities.
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

# Set test environment variables
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

def create_test_config() -> Dict[str, Any]:
    """Create a test configuration dictionary."""
    return {
        "llm": {
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "embeddings": {
            "provider": "openai",
            "model_name": "text-embedding-ada-002"
        },
        "vector_store": {
            "type": "chroma",
            "persist_directory": str(Path(tempfile.gettempdir()) / "test_chroma_db")
        },
        "retrieval": {
            "top_k": 5,
            "similarity_threshold": 0.7
        },
        "data": {
            "input_directory": str(Path(tempfile.gettempdir()) / "test_data"),
            "processed_directory": str(Path(tempfile.gettempdir()) / "test_processed")
        }
    }

def create_mock_llm():
    """Create a mock LLM for testing."""
    mock_llm = Mock()
    mock_llm.generate.return_value = "Test response"
    mock_llm.agenerate.return_value = "Test async response"
    return mock_llm

def create_mock_embeddings():
    """Create mock embeddings for testing."""
    mock_embeddings = Mock()
    mock_embeddings.embed_documents.return_value = [[0.1, 0.2, 0.3] for _ in range(5)]
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
    return mock_embeddings

def create_mock_vector_store():
    """Create a mock vector store for testing."""
    mock_vs = Mock()
    mock_vs.add_documents.return_value = ["doc1", "doc2", "doc3"]
    mock_vs.similarity_search.return_value = [
        Mock(page_content="Test document 1", metadata={"source": "test1.md"}),
        Mock(page_content="Test document 2", metadata={"source": "test2.md"})
    ]
    mock_vs.similarity_search_with_score.return_value = [
        (Mock(page_content="Test document 1", metadata={"source": "test1.md"}), 0.9),
        (Mock(page_content="Test document 2", metadata={"source": "test2.md"}), 0.8)
    ]
    return mock_vs

def create_mock_retriever():
    """Create a mock retriever for testing."""
    mock_retriever = Mock()
    mock_retriever.retrieve.return_value = [
        Mock(page_content="Test document 1", metadata={"source": "test1.md"}),
        Mock(page_content="Test document 2", metadata={"source": "test2.md"})
    ]
    return mock_retriever

def create_test_documents():
    """Create test documents for testing."""
    return [
        {
            "page_content": "This is a test document about Kubernetes.",
            "metadata": {"source": "test1.md", "title": "Kubernetes Basics"}
        },
        {
            "page_content": "This is another test document about Docker.",
            "metadata": {"source": "test2.md", "title": "Docker Basics"}
        },
        {
            "page_content": "This is a third test document about microservices.",
            "metadata": {"source": "test3.md", "title": "Microservices Architecture"}
        }
    ]

def setup_test_environment():
    """Set up the test environment with necessary patches."""
    patches = []
    
    # Patch the config loader
    config_patch = patch('src.utils.config_loader.load_config', return_value=create_test_config())
    patches.append(config_patch)
    
    # Patch the LLM creation
    llm_patch = patch('src.generation.llm.create_llm', return_value=create_mock_llm())
    patches.append(llm_patch)
    
    # Patch the embeddings creation
    embeddings_patch = patch('src.ingestion.embeddings.create_embeddings', return_value=create_mock_embeddings())
    patches.append(embeddings_patch)
    
    # Patch the vector store creation
    vs_patch = patch('src.retrieval.vector_store.create_vector_store', return_value=create_mock_vector_store())
    patches.append(vs_patch)
    
    # Patch the retriever creation
    retriever_patch = patch('src.retrieval.retriever.Retriever', return_value=create_mock_retriever())
    patches.append(retriever_patch)
    
    return patches


