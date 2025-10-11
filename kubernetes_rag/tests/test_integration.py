"""Integration tests for the Kubernetes RAG system."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from src.generation.llm import OpenAILLM, RAGGenerator
from src.ingestion.document_processor import Document, KubernetesDocProcessor
from src.ingestion.embeddings import EmbeddingGenerator
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore
from src.utils.config_loader import Config, Settings, get_config


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator integration."""

    def test_embedding_generator_initialization(self):
        """Test embedding generator initialization."""
        generator = EmbeddingGenerator()

        assert generator.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert generator.embedding_dim > 0
        assert generator.device in ["cpu", "cuda"]

    def test_encode_single_text(self):
        """Test encoding a single text."""
        generator = EmbeddingGenerator()

        text = "Kubernetes is a container orchestration platform"
        embedding = generator.encode(text)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 1
        assert embedding.shape[1] == generator.embedding_dim

    def test_encode_multiple_texts(self):
        """Test encoding multiple texts."""
        generator = EmbeddingGenerator()

        texts = [
            "Kubernetes is a container orchestration platform",
            "Docker is a containerization platform",
            "Pods are the smallest deployable units in Kubernetes",
        ]

        embeddings = generator.encode(texts)

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == len(texts)
        assert embeddings.shape[1] == generator.embedding_dim

    def test_encode_query(self):
        """Test query encoding."""
        generator = EmbeddingGenerator()

        query = "What is Kubernetes?"
        embedding = generator.encode_query(query)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == generator.embedding_dim

    def test_encode_documents(self):
        """Test encoding Document objects."""
        generator = EmbeddingGenerator()

        documents = [
            Document(
                content="Kubernetes is a container orchestration platform",
                metadata={"source": "test.md", "type": "kubernetes_doc"},
                chunk_id="test_1",
            ),
            Document(
                content="Docker is a containerization platform",
                metadata={"source": "test.md", "type": "kubernetes_doc"},
                chunk_id="test_2",
            ),
        ]

        embeddings = generator.encode_documents(documents)

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == len(documents)
        assert embeddings.shape[1] == generator.embedding_dim


class TestVectorStore:
    """Test VectorStore integration."""

    @pytest.fixture
    def temp_vector_store(self):
        """Create a temporary vector store for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = VectorStore(
                collection_name="test_collection", persist_directory=temp_dir
            )
            yield store

    def test_vector_store_initialization(self, temp_vector_store):
        """Test vector store initialization."""
        assert temp_vector_store.collection_name == "test_collection"
        assert temp_vector_store.collection is not None

    def test_add_documents(self, temp_vector_store):
        """Test adding documents to vector store."""
        documents = [
            Document(
                content="Kubernetes is a container orchestration platform",
                metadata={"source": "test.md", "type": "kubernetes_doc"},
                chunk_id="test_1",
            ),
            Document(
                content="Docker is a containerization platform",
                metadata={"source": "test.md", "type": "kubernetes_doc"},
                chunk_id="test_2",
            ),
        ]

        # Create mock embeddings
        embeddings = np.random.rand(len(documents), 384)

        temp_vector_store.add_documents(documents, embeddings)

        # Verify documents were added
        stats = temp_vector_store.get_collection_stats()
        assert stats["count"] == len(documents)

    def test_search_by_text(self, temp_vector_store):
        """Test searching by text."""
        # Add test documents
        documents = [
            Document(
                content="Kubernetes is a container orchestration platform",
                metadata={"source": "test.md", "type": "kubernetes_doc"},
                chunk_id="test_1",
            ),
            Document(
                content="Docker is a containerization platform",
                metadata={"source": "test.md", "type": "kubernetes_doc"},
                chunk_id="test_2",
            ),
        ]

        embeddings = np.random.rand(len(documents), 384)
        temp_vector_store.add_documents(documents, embeddings)

        # Create mock embedding generator
        mock_generator = Mock()
        mock_generator.encode_query.return_value = np.random.rand(384)

        # Search
        results = temp_vector_store.search_by_text(
            "What is Kubernetes?", mock_generator, top_k=2
        )

        assert len(results) <= 2
        assert all("content" in result for result in results)
        assert all("metadata" in result for result in results)
        assert all("score" in result for result in results)

    def test_get_collection_stats(self, temp_vector_store):
        """Test getting collection statistics."""
        stats = temp_vector_store.get_collection_stats()

        assert "name" in stats
        assert "count" in stats
        assert "persist_directory" in stats
        assert stats["name"] == "test_collection"


class TestIngestionPipeline:
    """Test IngestionPipeline integration."""

    @pytest.fixture
    def temp_pipeline(self):
        """Create a temporary pipeline for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_store = VectorStore(
                collection_name="test_collection", persist_directory=temp_dir
            )
            embedding_generator = EmbeddingGenerator()
            doc_processor = KubernetesDocProcessor()

            pipeline = IngestionPipeline(
                vector_store=vector_store,
                embedding_generator=embedding_generator,
                doc_processor=doc_processor,
            )
            yield pipeline

    def test_ingest_from_text(self, temp_pipeline):
        """Test ingesting text directly."""
        text = """
        # Kubernetes Basics

        ## What is Kubernetes?

        Kubernetes is a container orchestration platform that automates the deployment, scaling, and management of containerized applications.

        ## Key Concepts

        - **Pods**: The smallest deployable units in Kubernetes
        - **Services**: Stable network endpoints for Pods
        - **Deployments**: Manage Pod replicas and updates
        """

        num_chunks = temp_pipeline.ingest_from_text(
            text, metadata={"source": "test_text"}, source_name="test_source"
        )

        assert num_chunks > 0

        # Verify documents were added to vector store
        stats = temp_pipeline.vector_store.get_collection_stats()
        assert stats["count"] == num_chunks

    def test_ingest_file(self, temp_pipeline):
        """Test ingesting a file."""
        # Create a temporary markdown file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """
            # Kubernetes Documentation

            ## What is Kubernetes?

            <details>
            <summary>Explain Kubernetes</summary><br><b>
            Kubernetes is an open-source container orchestration platform.
            </b></details>

            ## Pods

            A Pod is the smallest deployable unit in Kubernetes.
            """
            )
            temp_file = Path(f.name)

        try:
            num_chunks = temp_pipeline.ingest_file(temp_file)
            assert num_chunks > 0

            # Verify documents were added
            stats = temp_pipeline.vector_store.get_collection_stats()
            assert stats["count"] == num_chunks
        finally:
            temp_file.unlink()

    def test_ingest_directory(self, temp_pipeline):
        """Test ingesting a directory."""
        # Create a temporary directory with markdown files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test1.md").write_text("# Test Document 1\n\nContent here.")
            (temp_path / "test2.md").write_text("# Test Document 2\n\nMore content.")

            stats = temp_pipeline.ingest_directory(temp_path)

            assert stats["total_files"] == 2
            assert stats["processed_files"] == 2
            assert stats["total_chunks"] > 0
            assert len(stats["failed_files"]) == 0


class TestRetrieverIntegration:
    """Test Retriever integration."""

    @pytest.fixture
    def temp_retriever(self):
        """Create a temporary retriever for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vector_store = VectorStore(
                collection_name="test_collection", persist_directory=temp_dir
            )
            embedding_generator = EmbeddingGenerator()

            retriever = Retriever(
                vector_store=vector_store,
                embedding_generator=embedding_generator,
                use_rerank=False,
            )

            # Add some test documents
            documents = [
                Document(
                    content="Kubernetes is a container orchestration platform",
                    metadata={"source": "test.md", "type": "kubernetes_doc"},
                    chunk_id="test_1",
                ),
                Document(
                    content="Docker is a containerization platform",
                    metadata={"source": "test.md", "type": "kubernetes_doc"},
                    chunk_id="test_2",
                ),
                Document(
                    content="Question: What is a Pod? Answer: A Pod is the smallest deployable unit in Kubernetes.",
                    metadata={"source": "test.md", "type": "qa_pair"},
                    chunk_id="test_3",
                ),
            ]

            embeddings = embedding_generator.encode_documents(documents)
            vector_store.add_documents(documents, embeddings)

            yield retriever

    def test_retrieve_basic(self, temp_retriever):
        """Test basic retrieval."""
        results = temp_retriever.retrieve("What is Kubernetes?", top_k=3)

        assert len(results) <= 3
        assert all("content" in result for result in results)
        assert all("metadata" in result for result in results)
        assert all("score" in result for result in results)

    def test_retrieve_with_score_threshold(self, temp_retriever):
        """Test retrieval with score threshold."""
        results = temp_retriever.retrieve(
            "What is Kubernetes?", top_k=5, score_threshold=0.5
        )

        # All results should meet the score threshold
        for result in results:
            assert result["score"] >= 0.5

    def test_retrieve_by_category(self, temp_retriever):
        """Test retrieval by category."""
        results = temp_retriever.retrieve_by_category(
            "What is a Pod?", category="qa_pair", top_k=2
        )

        # All results should be from the specified category
        for result in results:
            assert result["metadata"]["type"] == "qa_pair"

    def test_multi_query_retrieve(self, temp_retriever):
        """Test multi-query retrieval."""
        queries = ["What is Kubernetes?", "What is Docker?", "What is a Pod?"]

        results = temp_retriever.multi_query_retrieve(
            queries, top_k=3, merge_strategy="unique"
        )

        assert len(results) <= 3
        # Check that results are unique (no duplicate content)
        contents = [result["content"] for result in results]
        assert len(contents) == len(set(contents))


class TestRAGGeneratorIntegration:
    """Test RAGGenerator integration."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "Kubernetes is a container orchestration platform that automates the deployment, scaling, and management of containerized applications."
        return mock_llm

    @pytest.fixture
    def rag_generator(self, mock_llm):
        """Create a RAG generator with mock LLM."""
        return RAGGenerator(llm=mock_llm)

    def test_generate_answer(self, rag_generator, mock_llm):
        """Test generating an answer."""
        retrieved_docs = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md"},
                "score": 0.9,
            },
            {
                "content": "Docker is a containerization platform",
                "metadata": {"source": "test.md"},
                "score": 0.8,
            },
        ]

        result = rag_generator.generate_answer(
            "What is Kubernetes?", retrieved_docs, temperature=0.3, max_tokens=100
        )

        assert "query" in result
        assert "answer" in result
        assert "num_sources" in result
        assert result["query"] == "What is Kubernetes?"
        assert result["num_sources"] == len(retrieved_docs)
        assert len(result["answer"]) > 0

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

    def test_generate_with_followup(self, rag_generator, mock_llm):
        """Test generating answer with conversation history."""
        retrieved_docs = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md"},
                "score": 0.9,
            }
        ]

        conversation_history = [
            {"role": "user", "content": "What is Docker?"},
            {"role": "assistant", "content": "Docker is a containerization platform."},
        ]

        # Store initial length before modification
        initial_length = len(conversation_history)

        result = rag_generator.generate_with_followup(
            "What is Kubernetes?", retrieved_docs, conversation_history
        )

        assert "query" in result
        assert "answer" in result
        assert "conversation_history" in result
        assert "sources" in result

        # Verify conversation history was updated (should add 2 new entries)
        expected_length = initial_length + 2
        assert len(result["conversation_history"]) == expected_length


class TestConfigIntegration:
    """Test configuration integration."""

    def test_config_loading(self):
        """Test loading configuration."""
        config, settings = get_config()

        assert isinstance(config, Config)
        assert isinstance(settings, Settings)

        # Check that config has all required sections
        assert hasattr(config, "embedding")
        assert hasattr(config, "vector_db")
        assert hasattr(config, "document_processing")
        assert hasattr(config, "retrieval")
        assert hasattr(config, "llm")
        assert hasattr(config, "api")
        assert hasattr(config, "logging")
        assert hasattr(config, "paths")

    def test_config_validation(self):
        """Test configuration validation."""
        config, settings = get_config()

        # Test embedding config
        assert config.embedding.model_name is not None
        assert config.embedding.embedding_dim > 0
        assert config.embedding.batch_size > 0

        # Test vector DB config
        assert config.vector_db.type is not None
        assert config.vector_db.collection_name is not None
        assert config.vector_db.distance_metric is not None

        # Test document processing config
        assert config.document_processing.chunk_size > 0
        assert config.document_processing.chunk_overlap >= 0
        assert len(config.document_processing.separators) > 0

        # Test retrieval config
        assert config.retrieval.top_k > 0
        assert 0 <= config.retrieval.score_threshold <= 1
        assert isinstance(config.retrieval.rerank, bool)

        # Test LLM config
        assert config.llm.provider is not None
        assert config.llm.model_name is not None
        assert 0 <= config.llm.temperature <= 2
        assert config.llm.max_tokens > 0


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def temp_e2e_setup(self):
        """Set up temporary environment for end-to-end testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create components
            vector_store = VectorStore(
                collection_name="e2e_test", persist_directory=temp_dir
            )
            embedding_generator = EmbeddingGenerator()
            doc_processor = KubernetesDocProcessor()

            pipeline = IngestionPipeline(
                vector_store=vector_store,
                embedding_generator=embedding_generator,
                doc_processor=doc_processor,
            )

            retriever = Retriever(
                vector_store=vector_store,
                embedding_generator=embedding_generator,
                use_rerank=False,
            )

            # Mock LLM
            mock_llm = Mock()
            mock_llm.generate.return_value = "Kubernetes is a container orchestration platform that automates the deployment, scaling, and management of containerized applications."

            generator = RAGGenerator(llm=mock_llm)

            yield {
                "pipeline": pipeline,
                "retriever": retriever,
                "generator": generator,
                "vector_store": vector_store,
            }

    def test_full_rag_pipeline(self, temp_e2e_setup):
        """Test the complete RAG pipeline."""
        pipeline = temp_e2e_setup["pipeline"]
        retriever = temp_e2e_setup["retriever"]
        generator = temp_e2e_setup["generator"]

        # Step 1: Ingest documents
        test_text = """
        # Kubernetes Documentation

        ## What is Kubernetes?

        Kubernetes is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications.

        ## Key Concepts

        ### Pods
        A Pod is the smallest deployable unit in Kubernetes. It represents a single instance of a running process in your cluster.

        ### Services
        A Service is an abstraction which defines a logical set of Pods and a policy by which to access them.

        ### Deployments
        A Deployment provides declarative updates for Pods and ReplicaSets.

        ## Q&A

        <details>
        <summary>What is the difference between Docker and Kubernetes?</summary><br><b>
        Docker is a containerization platform, while Kubernetes is a container orchestration platform. Docker helps you create and run containers, while Kubernetes helps you manage and orchestrate multiple containers across multiple machines.
        </b></details>
        """

        num_chunks = pipeline.ingest_from_text(
            test_text, metadata={"source": "e2e_test.md"}, source_name="e2e_test"
        )

        assert num_chunks > 0

        # Step 2: Retrieve documents
        query = "What is Kubernetes?"
        retrieved_docs = retriever.retrieve(query, top_k=3)

        assert len(retrieved_docs) > 0
        assert all("content" in doc for doc in retrieved_docs)
        assert all("score" in doc for doc in retrieved_docs)

        # Step 3: Generate answer
        result = generator.generate_answer(query, retrieved_docs, temperature=0.3)

        assert "query" in result
        assert "answer" in result
        assert "num_sources" in result
        assert result["query"] == query
        assert result["num_sources"] == len(retrieved_docs)
        assert len(result["answer"]) > 0

    def test_category_filtering_e2e(self, temp_e2e_setup):
        """Test category filtering in end-to-end scenario."""
        pipeline = temp_e2e_setup["pipeline"]
        retriever = temp_e2e_setup["retriever"]

        # Ingest documents with different types
        qa_text = """
        <details>
        <summary>What is Kubernetes?</summary><br><b>
        Kubernetes is a container orchestration platform.
        </b></details>

        <details>
        <summary>What is Docker?</summary><br><b>
        Docker is a containerization platform.
        </b></details>
        """

        doc_text = """
        # Kubernetes Overview

        Kubernetes is an open-source container orchestration platform.
        """

        pipeline.ingest_from_text(
            qa_text,
            metadata={"source": "qa.md", "type": "qa_pair"},
            source_name="qa_source",
        )

        pipeline.ingest_from_text(
            doc_text,
            metadata={"source": "doc.md", "type": "kubernetes_doc"},
            source_name="doc_source",
        )

        # Test retrieval by category
        qa_results = retriever.retrieve_by_category(
            "What is Kubernetes?", category="qa_pair", top_k=5
        )

        doc_results = retriever.retrieve_by_category(
            "What is Kubernetes?", category="kubernetes_doc", top_k=5
        )

        # Verify category filtering
        for result in qa_results:
            assert result["metadata"]["type"] == "qa_pair"

        for result in doc_results:
            assert result["metadata"]["type"] == "kubernetes_doc"

    def test_score_threshold_e2e(self, temp_e2e_setup):
        """Test score threshold filtering in end-to-end scenario."""
        pipeline = temp_e2e_setup["pipeline"]
        retriever = temp_e2e_setup["retriever"]

        # Ingest documents
        test_text = """
        # Kubernetes Documentation

        Kubernetes is a container orchestration platform.
        Docker is a containerization platform.
        Pods are the smallest deployable units in Kubernetes.
        """

        pipeline.ingest_from_text(
            test_text, metadata={"source": "test.md"}, source_name="test_source"
        )

        # Test with different score thresholds
        high_threshold_results = retriever.retrieve(
            "Kubernetes orchestration", top_k=5, score_threshold=0.8
        )

        low_threshold_results = retriever.retrieve(
            "Kubernetes orchestration", top_k=5, score_threshold=0.1
        )

        # High threshold should return fewer or equal results
        assert len(high_threshold_results) <= len(low_threshold_results)

        # All results should meet their respective thresholds
        for result in high_threshold_results:
            assert result["score"] >= 0.8

        for result in low_threshold_results:
            assert result["score"] >= 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
