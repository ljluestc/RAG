"""CLI tests that patch factories at their true call sites."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tests.conftest import make_mock_generator_answer, make_mock_retriever_results


@pytest.fixture()
def runner():
    return CliRunner()


def test_ingest_file_command(runner, tmp_path, mock_config):
    md_file = tmp_path / "input.md"
    md_file.write_text("# Hello\nworld")

    pipeline = MagicMock()
    pipeline.ingest_file.return_value = 4

    with (
        patch("src.cli.get_config", return_value=mock_config),
        patch("src.cli.create_ingestion_pipeline", return_value=pipeline),
    ):
        from src.cli import cli

        result = runner.invoke(cli, ["ingest", str(md_file)])

    assert result.exit_code == 0
    assert "4 chunks" in result.output
    pipeline.ingest_file.assert_called_once()


def test_query_command_with_generation(runner, mock_config):
    retriever = MagicMock()
    retriever.retrieve.return_value = make_mock_retriever_results()

    generator = MagicMock()
    generator.generate_answer.return_value = make_mock_generator_answer("What is Kubernetes?")

    with (
        patch("src.cli.get_config", return_value=mock_config),
        patch("src.cli.create_retriever", return_value=retriever),
        patch("src.cli.create_rag_generator", return_value=generator),
    ):
        from src.cli import cli

        result = runner.invoke(cli, ["query", "What is Kubernetes?"])

    assert result.exit_code == 0
    assert "ANSWER" in result.output
    retriever.retrieve.assert_called_once()
    generator.generate_answer.assert_called_once()


def test_query_command_without_generation(runner, mock_config):
    retriever = MagicMock()
    retriever.retrieve.return_value = make_mock_retriever_results(2)

    with (
        patch("src.cli.get_config", return_value=mock_config),
        patch("src.cli.create_retriever", return_value=retriever),
    ):
        from src.cli import cli

        result = runner.invoke(cli, ["query", "--no-generate", "pods"])

    assert result.exit_code == 0
    assert "ANSWER" not in result.output


def test_search_command_by_category(runner, mock_config):
    retriever = MagicMock()
    retriever.retrieve_by_category.return_value = make_mock_retriever_results(1)

    with (
        patch("src.cli.get_config", return_value=mock_config),
        patch("src.cli.create_retriever", return_value=retriever),
    ):
        from src.cli import cli

        result = runner.invoke(cli, ["search", "--category", "qa_pair", "controller"])

    assert result.exit_code == 0
    assert "Score" in result.output
    retriever.retrieve_by_category.assert_called_once()


def test_stats_and_reset_commands(runner, mock_config):
    fake_store = MagicMock()
    fake_store.get_collection_stats.return_value = {
        "name": "kubernetes_docs",
        "count": 22,
        "persist_directory": "./data/vector_db",
    }

    with (
        patch("src.cli.get_config", return_value=mock_config),
        patch("src.retrieval.vector_store.VectorStore", return_value=fake_store),
    ):
        from src.cli import cli

        stats_result = runner.invoke(cli, ["stats"])
        reset_result = runner.invoke(cli, ["reset", "--yes"])

    assert stats_result.exit_code == 0
    assert "22" in stats_result.output
    assert reset_result.exit_code == 0
    assert "reset complete" in reset_result.output.lower()
    fake_store.delete_collection.assert_called_once()
