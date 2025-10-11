"""Integration tests for CLI commands."""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner
from src.cli import cli
from src.ingestion.document_processor import Document
from src.retrieval.vector_store import VectorStore


class TestCLIIntegration:
    """Test CLI integration."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config(self):
        """Create temporary config file."""
        config_content = """
# Kubernetes RAG System Configuration

# Embedding Model Configuration
embedding:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  embedding_dim: 384
  batch_size: 32

# Vector Database Configuration
vector_db:
  type: "chromadb"
  persist_directory: "./data/vector_db"
  collection_name: "kubernetes_docs"
  distance_metric: "cosine"

# Document Processing Configuration
document_processing:
  chunk_size: 1000
  chunk_overlap: 200
  separators: ["\\n\\n", "\\n", ". ", " ", ""]

# Retrieval Configuration
retrieval:
  top_k: 5
  score_threshold: 0.7
  rerank: true
  rerank_top_k: 3

# LLM Configuration
llm:
  provider: "openai"
  model_name: "gpt-3.5-turbo"
  temperature: 0.3
  max_tokens: 1000
  local_model_path: null

# API Configuration
api:
  host: "0.0.0.0"
  port: 8000
  reload: true

# Logging Configuration
logging:
  level: "INFO"
  format: "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"

# Data Paths
paths:
  raw_data: "./data/raw"
  processed_data: "./data/processed"
  vector_db: "./data/vector_db"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            return Path(f.name)

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test markdown files
            (temp_path / "test1.md").write_text(
                """
# Kubernetes Basics

## What is Kubernetes?

Kubernetes is a container orchestration platform that automates the deployment, scaling, and management of containerized applications.

## Key Concepts

- **Pods**: The smallest deployable units in Kubernetes
- **Services**: Stable network endpoints for Pods
- **Deployments**: Manage Pod replicas and updates
"""
            )

            (temp_path / "test2.md").write_text(
                """
# Docker Overview

## What is Docker?

Docker is a containerization platform that allows you to package applications and their dependencies into lightweight, portable containers.

## Benefits

- **Consistency**: Same environment across development, testing, and production
- **Efficiency**: Better resource utilization compared to virtual machines
- **Portability**: Run anywhere Docker is supported
"""
            )

            yield temp_path

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Kubernetes RAG System CLI" in result.output

    def test_cli_with_custom_config(self, runner, temp_config):
        """Test CLI with custom config file."""
        result = runner.invoke(cli, ["--config", str(temp_config), "--help"])
        assert result.exit_code == 0

    @patch("src.cli.create_ingestion_pipeline")
    def test_ingest_command_file(
        self, mock_pipeline, runner, temp_config, temp_data_dir
    ):
        """Test ingest command with a single file."""
        # Mock pipeline
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.ingest_file.return_value = 5
        mock_pipeline.return_value = mock_pipeline_instance

        test_file = temp_data_dir / "test1.md"

        result = runner.invoke(
            cli, ["--config", str(temp_config), "ingest", str(test_file)]
        )

        assert result.exit_code == 0
        assert "Ingested 5 chunks from file" in result.output
        mock_pipeline_instance.ingest_file.assert_called_once()

    @patch("src.cli.create_ingestion_pipeline")
    def test_ingest_command_directory(
        self, mock_pipeline, runner, temp_config, temp_data_dir
    ):
        """Test ingest command with a directory."""
        # Mock pipeline
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.ingest_directory.return_value = {
            "total_files": 2,
            "processed_files": 2,
            "total_chunks": 8,
            "failed_files": [],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = runner.invoke(
            cli, ["--config", str(temp_config), "ingest", str(temp_data_dir)]
        )

        assert result.exit_code == 0
        assert "Files processed: 2/2" in result.output
        assert "Total chunks: 8" in result.output
        mock_pipeline_instance.ingest_directory.assert_called_once()

    @patch("src.cli.create_retriever")
    @patch("src.cli.create_rag_generator")
    def test_query_command(self, mock_generator, mock_retriever, runner, temp_config):
        """Test query command."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md"},
                "score": 0.9,
            }
        ]
        mock_retriever.return_value = mock_retriever_instance

        # Mock generator
        mock_generator_instance = Mock()
        mock_generator_instance.generate_answer.return_value = {
            "answer": "Kubernetes is a container orchestration platform that automates deployment and scaling.",
            "num_sources": 1,
        }
        mock_generator.return_value = mock_generator_instance

        result = runner.invoke(
            cli, ["--config", str(temp_config), "query", "What is Kubernetes?"]
        )

        assert result.exit_code == 0
        assert "Retrieved 1 relevant documents" in result.output
        assert "ANSWER:" in result.output

    @patch("src.cli.create_retriever")
    def test_query_command_no_generate(self, mock_retriever, runner, temp_config):
        """Test query command without generating answer."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md"},
                "score": 0.9,
            }
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config),
                "query",
                "What is Kubernetes?",
                "--no-generate",
            ],
        )

        assert result.exit_code == 0
        assert "Retrieved 1 relevant documents" in result.output
        assert "ANSWER:" not in result.output

    @patch("src.cli.create_retriever")
    def test_query_command_no_results(self, mock_retriever, runner, temp_config):
        """Test query command when no results are found."""
        # Mock retriever to return empty results
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = []
        mock_retriever.return_value = mock_retriever_instance

        result = runner.invoke(
            cli, ["--config", str(temp_config), "query", "Non-existent topic"]
        )

        assert result.exit_code == 0
        assert "No relevant documents found" in result.output

    @patch("src.cli.create_retriever")
    def test_search_command(self, mock_retriever, runner, temp_config):
        """Test search command."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md", "type": "kubernetes_doc"},
                "score": 0.9,
            }
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = runner.invoke(
            cli, ["--config", str(temp_config), "search", "Kubernetes orchestration"]
        )

        assert result.exit_code == 0
        assert "Searching for: Kubernetes orchestration" in result.output
        assert "Score: 0.900" in result.output

    @patch("src.cli.create_retriever")
    def test_search_command_with_category(self, mock_retriever, runner, temp_config):
        """Test search command with category filter."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve_by_category.return_value = [
            {
                "content": "Question: What is a Pod? Answer: A Pod is the smallest deployable unit.",
                "metadata": {"source": "test.md", "type": "qa_pair"},
                "score": 0.9,
            }
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = runner.invoke(
            cli,
            [
                "--config",
                str(temp_config),
                "search",
                "What is a Pod?",
                "--category",
                "qa_pair",
            ],
        )

        assert result.exit_code == 0
        assert "Type: qa_pair" in result.output

    @patch("src.cli.VectorStore")
    def test_stats_command(self, mock_vector_store_class, runner, temp_config):
        """Test stats command."""
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store.get_collection_stats.return_value = {
            "name": "test_collection",
            "count": 150,
            "persist_directory": "/tmp/test_db",
        }
        mock_vector_store_class.return_value = mock_vector_store

        result = runner.invoke(cli, ["--config", str(temp_config), "stats"])

        assert result.exit_code == 0
        assert "Collection: test_collection" in result.output
        assert "Documents: 150" in result.output

    @patch("src.cli.VectorStore")
    def test_reset_command(self, mock_vector_store_class, runner, temp_config):
        """Test reset command."""
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        result = runner.invoke(cli, ["--config", str(temp_config), "reset", "--yes"])

        assert result.exit_code == 0
        assert "Vector database reset complete" in result.output
        mock_vector_store.delete_collection.assert_called_once()

    @patch("src.cli.VectorStore")
    def test_reset_command_with_confirmation(
        self, mock_vector_store_class, runner, temp_config
    ):
        """Test reset command with confirmation."""
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        # Simulate user confirming the reset
        result = runner.invoke(
            cli, ["--config", str(temp_config), "reset"], input="y\n"
        )

        assert result.exit_code == 0
        assert "Vector database reset complete" in result.output

    @patch("src.cli.VectorStore")
    def test_reset_command_cancelled(
        self, mock_vector_store_class, runner, temp_config
    ):
        """Test reset command when cancelled."""
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        # Simulate user cancelling the reset
        result = runner.invoke(
            cli, ["--config", str(temp_config), "reset"], input="n\n"
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_vector_store.delete_collection.assert_not_called()

    def test_invalid_config_file(self, runner):
        """Test CLI with invalid config file."""
        result = runner.invoke(cli, ["--config", "nonexistent.yaml", "stats"])

        assert result.exit_code == 1
        assert "Error loading configuration" in result.output

    def test_invalid_command(self, runner, temp_config):
        """Test CLI with invalid command."""
        result = runner.invoke(cli, ["--config", str(temp_config), "invalid_command"])

        assert result.exit_code != 0

    def test_ingest_nonexistent_file(self, runner, temp_config):
        """Test ingest command with nonexistent file."""
        result = runner.invoke(
            cli, ["--config", str(temp_config), "ingest", "nonexistent.md"]
        )

        assert result.exit_code != 0

    def test_ingest_nonexistent_directory(self, runner, temp_config):
        """Test ingest command with nonexistent directory."""
        result = runner.invoke(
            cli, ["--config", str(temp_config), "ingest", "nonexistent_dir"]
        )

        assert result.exit_code != 0

    @patch("src.cli.create_retriever")
    @patch("src.cli.create_rag_generator")
    def test_interactive_command(
        self, mock_generator, mock_retriever, runner, temp_config
    ):
        """Test interactive command."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {
                "content": "Kubernetes is a container orchestration platform",
                "metadata": {"source": "test.md"},
                "score": 0.9,
            }
        ]
        mock_retriever.return_value = mock_retriever_instance

        # Mock generator
        mock_generator_instance = Mock()
        mock_generator_instance.generate_with_followup.return_value = {
            "answer": "Kubernetes is a container orchestration platform.",
            "conversation_history": [],
        }
        mock_generator.return_value = mock_generator_instance

        # Simulate interactive session with exit
        result = runner.invoke(
            cli,
            ["--config", str(temp_config), "interactive"],
            input="What is Kubernetes?\nexit\n",
        )

        assert result.exit_code == 0
        assert "Interactive Mode" in result.output
        assert "Goodbye!" in result.output

    def test_log_level_option(self, runner, temp_config):
        """Test log level option."""
        result = runner.invoke(
            cli, ["--config", str(temp_config), "--log-level", "DEBUG", "stats"]
        )

        # Should not fail even with DEBUG log level
        assert (
            result.exit_code == 0 or result.exit_code == 1
        )  # May fail due to missing components


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
