"""Vector store implementation using ChromaDB."""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import numpy as np
from chromadb.config import Settings
from chromadb.utils import embedding_functions


class VectorStore:
    """Vector store for storing and retrieving document embeddings."""

    def __init__(
        self,
        collection_name: str = "kubernetes_docs",
        persist_directory: str = "./data/vector_db",
        distance_metric: str = "cosine",
    ):
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the collection
            persist_directory: Directory to persist the database
            distance_metric: Distance metric (cosine, l2, ip)
        """
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": distance_metric}
        )

    def add_documents(
        self, documents: List, embeddings: np.ndarray, batch_size: int = 100
    ):
        """
        Add documents to the vector store.

        Args:
            documents: List of Document objects
            embeddings: Numpy array of embeddings
            batch_size: Batch size for adding documents
        """
        total_docs = len(documents)

        for i in range(0, total_docs, batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            ids = [doc.chunk_id for doc in batch_docs]
            texts = [doc.content for doc in batch_docs]
            metadatas = [doc.metadata for doc in batch_docs]

            self.collection.add(
                ids=ids,
                embeddings=batch_embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
            )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[str], List[Dict], List[float]]:
        """
        Search for similar documents.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            Tuple of (documents, metadatas, distances)
        """
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=filter_dict,
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        return documents, metadatas, distances

    def search_by_text(
        self,
        query_text: str,
        embedding_generator,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search using text query.

        Args:
            query_text: Text query
            embedding_generator: EmbeddingGenerator instance
            top_k: Number of results
            filter_dict: Optional metadata filter

        Returns:
            List of search results
        """
        query_embedding = embedding_generator.encode_query(query_text)
        documents, metadatas, distances = self.search(
            query_embedding, top_k=top_k, filter_dict=filter_dict
        )

        results = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            results.append(
                {
                    "content": doc,
                    "metadata": metadata,
                    "score": 1 - distance,  # Convert distance to similarity score
                }
            )

        return results

    def delete_collection(self):
        """Delete the collection."""
        self.client.delete_collection(name=self.collection_name)

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        count = self.collection.count()
        return {
            "name": self.collection_name,
            "count": count,
            "persist_directory": str(self.persist_directory),
        }

    def update_document(
        self,
        doc_id: str,
        embedding: np.ndarray,
        document: str,
        metadata: Dict[str, Any],
    ):
        """Update a document in the collection."""
        self.collection.update(
            ids=[doc_id],
            embeddings=[embedding.tolist()],
            documents=[document],
            metadatas=[metadata],
        )

    def delete_documents(self, doc_ids: List[str]):
        """Delete documents by IDs."""
        self.collection.delete(ids=doc_ids)

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        results = self.collection.get(
            ids=[doc_id], include=["embeddings", "documents", "metadatas"]
        )

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "content": results["documents"][0],
                "metadata": results["metadatas"][0],
                "embedding": results["embeddings"][0],
            }

        return None

    def list_all_documents(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all documents in the collection."""
        results = self.collection.get(
            limit=limit, offset=offset, include=["documents", "metadatas"]
        )

        documents = []
        for doc_id, content, metadata in zip(
            results["ids"], results["documents"], results["metadatas"]
        ):
            documents.append({"id": doc_id, "content": content, "metadata": metadata})

        return documents


class HybridVectorStore:
    """Hybrid vector store combining dense and sparse retrieval."""

    def __init__(
        self,
        collection_name: str = "kubernetes_docs",
        persist_directory: str = "./data/vector_db",
    ):
        self.dense_store = VectorStore(
            collection_name=f"{collection_name}_dense",
            persist_directory=persist_directory,
        )

        # In a production system, you might use a separate store for sparse vectors
        # For now, we'll use the same store with different handling

    def add_documents(self, documents: List, dense_embeddings: np.ndarray):
        """Add documents with hybrid embeddings."""
        self.dense_store.add_documents(documents, dense_embeddings)

    def hybrid_search(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        top_k: int = 5,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining dense and sparse retrieval.

        Args:
            query_embedding: Dense query embedding
            query_text: Query text for sparse search
            top_k: Number of results
            dense_weight: Weight for dense search
            sparse_weight: Weight for sparse search

        Returns:
            List of hybrid search results
        """
        # Get dense results
        dense_docs, dense_metas, dense_dists = self.dense_store.search(
            query_embedding, top_k=top_k * 2  # Get more results for reranking
        )

        # Simple keyword matching for sparse component
        # In production, use proper BM25 or similar
        sparse_scores = []
        query_terms = set(query_text.lower().split())

        for doc in dense_docs:
            doc_terms = set(doc.lower().split())
            overlap = len(query_terms.intersection(doc_terms))
            sparse_scores.append(overlap / len(query_terms) if query_terms else 0)

        # Combine scores
        combined_results = []
        for i, (doc, meta, dense_dist) in enumerate(
            zip(dense_docs, dense_metas, dense_dists)
        ):
            dense_score = 1 - dense_dist
            sparse_score = sparse_scores[i]
            combined_score = (dense_weight * dense_score) + (
                sparse_weight * sparse_score
            )

            combined_results.append(
                {
                    "content": doc,
                    "metadata": meta,
                    "score": combined_score,
                    "dense_score": dense_score,
                    "sparse_score": sparse_score,
                }
            )

        # Sort by combined score and return top_k
        combined_results.sort(key=lambda x: x["score"], reverse=True)
        return combined_results[:top_k]
