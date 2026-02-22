"""LLM integration for answer generation."""

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger()


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English)."""
    return max(1, len(text) // 4)


def build_source_url(source_path: str, filename: str) -> Optional[str]:
    """Build a web URL from a source path.

    - arXiv papers  → https://arxiv.org/abs/<id>
    - devops-exercises → GitHub blob link
    - Otherwise → None
    """
    if not source_path:
        return None

    # arXiv papers: extract ID from filename like "2106.09685v2.pdf"
    if "arxiv_papers" in source_path:
        stem = Path(source_path).stem  # e.g. "2106.09685v2"
        # Strip version suffix for cleaner URL
        arxiv_id = re.sub(r"v\d+$", "", stem)
        return f"https://arxiv.org/abs/{arxiv_id}"

    # DevOps exercises: map local clone path to GitHub URL
    if "devops_exercises" in source_path or "devops-exercises" in source_path:
        # Find the path after "topics/"
        m = re.search(r"topics/(.+)$", source_path)
        if m:
            relative = m.group(1)
            return f"https://github.com/bregman-arie/devops-exercises/blob/master/topics/{relative}"

    return None


class LLMBase(ABC):
    """Base class for LLM providers."""

    model: str = "unknown"

    @abstractmethod
    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text from prompt."""
        pass

    def get_model_name(self) -> str:
        """Return the model identifier."""
        return getattr(self, "model", "unknown")


class OpenAILLM(LLMBase):
    """OpenAI LLM provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """Initialize OpenAI LLM."""
        from openai import OpenAI

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            # In test mode, use a mock client
            if os.getenv("TESTING") == "true":
                self.client = None
                self.model = model
                return
            raise ValueError("OpenAI API key not found")

        # Check for test mode even with API key
        if os.getenv("TESTING") == "true":
            self.client = None
            self.model = model
            return

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text using OpenAI."""
        if self.client is None:
            self.last_usage = {"input_tokens": 0, "output_tokens": 0}
            return "This is a mock response for testing purposes."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful Kubernetes expert assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if response.usage:
                self.last_usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                }

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicLLM(LLMBase):
    """Anthropic Claude LLM provider."""

    def __init__(
        self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"
    ):
        """Initialize Anthropic LLM."""
        import anthropic

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_KEY")
        if not self.api_key:
            # In test mode, use a mock client
            if os.getenv("TESTING") == "true":
                self.client = None
                self.model = model
                return
            raise ValueError("Anthropic API key not found")

        # Check for test mode even with API key
        if os.getenv("TESTING") == "true":
            self.client = None
            self.model = model
            return

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text using Anthropic."""
        if self.client is None:
            self.last_usage = {"input_tokens": 0, "output_tokens": 0}
            return "This is a mock response for testing purposes."

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            self.last_usage = {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            }

            return message.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class LocalLLM(LLMBase):
    """Local LLM provider (placeholder for local models)."""

    def __init__(self, model: Optional[str] = None, model_path: Optional[str] = None):
        """Initialize local LLM."""
        # Support both model and model_path for compatibility
        self.model = model or model_path or "local-model"
        self.model_path = model_path

        # In test mode, just set up the model name
        if os.getenv("TESTING") == "true":
            return

        logger.warning("Local LLM is not fully implemented yet")

    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text using local model."""
        # Mock response for testing
        if os.getenv("TESTING") == "true":
            return "This is a mock response for testing purposes."

        # This is a placeholder - implement with transformers or llama.cpp
        raise NotImplementedError("Local LLM generation not implemented")


class RAGGenerator:
    """RAG-based answer generator."""

    def __init__(self, llm: LLMBase):
        """
        Initialize RAG generator.

        Args:
            llm: LLM instance
        """
        self.llm = llm

    def generate_answer(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 1000,
        include_sources: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate answer using retrieved documents with citation grounding.

        Args:
            query: User query
            retrieved_docs: Retrieved documents from vector store
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate
            include_sources: Include source references

        Returns:
            Dictionary with answer, citations, and metadata
        """
        # Build citation grounding first so we can use citation IDs in the prompt
        citations = self._extract_citations(retrieved_docs)

        # Build a mapping from source path -> citation ID for context labeling
        source_to_cid: Dict[str, int] = {}
        for c in citations:
            source_to_cid[c["source"]] = c["citation_id"]

        # Build context from retrieved documents using citation IDs
        context = self._build_context(retrieved_docs, source_to_cid)

        # Create prompt with citation instructions
        prompt = self._create_prompt(query, context)

        logger.info("Generating answer with LLM")

        # Generate answer
        answer = self.llm.generate(
            prompt, temperature=temperature, max_tokens=max_tokens
        )

        # Post-process: normalise any remaining [Document N] references
        answer = self._normalize_citation_refs(answer, retrieved_docs, source_to_cid)

        # Use real token counts from LLM if available, otherwise estimate
        usage = getattr(self.llm, "last_usage", None)
        if usage:
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
        else:
            prompt_tokens = estimate_tokens(prompt)
            completion_tokens = estimate_tokens(answer)

        result = {
            "query": query,
            "answer": answer,
            "num_sources": len(retrieved_docs),
            "citations": citations,
            "model_used": self.llm.get_model_name(),
            "tokens_used": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": prompt_tokens + completion_tokens,
            },
        }

        if include_sources:
            result["sources"] = [
                {
                    "content": doc["content"][:200] + "...",
                    "metadata": doc["metadata"],
                    "score": doc.get("score", 0.0),
                }
                for doc in retrieved_docs
            ]

        return result

    def _extract_citations(self, retrieved_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract structured citations, deduplicated by source file.

        Multiple chunks from the same file are merged into one citation
        keeping the highest relevance score and best section title.
        """
        # Group by (source_path) — keep highest-scoring entry per file
        best_by_source: Dict[str, Dict[str, Any]] = {}
        for doc in retrieved_docs:
            meta = doc.get("metadata", {})
            source_path = meta.get("source", "unknown")
            score = doc.get("score", 0.0)

            existing = best_by_source.get(source_path)
            if existing is None or score > existing["relevance_score"]:
                filename = meta.get("filename", "unknown")
                best_by_source[source_path] = {
                    "source": source_path,
                    "filename": filename,
                    "doc_type": meta.get("type", "unknown"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "section_title": meta.get("section_title", None),
                    "page_number": meta.get("page_number", None),
                    "relevance_score": score,
                    "passage": doc["content"][:300],
                    "url": build_source_url(source_path, filename),
                }
            elif existing is not None and score == existing["relevance_score"]:
                # Same score — prefer the one with a section title
                if not existing.get("section_title") and meta.get("section_title"):
                    existing["section_title"] = meta["section_title"]

        # Sort by relevance descending, assign citation IDs
        sorted_citations = sorted(
            best_by_source.values(), key=lambda c: c["relevance_score"], reverse=True
        )
        for i, c in enumerate(sorted_citations, 1):
            c["citation_id"] = i

        return sorted_citations

    def _build_context(
        self,
        retrieved_docs: List[Dict[str, Any]],
        source_to_cid: Optional[Dict[str, int]] = None,
    ) -> str:
        """Build context string from retrieved documents.

        Each chunk is labelled with [Source N] where N is the citation ID so the
        LLM can reference sources that map directly to the citation panel.
        """
        context_parts = []

        for doc in retrieved_docs:
            content = doc["content"]
            score = doc.get("score", 0.0)
            meta = doc.get("metadata", {})
            source_path = meta.get("source", "unknown")
            filename = meta.get("filename", "unknown")
            section = meta.get("section_title", "")

            cid = (source_to_cid or {}).get(source_path)
            label = f"Source {cid}" if cid else filename
            section_hint = f" — {section}" if section else ""

            context_parts.append(
                f"[{label}{section_hint}] (Relevance: {score:.2f})\n{content}\n"
            )

        return "\n".join(context_parts)

    @staticmethod
    def _normalize_citation_refs(
        answer: str,
        retrieved_docs: List[Dict[str, Any]],
        source_to_cid: Dict[str, int],
    ) -> str:
        """Replace any leftover [Document N] references with [Source <cid>]."""
        def _replace(m: re.Match) -> str:
            idx = int(m.group(1)) - 1  # 0-based
            if 0 <= idx < len(retrieved_docs):
                src = retrieved_docs[idx].get("metadata", {}).get("source", "")
                cid = source_to_cid.get(src)
                if cid:
                    return f"[Source {cid}]"
            return m.group(0)

        return re.sub(r"\[Document\s+(\d+)\]", _replace, answer)

    def _create_prompt(self, query: str, context: str) -> str:
        """Create prompt for LLM with citation grounding instructions."""
        prompt_template = """You are a knowledgeable assistant. Answer the user's question based on the provided context documents.

Context:
{context}

User Question: {query}

Instructions:
1. Answer the question based primarily on the provided context
2. Cite your sources using the [Source N] labels shown above (e.g. [Source 1], [Source 3])
3. Be concise and accurate
4. If the context doesn't contain enough information, acknowledge this
5. Include specific concepts, commands, or examples when relevant
6. Format your answer clearly with proper markdown if needed

Answer:"""

        return prompt_template.format(context=context, query=query)

    def generate_with_followup(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate answer with conversation history.

        Args:
            query: Current query
            retrieved_docs: Retrieved documents
            conversation_history: Previous conversation turns

        Returns:
            Answer with updated conversation history
        """
        if conversation_history is None:
            conversation_history = []

        # Build context
        context = self._build_context(retrieved_docs)

        # Create prompt with history
        prompt = self._create_conversational_prompt(
            query, context, conversation_history
        )

        # Generate answer
        answer = self.llm.generate(prompt)

        # Update history
        conversation_history.append({"role": "user", "content": query})
        conversation_history.append({"role": "assistant", "content": answer})

        return {
            "query": query,
            "answer": answer,
            "conversation_history": conversation_history,
            "sources": retrieved_docs,
        }

    def _create_conversational_prompt(
        self, query: str, context: str, history: List[Dict[str, str]]
    ) -> str:
        """Create conversational prompt with history."""
        history_text = ""
        for turn in history[-3:]:  # Last 3 turns
            role = turn["role"].capitalize()
            content = turn["content"]
            history_text += f"{role}: {content}\n\n"

        prompt = f"""You are a Kubernetes expert assistant engaged in a conversation.

Previous conversation:
{history_text}

Current context from documentation:
{context}

Current question: {query}

Provide a helpful answer considering the conversation history and current context.

Answer:"""

        return prompt


def create_llm(provider: str, **kwargs) -> LLMBase:
    """
    Create LLM instance based on provider.

    Args:
        provider: LLM provider (openai, anthropic, local)
        **kwargs: Additional arguments for the provider

    Returns:
        LLM instance
    """
    if provider.lower() == "openai":
        return OpenAILLM(**kwargs)
    elif provider.lower() == "anthropic":
        return AnthropicLLM(**kwargs)
    elif provider.lower() == "local":
        return LocalLLM(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_rag_generator(config: dict) -> RAGGenerator:
    """
    Create RAG generator from configuration.

    Args:
        config: Configuration object

    Returns:
        RAGGenerator instance
    """
    llm = create_llm(provider=config.llm.provider, model=config.llm.model_name)

    return RAGGenerator(llm=llm)
