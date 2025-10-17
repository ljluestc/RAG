"""Embedding generation using sentence transformers."""

from typing import List, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class EmbeddingGenerator:
    """Generate embeddings for text using sentence transformers."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = None,
    ):
        """
        Initialize the embedding generator.

        Args:
            model_name: Name of the sentence transformer model
            device: Device to use (cuda/cpu). Auto-detected if None.
        """
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = True,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
            show_progress: Show progress bar
            normalize: Normalize embeddings to unit length

        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )

        return embeddings

    def encode_documents(
        self, documents: List, batch_size: int = 32, show_progress: bool = True
    ) -> List[np.ndarray]:
        """
        Generate embeddings for a list of Document objects.

        Args:
            documents: List of Document objects
            batch_size: Batch size for encoding
            show_progress: Show progress bar

        Returns:
            List of embeddings
        """
        texts = [doc.content for doc in documents]

        embeddings = self.encode(
            texts, batch_size=batch_size, show_progress=show_progress
        )

        return embeddings

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self.embedding_dim

    def encode_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        Encode a query for retrieval.

        Args:
            query: Query text
            normalize: Normalize embedding

        Returns:
            Query embedding
        """
        return self.encode(
            query, batch_size=1, show_progress=False, normalize=normalize
        )[0]


class HybridEmbedding:
    """Hybrid embedding combining dense and sparse representations."""

    def __init__(
        self, dense_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.dense_encoder = EmbeddingGenerator(dense_model_name)

    def encode_dense(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate dense embeddings."""
        return self.dense_encoder.encode(texts, **kwargs)

    def encode_sparse(self, texts: Union[str, List[str]]) -> List[dict]:
        """
        Generate sparse embeddings (BM25-style).
        This is a simplified version - in production you might use a proper BM25
        implementation.
        """
        if isinstance(texts, str):
            texts = [texts]

        sparse_embeddings = []
        for text in texts:
            # Simple word frequency as sparse representation
            words = text.lower().split()
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1

            sparse_embeddings.append(word_freq)

        return sparse_embeddings

    def encode_hybrid(
        self,
        texts: Union[str, List[str]],
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ):
        """
        Generate hybrid embeddings.

        Args:
            texts: Text(s) to encode
            dense_weight: Weight for dense embeddings
            sparse_weight: Weight for sparse embeddings

        Returns:
            Dictionary with dense and sparse embeddings
        """
        dense_embs = self.encode_dense(texts)
        sparse_embs = self.encode_sparse(texts)

        return {
            "dense": dense_embs,
            "sparse": sparse_embs,
            "weights": {"dense": dense_weight, "sparse": sparse_weight},
        }


# Backwards compatibility alias
EmbeddingsManager = EmbeddingGenerator


def create_embeddings(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2", device: str = None
) -> EmbeddingGenerator:
    """
    Factory function to create an embedding generator.

    Args:
        model_name: Name of the sentence transformer model
        device: Device to use (cuda/cpu)

    Returns:
        EmbeddingGenerator instance
    """
    return EmbeddingGenerator(model_name=model_name, device=device)
