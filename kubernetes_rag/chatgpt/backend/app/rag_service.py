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
            self._generator = create_rag_generator(config)
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

        answer_data = self._generator.generate_answer(
            question, results, temperature=temperature
        )
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
