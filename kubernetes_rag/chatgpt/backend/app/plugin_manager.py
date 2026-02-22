"""Plugin system with registry and built-in plugins."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import PluginID, PluginInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plugin ABC
# ---------------------------------------------------------------------------

class Plugin(ABC):
    """Base class for all plugins."""

    @property
    @abstractmethod
    def plugin_id(self) -> PluginID:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    async def execute(self, query: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Run the plugin and return structured output."""

    def info(self) -> PluginInfo:
        return PluginInfo(id=self.plugin_id, name=self.name, description=self.description)


# ---------------------------------------------------------------------------
# Built-in: Web Search (stub)
# ---------------------------------------------------------------------------

class WebSearchPlugin(Plugin):
    plugin_id = PluginID.web_search
    name = "Web Search"
    description = "Search the web for up-to-date information."

    async def execute(self, query: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Stub implementation — replace with real search API (SerpAPI / Tavily)."""
        logger.info(f"[WebSearch] query={query}")
        return {
            "plugin": self.plugin_id.value,
            "results": [
                {"title": f"Web result for: {query}", "snippet": "Simulated web search result.", "url": "https://example.com"}
            ],
            "result_text": f"Web search results for '{query}': [simulated — integrate a real search API here]",
        }


# ---------------------------------------------------------------------------
# Built-in: Code Interpreter (stub)
# ---------------------------------------------------------------------------

class CodeInterpreterPlugin(Plugin):
    plugin_id = PluginID.code_interpreter
    name = "Code Interpreter"
    description = "Execute Python code snippets in a sandboxed environment."

    async def execute(self, query: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Stub implementation — replace with sandboxed exec (e.g. E2B, modal)."""
        logger.info(f"[CodeInterpreter] code={query[:100]}")
        return {
            "plugin": self.plugin_id.value,
            "output": "[sandbox] Code execution is a stub — integrate a sandboxed runtime.",
            "result_text": "Code interpreter ran your snippet (stub).",
        }


# ---------------------------------------------------------------------------
# Built-in: RAG Lookup
# ---------------------------------------------------------------------------

class RAGLookupPlugin(Plugin):
    plugin_id = PluginID.rag_lookup
    name = "RAG Lookup"
    description = "Search the knowledge base using RAG retrieval."

    def __init__(self, rag_service=None):
        self._rag = rag_service

    async def execute(self, query: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        logger.info(f"[RAGLookup] query={query}")
        if self._rag is None:
            return {"plugin": self.plugin_id.value, "result_text": "RAG service not configured."}

        result = self._rag.query(query)
        return {
            "plugin": self.plugin_id.value,
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "result_text": result.get("answer", "No results found."),
        }


# ---------------------------------------------------------------------------
# Plugin Registry / Manager
# ---------------------------------------------------------------------------

class PluginManager:
    """Registry of available plugins."""

    def __init__(self, rag_service=None):
        self._plugins: Dict[PluginID, Plugin] = {}
        self._register_defaults(rag_service)

    def _register_defaults(self, rag_service=None):
        self.register(WebSearchPlugin())
        self.register(CodeInterpreterPlugin())
        self.register(RAGLookupPlugin(rag_service=rag_service))

    def register(self, plugin: Plugin):
        self._plugins[plugin.plugin_id] = plugin

    def get(self, plugin_id: PluginID) -> Optional[Plugin]:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> List[PluginInfo]:
        return [p.info() for p in self._plugins.values()]

    async def run(self, plugin_id: PluginID, query: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        plugin = self.get(plugin_id)
        if not plugin:
            return {"error": f"Plugin {plugin_id} not found"}
        try:
            return await plugin.execute(query, context)
        except Exception as exc:
            logger.error(f"Plugin {plugin_id} error: {exc}")
            return {"error": str(exc)}

    async def run_many(self, plugin_ids: List[PluginID], query: str) -> List[Dict[str, Any]]:
        """Run multiple plugins and collect results."""
        import asyncio
        tasks = [self.run(pid, query) for pid in plugin_ids]
        return await asyncio.gather(*tasks)
