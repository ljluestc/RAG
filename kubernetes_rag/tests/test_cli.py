"""CLI tests that patch factories at their true call sites."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from conftest import make_mock_generator_answer, make_mock_retriever_results


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
"""CLI tests — patches factory functions at their call-site in src.cli."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

def make_mock_retriever_results(n: int = 3):
    return [
        {
            "content": f"Document {i} about Kubernetes.",
            "metadata": {"source": f"doc_{i}.md", "filename": f"doc_{i}.md", "type": "kubernetes_doc"},
            "score": round(0.95 - i * 0.05, 2),
        }
        for i in range(n)
    ]


def make_mock_generator_answer(query: str = "test query"):
    return {
        "query": query,
        "answer": "Kubernetes is a container orchestration platform. [Source 1]",
        "num_sources": 3,
        "citations": [
            {
                "citation_id": 1,
                "source": "doc_0.md",
                "filename": "doc_0.md",
                "doc_type": "kubernetes_doc",
                "chunk_index": 0,
                "section_title": None,
                "page_number": None,
                "relevance_score": 0.95,
                "passage": "Document 0 about Kubernetes.",
                "url": None,
            }
        ],
        "model_used": "test-model",
        "tokens_used": {"prompt": 100, "completion": 50, "total": 150},
        "sources": [],
    }


@pytest.fixture()
def runner():
    return CliRunner()


def _mock_config():
    """Return (mock_config, mock_settings) matching src.utils.config_loader.Config."""
    from src.utils.config_loader import Config, Settings

    cfg = Config(
        embedding={"model_name": "sentence-transformers/all-MiniLM-L6-v2", "embedding_dim": 384, "batch_size": 32},
        vector_db={"type": "chromadb", "persist_directory": "/tmp/test_vdb", "collection_name": "test", "distance_metric": "cosine"},
        document_processing={"chunk_size": 1000, "chunk_overlap": 200, "separators": ["\n\n", "\n", " ", ""]},
        retrieval={"top_k": 5, "score_threshold": 0.7, "rerank": False, "rerank_top_k": 3},
        llm={"provider": "openai", "model_name": "gpt-3.5-turbo", "temperature": 0.3, "max_tokens": 1000},
        api={"host": "0.0.0.0", "port": 8000, "reload": False},
        logging={"level": "INFO", "format": "{time} {level} {message}"},
        paths={"raw_data": "./data/raw", "processed_data": "./data/processed", "vector_db": "./data/vector_db"},
    )
    settings = Settings()
    return cfg, settings


# ═══════════════════════════════════════════════════════════════════════════
# Ingest command
# ═══════════════════════════════════════════════════════════════════════════

class TestIngestCommand:
    def test_ingest_file(self, runner, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\nworld")

        mock_pipeline = MagicMock()
        mock_pipeline.ingest_file.return_value = 3

        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.cli.create_ingestion_pipeline", return_value=mock_pipeline),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["ingest", str(md_file)])

        assert result.exit_code == 0
        assert "3 chunks" in result.output

    def test_ingest_directory(self, runner, tmp_path):
        (tmp_path / "a.md").write_text("# A\nContent")
        (tmp_path / "b.md").write_text("# B\nContent")

        mock_pipeline = MagicMock()
        mock_pipeline.ingest_directory.return_value = {
            "total_files": 2, "processed_files": 2, "total_chunks": 6, "failed_files": []
        }

        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.cli.create_ingestion_pipeline", return_value=mock_pipeline),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["ingest", str(tmp_path)])

        assert result.exit_code == 0
        assert "complete" in result.output.lower()


# ═══════════════════════════════════════════════════════════════════════════
# Query command
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryCommand:
    def test_query_with_answer(self, runner):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = make_mock_retriever_results()

        mock_generator = MagicMock()
        mock_generator.generate_answer.return_value = make_mock_generator_answer("What is a Pod?")

        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.cli.create_retriever", return_value=mock_retriever),
            patch("src.cli.create_rag_generator", return_value=mock_generator),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["query", "What is a Pod?"])

        assert result.exit_code == 0
        assert "ANSWER" in result.output

    def test_query_no_generate(self, runner):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = make_mock_retriever_results()

        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.cli.create_retriever", return_value=mock_retriever),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["query", "--no-generate", "pods"])

        assert result.exit_code == 0
        assert "ANSWER" not in result.output

    def test_query_no_results(self, runner):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []

        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.cli.create_retriever", return_value=mock_retriever),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["query", "xyz"])

        assert result.exit_code == 0
        assert "No relevant documents" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# Search command
# ═══════════════════════════════════════════════════════════════════════════

class TestSearchCommand:
    def test_search_basic(self, runner):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = make_mock_retriever_results()

        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.cli.create_retriever", return_value=mock_retriever),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["search", "deployment"])

        assert result.exit_code == 0
        assert "Score" in result.output

    def test_search_by_category(self, runner):
        mock_retriever = MagicMock()
        mock_retriever.retrieve_by_category.return_value = make_mock_retriever_results(2)

        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.cli.create_retriever", return_value=mock_retriever),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["search", "--category", "qa_pair", "pods"])

        assert result.exit_code == 0


# ═══════════════════════════════════════════════════════════════════════════
# Stats command
# ═══════════════════════════════════════════════════════════════════════════

class TestStatsCommand:
    def test_stats(self, runner):
        mock_vs = MagicMock()
        mock_vs.get_collection_stats.return_value = {
            "name": "test", "count": 10, "persist_directory": "/tmp"
        }
        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.retrieval.vector_store.VectorStore", return_value=mock_vs),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["stats"])

        assert result.exit_code == 0
        assert "10" in result.output


# ═══════════════════════════════════════════════════════════════════════════
# Reset command
# ═══════════════════════════════════════════════════════════════════════════

class TestResetCommand:
    def test_reset_with_yes(self, runner):
        mock_vs = MagicMock()
        with (
            patch("src.cli.get_config", return_value=_mock_config()),
            patch("src.retrieval.vector_store.VectorStore", return_value=mock_vs),
        ):
            from src.cli import cli
            result = runner.invoke(cli, ["reset", "--yes"])

        assert result.exit_code == 0
        assert "reset complete" in result.output.lower()
        mock_vs.delete_collection.assert_called_once()

    def test_reset_declined(self, runner):
        with patch("src.cli.get_config", return_value=_mock_config()):
            from src.cli import cli
            result = runner.invoke(cli, ["reset"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output or "cancel" in result.output.lower()
