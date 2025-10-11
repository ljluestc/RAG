"""LLM integration for answer generation."""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger()


class LLMBase(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text from prompt."""
        pass


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

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text using OpenAI."""
        if self.client is None:
            # Mock response for testing
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

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicLLM(LLMBase):
    """Anthropic Claude LLM provider."""

    def __init__(
        self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"
    ):
        """Initialize Anthropic LLM."""
        import anthropic

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model

    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text using Anthropic."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            return message.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class LocalLLM(LLMBase):
    """Local LLM provider (placeholder for local models)."""

    def __init__(self, model_path: str):
        """Initialize local LLM."""
        self.model_path = model_path
        logger.warning("Local LLM is not fully implemented yet")

    def generate(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000
    ) -> str:
        """Generate text using local model."""
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
        Generate answer using retrieved documents.

        Args:
            query: User query
            retrieved_docs: Retrieved documents from vector store
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate
            include_sources: Include source references

        Returns:
            Dictionary with answer and metadata
        """
        # Build context from retrieved documents
        context = self._build_context(retrieved_docs)

        # Create prompt
        prompt = self._create_prompt(query, context)

        logger.info("Generating answer with LLM")

        # Generate answer
        answer = self.llm.generate(
            prompt, temperature=temperature, max_tokens=max_tokens
        )

        result = {"query": query, "answer": answer, "num_sources": len(retrieved_docs)}

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

    def _build_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents."""
        context_parts = []

        for i, doc in enumerate(retrieved_docs, 1):
            content = doc["content"]
            score = doc.get("score", 0.0)

            context_parts.append(
                f"[Document {i}] (Relevance: {score:.2f})\n{content}\n"
            )

        return "\n".join(context_parts)

    def _create_prompt(self, query: str, context: str) -> str:
        """Create prompt for LLM."""
        prompt_template = """You are a Kubernetes expert assistant. Answer the user's question based on the provided context from Kubernetes documentation.

Context:
{context}

User Question: {query}

Instructions:
1. Answer the question based primarily on the provided context
2. Be concise and accurate
3. If the context doesn't contain enough information, acknowledge this
4. Include specific Kubernetes concepts, commands, or examples when relevant
5. Format your answer clearly with proper markdown if needed

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
