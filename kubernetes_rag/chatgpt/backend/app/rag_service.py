"""RAG service — thin wrapper around the parent project's retriever + generator.

Imports from the kubernetes_rag src package so we can reuse embeddings,
vector store, and LLM generation without duplicating logic.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ensure the parent project root is importable
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # chatgpt/backend/app -> kubernetes_rag
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


class RAGService:
    """High-level RAG query interface backed by the kubernetes_rag pipeline."""

    def __init__(self, config_path: str | None = None):
        self._retriever = None
        self._generator = None
        self._ready = False
        self._config_path = config_path or str(_PROJECT_ROOT / "config" / "config.yaml")

    def _lazy_init(self):
        if self._ready:
            return
        try:
            from src.utils.config_loader import load_config
            from src.retrieval.retriever import create_retriever
            from src.generation.llm import create_rag_generator

            config = load_config(self._config_path)
            self._retriever = create_retriever(config)
            try:
                self._generator = create_rag_generator(config)
            except Exception as exc:
                logger.warning(f"RAG generator unavailable, using extractive fallback: {exc}")
                self._generator = None
            self._ready = True
            logger.info("RAG service initialized successfully")
        except Exception as exc:
            logger.warning(f"RAG service unavailable: {exc}")

    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        top_k: int = 5,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """Run full RAG pipeline: retrieve + generate answer."""
        self._lazy_init()
        if not self._ready:
            return {"answer": "RAG service is not available.", "citations": []}

        results = self._retriever.retrieve(question, top_k=top_k)
        if not results:
            return {"answer": "No relevant documents found.", "citations": []}

        if self._generator is None:
            # Extractive fallback keeps system grounded even without LLM API keys.
            citations = []
            for idx, doc in enumerate(results, 1):
                meta = doc.get("metadata", {})
                citations.append({
                    "citation_id": idx,
                    "source": meta.get("source", "unknown"),
                    "filename": meta.get("filename", "unknown"),
                    "doc_type": meta.get("type", "unknown"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "section_title": meta.get("section_title"),
                    "page_number": meta.get("page_number"),
                    "relevance_score": float(doc.get("score", 0.0)),
                    "passage": (doc.get("content", "")[:300] or ""),
                    "url": None,
                })
            bullets = []
            for i, c in enumerate(citations[:4], 1):
                snippet = c["passage"].strip().replace("\n", " ")
                bullets.append(f"- [Source {i}] {snippet}")
            fallback_answer = (
                "Grounded retrieval results (LLM unavailable; extractive mode):\n\n"
                + "\n".join(bullets)
            )
            return {
                "answer": fallback_answer,
                "citations": citations,
                "model_used": "extractive-fallback",
                "tokens_used": {"prompt": 0, "completion": 0, "total": 0},
                "num_sources": len(results),
            }

        answer_data = self._generator.generate_answer(question, results, temperature=temperature)
        return {
            "answer": answer_data.get("answer", ""),
            "citations": answer_data.get("citations", []),
            "model_used": answer_data.get("model_used", ""),
            "tokens_used": answer_data.get("tokens_used", {}),
            "num_sources": len(results),
        }

    def search(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve documents without generating an answer."""
        self._lazy_init()
        if not self._ready:
            return []
        return self._retriever.retrieve(question, top_k=top_k)

    @property
    def is_ready(self) -> bool:
        self._lazy_init()
        return self._ready
