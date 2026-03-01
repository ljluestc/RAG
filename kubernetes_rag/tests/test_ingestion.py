"""Ingestion pipeline tests — mock VectorStore, EmbeddingGenerator, and processors."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from src.ingestion.document_processor import (
    Document,
    DocumentChunker,
    KubernetesDocProcessor,
    MarkdownProcessor,
    PDFProcessor,
    UnifiedDocProcessor,
)
from src.ingestion.pipeline import IngestionPipeline


# ---------------------------------------------------------------------------
# MarkdownProcessor
# ---------------------------------------------------------------------------

class TestMarkdownProcessor:
    def setup_method(self):
        self.proc = MarkdownProcessor()

    def test_extract_sections(self):
        md = "# Intro\nSome text\n## Details\nMore text"
        sections = self.proc.extract_sections(md)
        assert len(sections) >= 2
        assert sections[0]["title"] == "Intro"

    def test_extract_code_blocks(self):
        md = "```python\nprint('hi')\n```"
        blocks = self.proc.extract_code_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"

    def test_parse_qa_pairs(self):
        md = '<details><summary>What is K8s?</summary><br><b>A platform</b></details>'
        pairs = self.proc.parse_qa_pairs(md)
        assert len(pairs) == 1
        assert "K8s" in pairs[0]["question"]


# ---------------------------------------------------------------------------
# DocumentChunker
# ---------------------------------------------------------------------------

class TestDocumentChunker:
    def setup_method(self):
        self.chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)

    def test_chunk_text(self):
        text = "Hello world. " * 50
        docs = self.chunker.chunk_text(text, {"source": "test"})
        assert len(docs) >= 1
        for d in docs:
            assert isinstance(d, Document)
            assert d.metadata["source"] == "test"

    def test_chunk_by_section(self):
        sections = [
            {"title": "Intro", "content": "Short content", "level": 1},
            {"title": "Details", "content": "X " * 200, "level": 2},
        ]
        docs = self.chunker.chunk_by_section(sections, {"source": "test"})
        assert len(docs) >= 2

    def test_empty_text(self):
        docs = self.chunker.chunk_text("", {})
        assert docs == []


# ---------------------------------------------------------------------------
# KubernetesDocProcessor
# ---------------------------------------------------------------------------

class TestKubernetesDocProcessor:
    def test_process_markdown_file(self, tmp_path):
        md = tmp_path / "k8s.md"
        md.write_text("# Kubernetes\n\nK8s is great.\n\n## Pods\n\nPods are units.")
        proc = KubernetesDocProcessor(chunk_size=500, chunk_overlap=50)
        docs = proc.process_file(md)
        assert len(docs) >= 1
        assert all(isinstance(d, Document) for d in docs)

    def test_process_directory(self, tmp_path):
        (tmp_path / "a.md").write_text("# A\ncontent")
        (tmp_path / "b.md").write_text("# B\ncontent")
        proc = KubernetesDocProcessor()
        docs = proc.process_directory(tmp_path)
        assert len(docs) >= 2


# ---------------------------------------------------------------------------
# PDFProcessor
# ---------------------------------------------------------------------------

class TestPDFProcessor:
    def test_process_pdf(self, tmp_path):
        # We can't easily create a real PDF, so mock pdfplumber
        proc = PDFProcessor(chunk_size=500, chunk_overlap=50)

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Kubernetes scheduling overview. " * 20

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            docs = proc.process_file(Path("/fake/doc.pdf"))

        assert len(docs) >= 1
        assert all(isinstance(d, Document) for d in docs)


# ---------------------------------------------------------------------------
# UnifiedDocProcessor
# ---------------------------------------------------------------------------

class TestUnifiedDocProcessor:
    def test_process_markdown(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# Test\nContent here")
        proc = UnifiedDocProcessor()
        docs = proc.process_file(md)
        assert len(docs) >= 1

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("data")
        proc = UnifiedDocProcessor()
        with pytest.raises(ValueError, match="Unsupported"):
            proc.process_file(f)


# ---------------------------------------------------------------------------
# IngestionPipeline
# ---------------------------------------------------------------------------

class TestIngestionPipeline:
    @pytest.fixture()
    def pipeline(self):
        mock_vs = MagicMock()
        mock_emb = MagicMock()
        mock_emb.encode_documents.return_value = np.random.rand(3, 384)
        mock_proc = MagicMock()
        mock_proc.process_file.return_value = [
            Document(content=f"chunk {i}", metadata={"source": "test.md"}, chunk_id=f"c{i}")
            for i in range(3)
        ]
        mock_proc.chunker.chunk_text.return_value = [
            Document(content="inline chunk", metadata={"source": "inline"}, chunk_id="ic0")
        ]
        mock_proc.chunker.chunk_size = 1000
        mock_proc.chunker.chunk_overlap = 200
        return IngestionPipeline(
            vector_store=mock_vs,
            embedding_generator=mock_emb,
            doc_processor=mock_proc,
        )

    def test_ingest_file(self, pipeline, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# Test\ncontent")
        n = pipeline.ingest_file(md)
        assert n == 3
        pipeline.vector_store.add_documents.assert_called_once()

    def test_ingest_file_empty(self, pipeline, tmp_path):
        md = tmp_path / "empty.md"
        md.write_text("")
        pipeline.doc_processor.process_file.return_value = []
        n = pipeline.ingest_file(md)
        assert n == 0

    def test_ingest_from_text(self, pipeline):
        n = pipeline.ingest_from_text("Some text about K8s", source_name="test")
        assert n == 1
        pipeline.vector_store.add_documents.assert_called_once()

    def test_ingest_directory(self, pipeline, tmp_path):
        (tmp_path / "a.md").write_text("# A\ncontent")
        n = pipeline.ingest_directory(tmp_path)
        assert isinstance(n, dict)
        assert "total_files" in n

    def test_ingest_directory_not_found(self, pipeline):
        with pytest.raises(ValueError, match="not found"):
            pipeline.ingest_directory(Path("/nonexistent"))

    def test_save_processing_stats(self, pipeline, tmp_path):
        stats = {"total_files": 1, "total_chunks": 5}
        out = tmp_path / "stats.json"
        pipeline.save_processing_stats(stats, out)
        assert out.exists()
