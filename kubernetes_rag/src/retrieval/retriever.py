"""Retrieval module with re-ranking capabilities."""

from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import CrossEncoder

from ..ingestion.embeddings import EmbeddingGenerator
from ..utils.logger import get_logger
from .vector_store import VectorStore

logger = get_logger()


class Retriever:
    """Document retriever with optional re-ranking."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator,
        rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_rerank: bool = True,
    ):
        """
        Initialize the retriever.

        Args:
            vector_store: Vector store instance
            embedding_generator: Embedding generator instance
            rerank_model: Model name for re-ranking
            use_rerank: Whether to use re-ranking
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.use_rerank = use_rerank

        if use_rerank:
            logger.info(f"Loading re-ranker model: {rerank_model}")
            self.reranker = CrossEncoder(rerank_model)
        else:
            self.reranker = None

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_dict: Optional[Dict[str, Any]] = None,
        rerank_top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            filter_dict: Optional metadata filter
            rerank_top_k: Number of results to return after re-ranking

        Returns:
            List of retrieved documents with scores
        """
        logger.info(f"Retrieving documents for query: {query[:100]}...")

        # Initial retrieval
        initial_k = top_k * 3 if self.use_rerank and self.reranker else top_k

        results = self.vector_store.search_by_text(
            query, self.embedding_generator, top_k=initial_k, filter_dict=filter_dict
        )

        # Filter by score threshold
        results = [r for r in results if r["score"] >= score_threshold]

        if not results:
            logger.warning("No results found above score threshold")
            return []

        # Re-rank if enabled
        if self.use_rerank and self.reranker:
            logger.info(f"Re-ranking {len(results)} results")
            results = self._rerank(query, results, rerank_top_k or top_k)
        else:
            results = results[:top_k]

        logger.info(f"Retrieved {len(results)} documents")
        return results

    def _rerank(
        self, query: str, results: List[Dict[str, Any]], top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results using cross-encoder.

        Args:
            query: Original query
            results: Initial results
            top_k: Number of results to return

        Returns:
            Re-ranked results
        """
        # Prepare pairs for re-ranking
        pairs = [[query, r["content"]] for r in results]

        # Get re-ranking scores
        rerank_scores = self.reranker.predict(pairs)

        # Update results with new scores
        for i, score in enumerate(rerank_scores):
            results[i]["rerank_score"] = float(score)
            results[i]["original_score"] = results[i]["score"]

        # Sort by rerank score
        results.sort(key=lambda x: x["rerank_score"], reverse=True)

        return results[:top_k]

    def retrieve_with_context(
        self, query: str, top_k: int = 5, context_window: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents with surrounding context chunks.

        Args:
            query: Search query
            top_k: Number of results
            context_window: Number of chunks before/after to include

        Returns:
            Results with context
        """
        results = self.retrieve(query, top_k=top_k)

        enhanced_results = []
        for result in results:
            # metadata = result["metadata"]

            # Try to get surrounding chunks
            # chunk_index = metadata.get("chunk_index", 0)
            # source = metadata.get("source", "")

            # This is a simplified version - in production you'd
            # retrieve actual surrounding chunks from the store
            enhanced_results.append(
                {
                    **result,
                    "context_window": context_window,
                    "has_context": False,  # Would be True if we found context
                }
            )

        return enhanced_results

    def retrieve_by_category(
        self, query: str, category: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents filtered by category.

        Args:
            query: Search query
            category: Category to filter by (e.g., 'qa_pair', 'kubernetes_doc')
            top_k: Number of results

        Returns:
            Filtered results
        """
        filter_dict = {"type": category}
        return self.retrieve(query, top_k=top_k, filter_dict=filter_dict)

    def multi_query_retrieve(
        self, queries: List[str], top_k: int = 5, merge_strategy: str = "concatenate"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using multiple query variations.

        Args:
            queries: List of query variations
            top_k: Number of results per query
            merge_strategy: How to merge results (concatenate, unique, weighted)

        Returns:
            Merged results
        """
        all_results = []

        for query in queries:
            results = self.retrieve(query, top_k=top_k)
            all_results.extend(results)

        if merge_strategy == "unique":
            # Remove duplicates based on content
            seen_contents = set()
            unique_results = []

            for result in all_results:
                content = result["content"]
                if content not in seen_contents:
                    seen_contents.add(content)
                    unique_results.append(result)

            return unique_results[:top_k]

        elif merge_strategy == "concatenate":
            return all_results[:top_k]

        elif merge_strategy == "weighted":
            # Average scores for duplicate contents
            content_map = {}

            for result in all_results:
                content = result["content"]
                if content not in content_map:
                    content_map[content] = {
                        **result,
                        "scores": [result["score"]],
                        "count": 1,
                    }
                else:
                    content_map[content]["scores"].append(result["score"])
                    content_map[content]["count"] += 1

            # Calculate weighted scores
            weighted_results = []
            for content, data in content_map.items():
                avg_score = sum(data["scores"]) / len(data["scores"])
                weighted_results.append({**data, "score": avg_score, "weighted": True})

            weighted_results.sort(key=lambda x: x["score"], reverse=True)
            return weighted_results[:top_k]

        return all_results[:top_k]


def create_retriever(config: dict) -> Retriever:
    """
    Create a retriever from configuration.

    Args:
        config: Configuration object

    Returns:
        Retriever instance
    """
    vector_store = VectorStore(
        collection_name=config.vector_db.collection_name,
        persist_directory=config.vector_db.persist_directory,
        distance_metric=config.vector_db.distance_metric,
    )

    embedding_generator = EmbeddingGenerator(model_name=config.embedding.model_name)

    retriever = Retriever(
        vector_store=vector_store,
        embedding_generator=embedding_generator,
        use_rerank=config.retrieval.rerank,
    )

    return retriever
