"""Comprehensive test suite for CLI module to achieve 100% coverage."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click import ClickException
from click.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.cli import (
    cli,
    ingest_command,
    interactive_command,
    query_command,
    reset_command,
    search_command,
    stats_command,
)
from src.utils.config_loader import get_config


class TestCLICreation:
    """Test CLI creation and initialization."""

    def test_cli_exists(self):
        """Test that CLI exists."""
        assert cli is not None

    def test_cli_commands(self):
        """Test that CLI has all required commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "ingest" in result.output
        assert "query" in result.output
        assert "search" in result.output
        assert "interactive" in result.output
        assert "stats" in result.output
        assert "reset" in result.output


class TestIngestCommand:
    """Test ingest command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("src.cli.create_ingestion_pipeline")
    def test_ingest_file_success(self, mock_pipeline):
        """Test successful file ingestion."""
        # Mock pipeline
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.ingest_file.return_value = {
            "chunks_created": 5,
            "files_processed": 1,
        }
        mock_pipeline.return_value = mock_pipeline_instance

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Document\n\nThis is a test document.")
            temp_file = f.name

        try:
            result = self.runner.invoke(cli, ["ingest", temp_file])

            assert result.exit_code == 0
            assert "Successfully ingested" in result.output
        finally:
            os.unlink(temp_file)

    @patch("src.cli.create_ingestion_pipeline")
    def test_ingest_directory_success(self, mock_pipeline):
        """Test successful directory ingestion."""
        # Mock pipeline
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.ingest_directory.return_value = {
            "chunks_created": 10,
            "files_processed": 3,
        }
        mock_pipeline.return_value = mock_pipeline_instance

        # Create temporary directory with files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test1.md").write_text("# Test 1\nContent 1")
            (temp_path / "test2.md").write_text("# Test 2\nContent 2")

            result = self.runner.invoke(
                cli, ["ingest", str(temp_path), "--file-pattern", "*.md"]
            )

            assert result.exit_code == 0
            assert "Successfully ingested" in result.output

    def test_ingest_file_not_found(self):
        """Test ingest with non-existent file."""
        result = self.runner.invoke(cli, ["ingest", "non_existent_file.md"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_ingest_directory_not_found(self):
        """Test ingest with non-existent directory."""
        result = self.runner.invoke(cli, ["ingest", "non_existent_directory"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    @patch("src.cli.create_ingestion_pipeline")
    def test_ingest_pipeline_error(self, mock_pipeline):
        """Test ingest with pipeline error."""
        # Mock pipeline to raise exception
        mock_pipeline.side_effect = Exception("Pipeline error")

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Document\n\nThis is a test document.")
            temp_file = f.name

        try:
            result = self.runner.invoke(cli, ["ingest", temp_file])

            assert result.exit_code != 0
            assert "error" in result.output.lower()
        finally:
            os.unlink(temp_file)


class TestQueryCommand:
    """Test query command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("src.cli.create_retriever")
    @patch("src.cli.create_rag_generator")
    def test_query_success(self, mock_generator, mock_retriever):
        """Test successful query."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        # Mock generator
        mock_generator_instance = Mock()
        mock_generator_instance.generate_answer.return_value = {
            "answer": "Test answer",
            "sources": [],
            "metadata": {},
        }
        mock_generator.return_value = mock_generator_instance

        result = self.runner.invoke(cli, ["query", "What is Kubernetes?"])

        assert result.exit_code == 0
        assert "Test answer" in result.output

    @patch("src.cli.create_retriever")
    def test_query_search_only(self, mock_retriever):
        """Test query with search only (no generation)."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = self.runner.invoke(
            cli, ["query", "What is Kubernetes?", "--search-only"]
        )

        assert result.exit_code == 0
        assert "Test content" in result.output

    @patch("src.cli.create_retriever")
    def test_query_with_top_k(self, mock_retriever):
        """Test query with custom top_k."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": f"Test content {i}", "score": 0.9, "metadata": {}}
            for i in range(3)
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = self.runner.invoke(
            cli, ["query", "What is Kubernetes?", "--top-k", "3"]
        )

        assert result.exit_code == 0
        assert "Test content" in result.output

    @patch("src.cli.create_retriever")
    def test_query_retriever_error(self, mock_retriever):
        """Test query with retriever error."""
        # Mock retriever to raise exception
        mock_retriever.side_effect = Exception("Retriever error")

        result = self.runner.invoke(cli, ["query", "What is Kubernetes?"])

        assert result.exit_code != 0
        assert "error" in result.output.lower()

    @patch("src.cli.create_rag_generator")
    def test_query_generator_error(self, mock_generator):
        """Test query with generator error."""
        # Mock generator to raise exception
        mock_generator.side_effect = Exception("Generator error")

        result = self.runner.invoke(cli, ["query", "What is Kubernetes?"])

        assert result.exit_code != 0
        assert "error" in result.output.lower()


class TestSearchCommand:
    """Test search command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("src.cli.create_retriever")
    def test_search_success(self, mock_retriever):
        """Test successful search."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = self.runner.invoke(cli, ["search", "Kubernetes deployment"])

        assert result.exit_code == 0
        assert "Test content" in result.output

    @patch("src.cli.create_retriever")
    def test_search_with_category(self, mock_retriever):
        """Test search with category filter."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve_by_category.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = self.runner.invoke(
            cli, ["search", "Kubernetes deployment", "--category", "qa_pair"]
        )

        assert result.exit_code == 0
        assert "Test content" in result.output

    @patch("src.cli.create_retriever")
    def test_search_with_score_threshold(self, mock_retriever):
        """Test search with score threshold."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        result = self.runner.invoke(
            cli, ["search", "Kubernetes deployment", "--score-threshold", "0.8"]
        )

        assert result.exit_code == 0
        assert "Test content" in result.output

    @patch("src.cli.create_retriever")
    def test_search_retriever_error(self, mock_retriever):
        """Test search with retriever error."""
        # Mock retriever to raise exception
        mock_retriever.side_effect = Exception("Retriever error")

        result = self.runner.invoke(cli, ["search", "Kubernetes deployment"])

        assert result.exit_code != 0
        assert "error" in result.output.lower()


class TestInteractiveCommand:
    """Test interactive command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("src.cli.create_retriever")
    @patch("src.cli.create_rag_generator")
    def test_interactive_mode(self, mock_generator, mock_retriever):
        """Test interactive mode."""
        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        # Mock generator
        mock_generator_instance = Mock()
        mock_generator_instance.generate_answer.return_value = {
            "answer": "Test answer",
            "sources": [],
            "metadata": {},
        }
        mock_generator.return_value = mock_generator_instance

        # Simulate user input
        result = self.runner.invoke(
            cli, ["interactive"], input="What is Kubernetes?\nexit\n"
        )

        assert result.exit_code == 0
        assert "Interactive mode" in result.output or "Test answer" in result.output

    @patch("src.cli.create_retriever")
    def test_interactive_mode_error(self, mock_retriever):
        """Test interactive mode with error."""
        # Mock retriever to raise exception
        mock_retriever.side_effect = Exception("Retriever error")

        # Simulate user input
        result = self.runner.invoke(
            cli, ["interactive"], input="What is Kubernetes?\nexit\n"
        )

        assert result.exit_code == 0  # Should handle error gracefully


class TestStatsCommand:
    """Test stats command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("src.cli.create_vector_store")
    def test_stats_success(self, mock_vector_store):
        """Test successful stats command."""
        # Mock vector store
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.get_stats.return_value = {
            "total_documents": 10,
            "total_chunks": 50,
            "collections": ["kubernetes_docs"],
        }
        mock_vector_store.return_value = mock_vector_store_instance

        result = self.runner.invoke(cli, ["stats"])

        assert result.exit_code == 0
        assert "total_documents" in result.output or "10" in result.output

    @patch("src.cli.create_vector_store")
    def test_stats_error(self, mock_vector_store):
        """Test stats command with error."""
        # Mock vector store to raise exception
        mock_vector_store.side_effect = Exception("Vector store error")

        result = self.runner.invoke(cli, ["stats"])

        assert result.exit_code != 0
        assert "error" in result.output.lower()


class TestResetCommand:
    """Test reset command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("src.cli.create_vector_store")
    def test_reset_with_confirmation(self, mock_vector_store):
        """Test reset command with confirmation."""
        # Mock vector store
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.reset.return_value = True
        mock_vector_store.return_value = mock_vector_store_instance

        result = self.runner.invoke(cli, ["reset", "--yes"])

        assert result.exit_code == 0
        assert "reset" in result.output.lower()

    @patch("src.cli.create_vector_store")
    def test_reset_without_confirmation(self, mock_vector_store):
        """Test reset command without confirmation."""
        # Mock vector store
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.reset.return_value = True
        mock_vector_store.return_value = mock_vector_store_instance

        # Simulate user declining
        result = self.runner.invoke(cli, ["reset"], input="n\n")

        assert result.exit_code == 0
        assert (
            "cancelled" in result.output.lower() or "aborted" in result.output.lower()
        )

    @patch("src.cli.create_vector_store")
    def test_reset_error(self, mock_vector_store):
        """Test reset command with error."""
        # Mock vector store to raise exception
        mock_vector_store.side_effect = Exception("Vector store error")

        result = self.runner.invoke(cli, ["reset", "--yes"])

        assert result.exit_code != 0
        assert "error" in result.output.lower()


class TestCLIValidation:
    """Test CLI validation."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_query_empty_string(self):
        """Test query with empty string."""
        result = self.runner.invoke(cli, ["query", ""])

        assert result.exit_code != 0

    def test_search_empty_string(self):
        """Test search with empty string."""
        result = self.runner.invoke(cli, ["search", ""])

        assert result.exit_code != 0

    def test_top_k_invalid_value(self):
        """Test query with invalid top_k value."""
        result = self.runner.invoke(cli, ["query", "test", "--top-k", "0"])

        assert result.exit_code != 0

    def test_score_threshold_invalid_value(self):
        """Test search with invalid score_threshold value."""
        result = self.runner.invoke(cli, ["search", "test", "--score-threshold", "1.5"])

        assert result.exit_code != 0


class TestCLIPerformance:
    """Test CLI performance."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_help_performance(self):
        """Test help command performance."""
        import time

        start_time = time.time()
        result = self.runner.invoke(cli, ["--help"])
        end_time = time.time()

        assert result.exit_code == 0
        assert (end_time - start_time) < 1.0

    @patch("src.cli.create_vector_store")
    def test_stats_performance(self, mock_vector_store):
        """Test stats command performance."""
        import time

        # Mock vector store
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.get_stats.return_value = {
            "total_documents": 10,
            "total_chunks": 50,
        }
        mock_vector_store.return_value = mock_vector_store_instance

        start_time = time.time()
        result = self.runner.invoke(cli, ["stats"])
        end_time = time.time()

        assert result.exit_code == 0
        assert (end_time - start_time) < 2.0


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("src.cli.create_ingestion_pipeline")
    @patch("src.cli.create_retriever")
    @patch("src.cli.create_rag_generator")
    def test_full_workflow(self, mock_generator, mock_retriever, mock_pipeline):
        """Test full CLI workflow."""
        # Mock pipeline
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.ingest_file.return_value = {
            "chunks_created": 5,
            "files_processed": 1,
        }
        mock_pipeline.return_value = mock_pipeline_instance

        # Mock retriever
        mock_retriever_instance = Mock()
        mock_retriever_instance.retrieve.return_value = [
            {"content": "Test content", "score": 0.9, "metadata": {}}
        ]
        mock_retriever.return_value = mock_retriever_instance

        # Mock generator
        mock_generator_instance = Mock()
        mock_generator_instance.generate_answer.return_value = {
            "answer": "Test answer",
            "sources": [],
            "metadata": {},
        }
        mock_generator.return_value = mock_generator_instance

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Document\n\nThis is a test document.")
            temp_file = f.name

        try:
            # Test ingest
            ingest_result = self.runner.invoke(cli, ["ingest", temp_file])
            assert ingest_result.exit_code == 0

            # Test query
            query_result = self.runner.invoke(
                cli, ["query", "What is this document about?"]
            )
            assert query_result.exit_code == 0

            # Test search
            search_result = self.runner.invoke(cli, ["search", "test document"])
            assert search_result.exit_code == 0

        finally:
            os.unlink(temp_file)


# Test markers for pytest
@pytest.mark.unit
class TestUnitCLI(TestCLICreation, TestCLIValidation):
    """Unit tests for CLI module."""

    pass


@pytest.mark.integration
class TestIntegrationCLI(
    TestIngestCommand, TestQueryCommand, TestSearchCommand, TestCLIIntegration
):
    """Integration tests for CLI module."""

    pass


@pytest.mark.cli
class TestCLISpecific(TestInteractiveCommand, TestStatsCommand, TestResetCommand):
    """CLI-specific tests."""

    pass


@pytest.mark.slow
class TestSlowCLI(TestCLIPerformance):
    """Slow tests for CLI module."""

    pass
