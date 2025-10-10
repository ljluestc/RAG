"""Tests for retrieval module."""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from src.retrieval.retriever import Retriever


class TestRetriever:
    """Test Retriever class."""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        mock_vector_store = Mock()
        mock_embedding_gen = Mock()
        mock_embedding_gen.encode_query.return_value = np.array([0.1] * 384)

        return mock_vector_store, mock_embedding_gen

    def test_retrieve(self, mock_components):
        """Test basic retrieval."""
        vector_store, embedding_gen = mock_components

        # Mock search results
        vector_store.search_by_text.return_value = [
            {
                'content': 'Test content 1',
                'metadata': {'source': 'test1.md'},
                'score': 0.9
            },
            {
                'content': 'Test content 2',
                'metadata': {'source': 'test2.md'},
                'score': 0.8
            }
        ]

        retriever = Retriever(
            vector_store=vector_store,
            embedding_generator=embedding_gen,
            use_rerank=False
        )

        results = retriever.retrieve('test query', top_k=2)

        assert len(results) == 2
        assert results[0]['score'] == 0.9

    def test_score_threshold(self, mock_components):
        """Test score threshold filtering."""
        vector_store, embedding_gen = mock_components

        vector_store.search_by_text.return_value = [
            {
                'content': 'High score content',
                'metadata': {'source': 'test1.md'},
                'score': 0.9
            },
            {
                'content': 'Low score content',
                'metadata': {'source': 'test2.md'},
                'score': 0.3
            }
        ]

        retriever = Retriever(
            vector_store=vector_store,
            embedding_generator=embedding_gen,
            use_rerank=False
        )

        results = retriever.retrieve(
            'test query',
            top_k=5,
            score_threshold=0.5
        )

        assert len(results) == 1
        assert results[0]['score'] >= 0.5

    def test_retrieve_by_category(self, mock_components):
        """Test category filtering."""
        vector_store, embedding_gen = mock_components

        vector_store.search_by_text.return_value = [
            {
                'content': 'Q&A content',
                'metadata': {'type': 'qa_pair'},
                'score': 0.9
            }
        ]

        retriever = Retriever(
            vector_store=vector_store,
            embedding_generator=embedding_gen,
            use_rerank=False
        )

        results = retriever.retrieve_by_category(
            'test query',
            category='qa_pair',
            top_k=5
        )

        assert len(results) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
