"""Comprehensive performance tests for Kubernetes RAG system."""

import os
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import statistics
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up test environment
os.environ.update({
    "OPENAI_API_KEY": "test-key-12345",
    "ANTHROPIC_API_KEY": "test-key-12345",
    "PERPLEXITY_API_KEY": "test-key-12345",
    "GOOGLE_API_KEY": "test-key-12345",
    "MISTRAL_API_KEY": "test-key-12345",
    "XAI_API_KEY": "test-key-12345",
    "OPENROUTER_API_KEY": "test-key-12345",
    "AZURE_OPENAI_API_KEY": "test-key-12345",
    "OLLAMA_API_KEY": "test-key-12345",
    "TESTING": "true",
    "LOG_LEVEL": "DEBUG"
})

from src.generation.llm import OpenAILLM, AnthropicLLM, RAGGenerator
from src.ingestion.document_processor import DocumentProcessor
from src.ingestion.embeddings import EmbeddingsManager
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore


class PerformanceMetrics:
    """Class to collect and analyze performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def add_metric(self, name: str, value: float):
        """Add a performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = self.metrics[name]
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics."""
        return {name: self.get_stats(name) for name in self.metrics}


@pytest.mark.slow
class TestDocumentProcessorPerformance:
    """Test document processor performance."""
    
    def test_process_large_document(self):
        """Test processing large documents."""
        processor = DocumentProcessor()
        metrics = PerformanceMetrics()
        
        # Create a large document
        large_content = "# Large Document\n\n" + "This is a test paragraph. " * 1000
        
        # Test multiple iterations
        for i in range(10):
            start_time = time.time()
            result = processor.process_markdown(large_content, f"large_doc_{i}.md")
            end_time = time.time()
            
            duration = end_time - start_time
            metrics.add_metric("large_document_processing", duration)
            
            assert len(result) > 0
        
        stats = metrics.get_stats("large_document_processing")
        assert stats["mean"] < 1.0  # Should process in less than 1 second
        print(f"Large document processing: {stats}")
    
    def test_process_multiple_documents(self):
        """Test processing multiple documents."""
        processor = DocumentProcessor()
        metrics = PerformanceMetrics()
        
        # Create multiple documents
        documents = []
        for i in range(100):
            content = f"# Document {i}\n\nThis is document {i} with some content."
            documents.append((content, f"doc_{i}.md"))
        
        # Test processing all documents
        start_time = time.time()
        all_results = []
        for content, filename in documents:
            result = processor.process_markdown(content, filename)
            all_results.extend(result)
        end_time = time.time()
        
        duration = end_time - start_time
        metrics.add_metric("multiple_documents_processing", duration)
        
        assert len(all_results) > 0
        stats = metrics.get_stats("multiple_documents_processing")
        assert stats["mean"] < 5.0  # Should process 100 documents in less than 5 seconds
        print(f"Multiple documents processing: {stats}")
    
    def test_chunking_performance(self):
        """Test text chunking performance."""
        processor = DocumentProcessor()
        metrics = PerformanceMetrics()
        
        # Create very long text
        long_text = "This is a test sentence. " * 10000
        
        # Test different chunk sizes
        chunk_sizes = [100, 500, 1000, 2000]
        
        for chunk_size in chunk_sizes:
            start_time = time.time()
            chunks = processor._chunk_text(long_text, chunk_size=chunk_size, overlap=50)
            end_time = time.time()
            
            duration = end_time - start_time
            metrics.add_metric(f"chunking_{chunk_size}", duration)
            
            assert len(chunks) > 0
        
        # All chunking operations should be fast
        for chunk_size in chunk_sizes:
            stats = metrics.get_stats(f"chunking_{chunk_size}")
            assert stats["mean"] < 0.1  # Should chunk in less than 0.1 seconds
            print(f"Chunking {chunk_size}: {stats}")


@pytest.mark.slow
class TestEmbeddingsPerformance:
    """Test embeddings performance."""
    
    def test_embed_documents_performance(self):
        """Test embedding multiple documents."""
        metrics = PerformanceMetrics()
        
        with patch('sentence_transformers.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3] for _ in range(100)]
            mock_st.return_value = mock_model
            
            manager = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
            
            # Test different batch sizes
            batch_sizes = [10, 50, 100, 200]
            
            for batch_size in batch_sizes:
                documents = [f"Document {i}" for i in range(batch_size)]
                
                start_time = time.time()
                embeddings = manager.embed_documents(documents)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric(f"embed_documents_{batch_size}", duration)
                
                assert len(embeddings) == batch_size
            
            # All embedding operations should be reasonably fast
            for batch_size in batch_sizes:
                stats = metrics.get_stats(f"embed_documents_{batch_size}")
                assert stats["mean"] < 2.0  # Should embed in less than 2 seconds
                print(f"Embed documents {batch_size}: {stats}")
    
    def test_embed_query_performance(self):
        """Test embedding query performance."""
        metrics = PerformanceMetrics()
        
        with patch('sentence_transformers.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_st.return_value = mock_model
            
            manager = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
            
            # Test multiple queries
            queries = [f"Query {i}" for i in range(100)]
            
            for query in queries:
                start_time = time.time()
                embedding = manager.embed_query(query)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric("embed_query", duration)
                
                assert len(embedding) == 3
            
            stats = metrics.get_stats("embed_query")
            assert stats["mean"] < 0.01  # Should embed query in less than 0.01 seconds
            print(f"Embed query: {stats}")


@pytest.mark.slow
class TestVectorStorePerformance:
    """Test vector store performance."""
    
    def test_add_documents_performance(self):
        """Test adding documents to vector store."""
        metrics = PerformanceMetrics()
        
        with patch('chromadb.Client') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_collection.add.return_value = None
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance
            
            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")
            
            # Test different document counts
            doc_counts = [10, 50, 100, 500]
            
            for doc_count in doc_counts:
                documents = [
                    {"content": f"Document {i}", "metadata": {"source": f"doc_{i}.md"}}
                    for i in range(doc_count)
                ]
                embeddings = [[0.1, 0.2, 0.3] for _ in range(doc_count)]
                
                start_time = time.time()
                result = vs.add_documents(documents, embeddings)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric(f"add_documents_{doc_count}", duration)
                
                assert result is not None
            
            # All operations should be reasonably fast
            for doc_count in doc_counts:
                stats = metrics.get_stats(f"add_documents_{doc_count}")
                assert stats["mean"] < 1.0  # Should add documents in less than 1 second
                print(f"Add documents {doc_count}: {stats}")
    
    def test_similarity_search_performance(self):
        """Test similarity search performance."""
        metrics = PerformanceMetrics()
        
        with patch('chromadb.Client') as mock_client:
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_result = Mock()
            mock_result['documents'] = [["doc1", "doc2", "doc3", "doc4", "doc5"]]
            mock_result['metadatas'] = [[{"source": f"test{i}.md"} for i in range(5)]]
            mock_result['distances'] = [[0.1, 0.2, 0.3, 0.4, 0.5]]
            mock_collection.query.return_value = mock_result
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance
            
            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")
            
            # Test multiple searches
            queries = [[0.1, 0.2, 0.3] for _ in range(100)]
            
            for query in queries:
                start_time = time.time()
                results = vs.similarity_search(query, top_k=5)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric("similarity_search", duration)
                
                assert len(results) == 5
            
            stats = metrics.get_stats("similarity_search")
            assert stats["mean"] < 0.1  # Should search in less than 0.1 seconds
            print(f"Similarity search: {stats}")


@pytest.mark.slow
class TestRetrieverPerformance:
    """Test retriever performance."""
    
    def test_retrieve_performance(self):
        """Test retrieval performance."""
        metrics = PerformanceMetrics()
        
        with patch('sentence_transformers.SentenceTransformer') as mock_st, \
             patch('chromadb.Client') as mock_client:
            
            # Setup mocks
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_st.return_value = mock_model
            
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_result = Mock()
            mock_result['documents'] = [["doc1", "doc2", "doc3", "doc4", "doc5"]]
            mock_result['metadatas'] = [[{"source": f"test{i}.md"} for i in range(5)]]
            mock_result['distances'] = [[0.1, 0.2, 0.3, 0.4, 0.5]]
            mock_collection.query.return_value = mock_result
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance
            
            # Create retriever
            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")
            embeddings = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
            retriever = Retriever(vector_store=vs, embeddings=embeddings)
            
            # Test multiple retrievals
            queries = [f"Query {i}" for i in range(100)]
            
            for query in queries:
                start_time = time.time()
                results = retriever.retrieve(query, top_k=5)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric("retrieve", duration)
                
                assert len(results) == 5
            
            stats = metrics.get_stats("retrieve")
            assert stats["mean"] < 0.5  # Should retrieve in less than 0.5 seconds
            print(f"Retrieve: {stats}")
    
    def test_retrieve_with_reranking_performance(self):
        """Test retrieval with reranking performance."""
        metrics = PerformanceMetrics()
        
        with patch('sentence_transformers.SentenceTransformer') as mock_st, \
             patch('chromadb.Client') as mock_client, \
             patch('src.retrieval.retriever.CrossEncoder') as mock_cross_encoder:
            
            # Setup mocks
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_st.return_value = mock_model
            
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_result = Mock()
            mock_result['documents'] = [["doc1", "doc2", "doc3", "doc4", "doc5"]]
            mock_result['metadatas'] = [[{"source": f"test{i}.md"} for i in range(5)]]
            mock_result['distances'] = [[0.1, 0.2, 0.3, 0.4, 0.5]]
            mock_collection.query.return_value = mock_result
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance
            
            mock_cross_encoder_model = Mock()
            mock_cross_encoder_model.predict.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]
            mock_cross_encoder.return_value = mock_cross_encoder_model
            
            # Create retriever with reranking
            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")
            embeddings = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
            retriever = Retriever(vector_store=vs, embeddings=embeddings)
            retriever.use_reranking = True
            
            # Test multiple retrievals
            queries = [f"Query {i}" for i in range(50)]  # Fewer queries due to reranking overhead
            
            for query in queries:
                start_time = time.time()
                results = retriever.retrieve(query, top_k=5)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric("retrieve_reranking", duration)
                
                assert len(results) == 5
            
            stats = metrics.get_stats("retrieve_reranking")
            assert stats["mean"] < 1.0  # Should retrieve with reranking in less than 1 second
            print(f"Retrieve with reranking: {stats}")


@pytest.mark.slow
class TestRAGGeneratorPerformance:
    """Test RAG generator performance."""
    
    def test_generate_answer_performance(self):
        """Test answer generation performance."""
        metrics = PerformanceMetrics()
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test answer"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            llm = OpenAILLM(model="gpt-3.5-turbo")
            
            # Create mock retriever
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = [
                {"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}
            ]
            
            generator = RAGGenerator(llm=llm, retriever=mock_retriever)
            
            # Test multiple generations
            queries = [f"Query {i}" for i in range(50)]
            
            for query in queries:
                documents = [
                    {"content": f"Document {i}", "metadata": {"source": f"doc_{i}.md"}}
                ]
                
                start_time = time.time()
                result = generator.generate_answer(query, documents)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric("generate_answer", duration)
                
                assert "answer" in result
            
            stats = metrics.get_stats("generate_answer")
            assert stats["mean"] < 2.0  # Should generate answer in less than 2 seconds
            print(f"Generate answer: {stats}")
    
    def test_generate_with_followup_performance(self):
        """Test answer generation with followup performance."""
        metrics = PerformanceMetrics()
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test answer with followup"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            llm = OpenAILLM(model="gpt-3.5-turbo")
            
            # Create mock retriever
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = [
                {"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}
            ]
            
            generator = RAGGenerator(llm=llm, retriever=mock_retriever)
            
            # Test multiple generations with conversation history
            queries = [f"Query {i}" for i in range(30)]  # Fewer queries due to complexity
            conversation_history = []
            
            for query in queries:
                documents = [
                    {"content": f"Document {i}", "metadata": {"source": f"doc_{i}.md"}}
                ]
                
                start_time = time.time()
                result = generator.generate_with_followup(query, documents, conversation_history)
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric("generate_with_followup", duration)
                
                assert "answer" in result
                assert "conversation_history" in result
                
                # Update conversation history
                conversation_history = result["conversation_history"]
            
            stats = metrics.get_stats("generate_with_followup")
            assert stats["mean"] < 3.0  # Should generate with followup in less than 3 seconds
            print(f"Generate with followup: {stats}")


@pytest.mark.slow
class TestEndToEndPerformance:
    """Test end-to-end performance."""
    
    def test_full_rag_pipeline_performance(self):
        """Test full RAG pipeline performance."""
        metrics = PerformanceMetrics()
        
        with patch('sentence_transformers.SentenceTransformer') as mock_st, \
             patch('chromadb.Client') as mock_client, \
             patch('openai.OpenAI') as mock_openai:
            
            # Setup all mocks
            mock_embeddings_model = Mock()
            mock_embeddings_model.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_st.return_value = mock_embeddings_model
            
            mock_client_instance = Mock()
            mock_collection = Mock()
            mock_result = Mock()
            mock_result['documents'] = [["doc1", "doc2", "doc3"]]
            mock_result['metadatas'] = [[{"source": f"test{i}.md"} for i in range(3)]]
            mock_result['distances'] = [[0.1, 0.2, 0.3]]
            mock_collection.query.return_value = mock_result
            mock_collection.add.return_value = None
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance
            
            mock_openai_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test answer"
            mock_openai_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_openai_client
            
            # Create components
            vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")
            embeddings = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
            retriever = Retriever(vector_store=vs, embeddings=embeddings)
            llm = OpenAILLM(model="gpt-3.5-turbo")
            generator = RAGGenerator(llm=llm, retriever=retriever)
            
            # Test full pipeline
            queries = [f"Query {i}" for i in range(20)]
            
            for query in queries:
                start_time = time.time()
                
                # Retrieve documents
                results = retriever.retrieve(query, top_k=3)
                
                # Generate answer
                answer_data = generator.generate_answer(query, results)
                
                end_time = time.time()
                
                duration = end_time - start_time
                metrics.add_metric("full_pipeline", duration)
                
                assert "answer" in answer_data
                assert len(results) == 3
            
            stats = metrics.get_stats("full_pipeline")
            assert stats["mean"] < 3.0  # Should complete full pipeline in less than 3 seconds
            print(f"Full pipeline: {stats}")
    
    def test_concurrent_queries_performance(self):
        """Test concurrent queries performance."""
        import threading
        import queue
        
        metrics = PerformanceMetrics()
        results_queue = queue.Queue()
        
        def process_query(query_id: int):
            """Process a single query."""
            with patch('sentence_transformers.SentenceTransformer') as mock_st, \
                 patch('chromadb.Client') as mock_client, \
                 patch('openai.OpenAI') as mock_openai:
                
                # Setup mocks (same as above)
                mock_embeddings_model = Mock()
                mock_embeddings_model.encode.return_value = [[0.1, 0.2, 0.3]]
                mock_st.return_value = mock_embeddings_model
                
                mock_client_instance = Mock()
                mock_collection = Mock()
                mock_result = Mock()
                mock_result['documents'] = [["doc1", "doc2", "doc3"]]
                mock_result['metadatas'] = [[{"source": f"test{i}.md"} for i in range(3)]]
                mock_result['distances'] = [[0.1, 0.2, 0.3]]
                mock_collection.query.return_value = mock_result
                mock_client_instance.get_or_create_collection.return_value = mock_collection
                mock_client.return_value = mock_client_instance
                
                mock_openai_client = Mock()
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = f"Answer for query {query_id}"
                mock_openai_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_openai_client
                
                # Create components
                vs = VectorStore(collection_name="test_collection", persist_directory="/tmp/test")
                embeddings = EmbeddingsManager(provider="sentence_transformers", model="all-MiniLM-L6-v2")
                retriever = Retriever(vector_store=vs, embeddings=embeddings)
                llm = OpenAILLM(model="gpt-3.5-turbo")
                generator = RAGGenerator(llm=llm, retriever=retriever)
                
                # Process query
                start_time = time.time()
                query = f"Query {query_id}"
                results = retriever.retrieve(query, top_k=3)
                answer_data = generator.generate_answer(query, results)
                end_time = time.time()
                
                duration = end_time - start_time
                results_queue.put((query_id, duration, answer_data))
        
        # Test concurrent processing
        num_threads = 10
        threads = []
        
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=process_query, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Collect results
        while not results_queue.empty():
            query_id, duration, answer_data = results_queue.get()
            metrics.add_metric("concurrent_query", duration)
            assert "answer" in answer_data
        
        stats = metrics.get_stats("concurrent_query")
        assert stats["count"] == num_threads
        assert total_duration < 10.0  # All queries should complete in less than 10 seconds
        print(f"Concurrent queries ({num_threads}): {stats}")
        print(f"Total duration: {total_duration:.2f} seconds")


@pytest.mark.slow
class TestMemoryUsage:
    """Test memory usage patterns."""
    
    def test_document_processing_memory(self):
        """Test memory usage during document processing."""
        import psutil
        import gc
        
        processor = DocumentProcessor()
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process many documents
        for i in range(100):
            content = f"# Document {i}\n\n" + "Content " * 1000
            result = processor.process_markdown(content, f"doc_{i}.md")
            
            # Check memory every 10 documents
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory increase should be reasonable (less than 100MB)
                assert memory_increase < 100, f"Memory increase too high: {memory_increase}MB"
        
        # Force garbage collection
        gc.collect()
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        print(f"Memory usage - Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB, Increase: {total_memory_increase:.2f}MB")
        
        # Total memory increase should be reasonable
        assert total_memory_increase < 200, f"Total memory increase too high: {total_memory_increase}MB"


