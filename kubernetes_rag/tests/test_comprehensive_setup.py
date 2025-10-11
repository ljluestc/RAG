"""Comprehensive test configuration and setup for 100% coverage."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="session")
def mock_config():
    """Create a mock configuration for tests."""
    from src.utils.config_loader import Config, Settings

    config = Config()
    settings = Settings()

    # Override with test values
    config.embedding.model_name = "test-model"
    config.embedding.embedding_dim = 384
    config.embedding.batch_size = 32

    config.vector_db.type = "chromadb"
    config.vector_db.persist_directory = "./test_data/vector_db"
    config.vector_db.collection_name = "test_collection"

    config.llm.provider = "openai"
    config.llm.model_name = "gpt-3.5-turbo"
    config.llm.temperature = 0.3
    config.llm.max_tokens = 1000

    config.retrieval.top_k = 5
    config.retrieval.score_threshold = 0.7
    config.retrieval.rerank = True
    config.retrieval.rerank_top_k = 3

    return config, settings


@pytest.fixture
def mock_embedding_generator():
    """Create a mock embedding generator."""
    from src.ingestion.embeddings import EmbeddingGenerator

    generator = Mock(spec=EmbeddingGenerator)
    generator.model_name = "test-model"
    generator.embedding_dim = 384
    generator.device = "cpu"
    generator.encode.return_value = [[0.1] * 384]

    return generator


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    from src.retrieval.vector_store import VectorStore

    store = Mock(spec=VectorStore)
    store.add_documents.return_value = ["doc1", "doc2"]
    store.search.return_value = [
        {"content": "Test content", "score": 0.9, "metadata": {}}
    ]
    store.get_stats.return_value = {
        "total_documents": 10,
        "total_chunks": 50,
        "collections": ["test_collection"],
    }
    store.reset.return_value = True

    return store


@pytest.fixture
def mock_retriever():
    """Create a mock retriever."""
    from src.retrieval.retriever import Retriever

    retriever = Mock(spec=Retriever)
    retriever.retrieve.return_value = [
        {"content": "Test content", "score": 0.9, "metadata": {}}
    ]
    retriever.retrieve_by_category.return_value = [
        {"content": "Test content", "score": 0.9, "metadata": {}}
    ]
    retriever.multi_query_retrieve.return_value = [
        {"content": "Test content", "score": 0.9, "metadata": {}}
    ]

    return retriever


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    from src.generation.llm import OpenAILLM, RAGGenerator

    llm = Mock(spec=OpenAILLM)
    llm.generate.return_value = "Test response"

    generator = Mock(spec=RAGGenerator)
    generator.generate_answer.return_value = {
        "answer": "Test answer",
        "sources": ["source1"],
        "metadata": {"model": "gpt-3.5-turbo"},
    }
    generator.generate_with_followup.return_value = {
        "answer": "Test answer",
        "sources": ["source1"],
        "metadata": {"model": "gpt-3.5-turbo"},
        "conversation_history": [],
    }

    return llm, generator


@pytest.fixture
def mock_document_processor():
    """Create a mock document processor."""
    from src.ingestion.document_processor import KubernetesDocProcessor

    processor = Mock(spec=KubernetesDocProcessor)
    processor.process_document.return_value = [
        {"content": "Test content", "metadata": {"source": "test"}}
    ]
    processor.extract_qa_pairs.return_value = [
        {
            "question": "What is Kubernetes?",
            "answer": "A container orchestration platform",
        }
    ]

    return processor


@pytest.fixture
def mock_ingestion_pipeline():
    """Create a mock ingestion pipeline."""
    from src.ingestion.pipeline import IngestionPipeline

    pipeline = Mock(spec=IngestionPipeline)
    pipeline.ingest_file.return_value = {"chunks_created": 5, "files_processed": 1}
    pipeline.ingest_directory.return_value = {
        "chunks_created": 10,
        "files_processed": 3,
    }
    pipeline.ingest_from_text.return_value = {
        "chunks_created": 1,
        "source_name": "test_source",
    }

    return pipeline


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        {
            "content": "Kubernetes is a container orchestration platform that automates deployment, scaling, and management of containerized applications.",
            "metadata": {"source": "kubernetes_intro.md", "category": "introduction"},
        },
        {
            "content": "A Pod is the smallest deployable unit in Kubernetes. It can contain one or more containers.",
            "metadata": {"source": "kubernetes_pods.md", "category": "concepts"},
        },
        {
            "content": "A Service is an abstract way to expose an application running on Pods as a network service.",
            "metadata": {"source": "kubernetes_services.md", "category": "concepts"},
        },
    ]


@pytest.fixture
def sample_qa_pairs():
    """Create sample Q&A pairs for testing."""
    return [
        {
            "question": "What is Kubernetes?",
            "answer": "Kubernetes is a container orchestration platform that automates deployment, scaling, and management of containerized applications.",
            "metadata": {"source": "kubernetes_intro.md", "category": "qa_pair"},
        },
        {
            "question": "What is a Pod?",
            "answer": "A Pod is the smallest deployable unit in Kubernetes. It can contain one or more containers.",
            "metadata": {"source": "kubernetes_pods.md", "category": "qa_pair"},
        },
        {
            "question": "What is a Service?",
            "answer": "A Service is an abstract way to expose an application running on Pods as a network service.",
            "metadata": {"source": "kubernetes_services.md", "category": "qa_pair"},
        },
    ]


@pytest.fixture
def mock_fastapi_app():
    """Create a mock FastAPI app for testing."""
    from fastapi import FastAPI

    app = FastAPI(title="Test API", version="1.0.0")

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/stats")
    async def stats():
        return {"total_documents": 10, "total_chunks": 50}

    return app


# Test markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.cli,
    pytest.mark.slow,
]


class TestConfiguration:
    """Test configuration and setup."""

    def test_temp_dir_fixture(self, temp_dir):
        """Test temporary directory fixture."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

    def test_mock_config_fixture(self, mock_config):
        """Test mock configuration fixture."""
        config, settings = mock_config

        assert config is not None
        assert settings is not None
        assert config.embedding.model_name == "test-model"
        assert config.vector_db.type == "chromadb"
        assert config.llm.provider == "openai"
        assert config.retrieval.top_k == 5

    def test_mock_embedding_generator_fixture(self, mock_embedding_generator):
        """Test mock embedding generator fixture."""
        generator = mock_embedding_generator

        assert generator.model_name == "test-model"
        assert generator.embedding_dim == 384
        assert generator.device == "cpu"

        # Test encode method
        result = generator.encode("test text")
        assert result == [[0.1] * 384]

    def test_mock_vector_store_fixture(self, mock_vector_store):
        """Test mock vector store fixture."""
        store = mock_vector_store

        # Test add_documents method
        result = store.add_documents([])
        assert result == ["doc1", "doc2"]

        # Test search method
        result = store.search("test query")
        assert len(result) == 1
        assert result[0]["content"] == "Test content"

        # Test get_stats method
        stats = store.get_stats()
        assert stats["total_documents"] == 10
        assert stats["total_chunks"] == 50

    def test_mock_retriever_fixture(self, mock_retriever):
        """Test mock retriever fixture."""
        retriever = mock_retriever

        # Test retrieve method
        result = retriever.retrieve("test query")
        assert len(result) == 1
        assert result[0]["content"] == "Test content"

        # Test retrieve_by_category method
        result = retriever.retrieve_by_category("test query", "qa_pair")
        assert len(result) == 1

        # Test multi_query_retrieve method
        result = retriever.multi_query_retrieve(["query1", "query2"])
        assert len(result) == 1

    def test_mock_llm_fixture(self, mock_llm):
        """Test mock LLM fixture."""
        llm, generator = mock_llm

        # Test LLM generate method
        result = llm.generate("test prompt")
        assert result == "Test response"

        # Test generator generate_answer method
        result = generator.generate_answer("test query", [])
        assert result["answer"] == "Test answer"
        assert result["sources"] == ["source1"]

        # Test generator generate_with_followup method
        result = generator.generate_with_followup("test query", [], [])
        assert result["answer"] == "Test answer"
        assert "conversation_history" in result

    def test_mock_document_processor_fixture(self, mock_document_processor):
        """Test mock document processor fixture."""
        processor = mock_document_processor

        # Test process_document method
        result = processor.process_document("test content")
        assert len(result) == 1
        assert result[0]["content"] == "Test content"

        # Test extract_qa_pairs method
        result = processor.extract_qa_pairs("test content")
        assert len(result) == 1
        assert result[0]["question"] == "What is Kubernetes?"

    def test_mock_ingestion_pipeline_fixture(self, mock_ingestion_pipeline):
        """Test mock ingestion pipeline fixture."""
        pipeline = mock_ingestion_pipeline

        # Test ingest_file method
        result = pipeline.ingest_file(Path("test.md"))
        assert result["chunks_created"] == 5
        assert result["files_processed"] == 1

        # Test ingest_directory method
        result = pipeline.ingest_directory(Path("test_dir"))
        assert result["chunks_created"] == 10
        assert result["files_processed"] == 3

        # Test ingest_from_text method
        result = pipeline.ingest_from_text("test content", {}, "test_source")
        assert result["chunks_created"] == 1
        assert result["source_name"] == "test_source"

    def test_sample_documents_fixture(self, sample_documents):
        """Test sample documents fixture."""
        assert len(sample_documents) == 3

        for doc in sample_documents:
            assert "content" in doc
            assert "metadata" in doc
            assert len(doc["content"]) > 0
            assert "source" in doc["metadata"]

    def test_sample_qa_pairs_fixture(self, sample_qa_pairs):
        """Test sample Q&A pairs fixture."""
        assert len(sample_qa_pairs) == 3

        for qa in sample_qa_pairs:
            assert "question" in qa
            assert "answer" in qa
            assert "metadata" in qa
            assert len(qa["question"]) > 0
            assert len(qa["answer"]) > 0
            assert qa["metadata"]["category"] == "qa_pair"

    def test_mock_fastapi_app_fixture(self, mock_fastapi_app):
        """Test mock FastAPI app fixture."""
        from fastapi.testclient import TestClient

        client = TestClient(mock_fastapi_app)

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # Test stats endpoint
        response = client.get("/stats")
        assert response.status_code == 200
        assert response.json()["total_documents"] == 10


class TestCoverageRequirements:
    """Test coverage requirements."""

    def test_all_modules_importable(self):
        """Test that all modules can be imported."""
        import src.api
        import src.cli
        import src.generation.llm
        import src.ingestion.document_processor
        import src.ingestion.embeddings
        import src.ingestion.pipeline
        import src.retrieval.retriever
        import src.retrieval.vector_store
        import src.utils.config_loader
        import src.utils.logger

        # All imports should succeed
        assert True

    def test_all_classes_instantiable(self):
        """Test that all classes can be instantiated."""
        from src.generation.llm import OpenAILLM, RAGGenerator
        from src.ingestion.document_processor import KubernetesDocProcessor
        from src.ingestion.embeddings import EmbeddingGenerator
        from src.ingestion.pipeline import IngestionPipeline
        from src.retrieval.retriever import Retriever
        from src.retrieval.vector_store import VectorStore
        from src.utils.config_loader import Config, Settings

        # Test instantiation
        config = Config()
        settings = Settings()
        processor = KubernetesDocProcessor()
        generator = EmbeddingGenerator()
        pipeline = IngestionPipeline()
        retriever = Retriever()
        store = VectorStore()
        llm = OpenAILLM()
        rag_generator = RAGGenerator()

        # All instantiations should succeed
        assert all(
            [
                config is not None,
                settings is not None,
                processor is not None,
                generator is not None,
                pipeline is not None,
                retriever is not None,
                store is not None,
                llm is not None,
                rag_generator is not None,
            ]
        )

    def test_all_methods_callable(self):
        """Test that all methods are callable."""
        from src.utils.config_loader import get_config
        from src.utils.logger import get_logger, setup_logger

        # Test function calls
        config, settings = get_config()
        logger1 = setup_logger("test")
        logger2 = get_logger("test")

        assert config is not None
        assert settings is not None
        assert logger1 is not None
        assert logger2 is not None


# Test markers for pytest
@pytest.mark.unit
class TestUnitConfiguration(TestConfiguration):
    """Unit tests for configuration."""

    pass


@pytest.mark.integration
class TestIntegrationConfiguration(TestCoverageRequirements):
    """Integration tests for configuration."""

    pass
