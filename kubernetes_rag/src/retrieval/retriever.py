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

        # Hybrid retrieval hook: combine dense scores with lightweight BM25 on retrieved set.
        results = self._apply_hybrid_scoring(query, results)

        # Filter by score threshold
        results = [r for r in results if r["score"] >= score_threshold]

        if not results:
            logger.warning("No results found above score threshold")
            return []

        # Deduplicate by content before re-ranking
        seen_content = set()
        deduped = []
        for r in results:
            key = r["content"].strip()[:200]
            if key not in seen_content:
                seen_content.add(key)
                deduped.append(r)
        results = deduped

        # Re-rank if enabled
        if self.use_rerank and self.reranker:
            logger.info(f"Re-ranking {len(results)} results")
            results = self._rerank(query, results, rerank_top_k or top_k)
        else:
            results = results[:top_k]

        logger.info(f"Retrieved {len(results)} documents")
        return results

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if t]

    def _bm25_scores(self, query: str, docs: List[str], k1: float = 1.5, b: float = 0.75) -> List[float]:
        """Compute lightweight BM25 scores over candidate docs."""
        if not docs:
            return []
        tokenized_docs = [self._tokenize(d) for d in docs]
        query_terms = self._tokenize(query)
        if not query_terms:
            return [0.0] * len(docs)

        n_docs = len(tokenized_docs)
        avgdl = sum(len(d) for d in tokenized_docs) / max(1, n_docs)

        # Document frequencies
        df: Dict[str, int] = {}
        for toks in tokenized_docs:
            for t in set(toks):
                df[t] = df.get(t, 0) + 1

        scores: List[float] = []
        for toks in tokenized_docs:
            tf: Dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            dl = len(toks) or 1
            score = 0.0
            for term in query_terms:
                if term not in tf:
                    continue
                term_df = df.get(term, 0)
                idf = np.log(1 + (n_docs - term_df + 0.5) / (term_df + 0.5))
                freq = tf[term]
                denom = freq + k1 * (1 - b + b * (dl / max(1.0, avgdl)))
                score += idf * ((freq * (k1 + 1)) / max(denom, 1e-9))
            scores.append(float(score))

        return scores

    def _apply_hybrid_scoring(
        self,
        query: str,
        results: List[Dict[str, Any]],
        dense_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Blend dense similarity with BM25 for hybrid retrieval."""
        if not results:
            return results
        docs = [r.get("content", "") for r in results]
        bm25_scores = self._bm25_scores(query, docs)
        max_bm25 = max(bm25_scores) if bm25_scores else 0.0
        for r, bm25 in zip(results, bm25_scores):
            bm25_norm = (bm25 / max_bm25) if max_bm25 > 0 else 0.0
            dense = float(r.get("score", 0.0))
            r["dense_score"] = dense
            r["bm25_score"] = bm25_norm
            r["score"] = (dense_weight * dense) + (bm25_weight * bm25_norm)
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
