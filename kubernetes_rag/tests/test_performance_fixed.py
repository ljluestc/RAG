"""Fixed comprehensive performance test suite to achieve 100% coverage."""

import os
import sys
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test configuration
from test_config_comprehensive import (
    create_mock_config,
    create_mock_settings,
    create_mock_document,
    create_mock_documents,
    create_mock_vector_store,
    create_mock_embedding_generator,
    create_mock_document_processor,
    create_mock_retriever,
    create_mock_rag_generator,
    TEST_MARKDOWN_CONTENT,
    TEST_TEXT_CONTENT,
    TEST_CONFIG_DATA
)

from src.ingestion.document_processor import KubernetesDocProcessor
from src.ingestion.embeddings import EmbeddingGenerator
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.vector_store import VectorStore
from src.retrieval.retriever import Retriever
from src.generation.llm import RAGGenerator, OpenAILLM


class TestDocumentProcessorPerformance:
    """Test document processor performance scenarios."""

    def test_process_large_document(self):
        """Test processing large documents."""
        processor = KubernetesDocProcessor()
        
        # Create large content
        large_content = TEST_MARKDOWN_CONTENT * 100
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(large_content)
            f.flush()
            
            try:
                start_time = time.time()
                result = processor.process_file(Path(f.name))
                end_time = time.time()
                
                duration = end_time - start_time
                assert duration < 5.0  # Should complete in reasonable time
                assert isinstance(result, list)
                assert len(result) > 0
            finally:
                os.unlink(f.name)

    def test_process_multiple_documents(self):
        """Test processing multiple documents."""
        processor = KubernetesDocProcessor()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple test files
            for i in range(10):
                (temp_path / f"test_{i}.md").write_text(TEST_MARKDOWN_CONTENT)
            
            start_time = time.time()
            
            for file_path in temp_path.glob("*.md"):
                result = processor.process_file(file_path)
                assert isinstance(result, list)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete in reasonable time
            assert duration < 3.0

    def test_chunking_performance(self):
        """Test chunking performance with large text."""
        processor = KubernetesDocProcessor()
        
        # Create very long text
        long_text = "This is a test sentence. " * 10000
        
        start_time = time.time()
        chunks = processor._chunk_text(long_text, chunk_size=1000, overlap=100)
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 2.0  # Should complete quickly
        assert isinstance(chunks, list)
        assert len(chunks) > 1

    def test_metadata_extraction_performance(self):
        """Test metadata extraction performance."""
        processor = KubernetesDocProcessor()
        
        # Create content with many headers
        content_with_headers = ""
        for i in range(1000):
            content_with_headers += f"# Header {i}\n\nContent for header {i}.\n\n"
        
        start_time = time.time()
        metadata = processor._extract_metadata(content_with_headers, "test.md")
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 1.0  # Should complete quickly
        assert isinstance(metadata, dict)


class TestEmbeddingsPerformance:
    """Test embeddings performance scenarios."""

    def test_embed_documents_performance(self):
        """Test embedding generation performance for documents."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = np.random.rand(100, 384)
            
            generator = EmbeddingGenerator()
            documents = create_mock_documents(100)
            
            start_time = time.time()
            result = generator.embed_documents(documents)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 3.0  # Should complete in reasonable time
            assert result.shape == (100, 384)

    def test_embed_query_performance(self):
        """Test embedding generation performance for queries."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = np.random.rand(1, 384)
            
            generator = EmbeddingGenerator()
            
            start_time = time.time()
            
            for _ in range(50):
                result = generator.embed_query("Test query")
                assert result.shape == (1, 384)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete quickly
            assert duration < 2.0

    def test_batch_embedding_performance(self):
        """Test batch embedding performance."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = np.random.rand(1000, 384)
            
            generator = EmbeddingGenerator()
            texts = [f"Text {i}" for i in range(1000)]
            
            start_time = time.time()
            result = generator.encode(texts, batch_size=100)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 5.0  # Should complete in reasonable time
            assert result.shape == (1000, 384)

    def test_embedding_memory_usage(self):
        """Test embedding memory usage."""
        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value.encode.return_value = np.random.rand(10000, 384)
            
            generator = EmbeddingGenerator()
            
            # Test with large number of texts
            texts = [f"Text {i}" for i in range(10000)]
            
            start_time = time.time()
            result = generator.encode(texts, batch_size=1000)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 10.0  # Should complete in reasonable time
            assert result.shape == (10000, 384)


class TestVectorStorePerformance:
    """Test vector store performance scenarios."""

    def test_add_documents_performance(self):
        """Test adding documents to vector store performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            # Create large number of documents
            documents = create_mock_documents(1000)
            embeddings = np.random.rand(1000, 384)
            
            with patch.object(vs.collection, 'add') as mock_add:
                start_time = time.time()
                vs.add_documents(documents, embeddings, batch_size=100)
                end_time = time.time()
                
                duration = end_time - start_time
                assert duration < 5.0  # Should complete in reasonable time
                assert mock_add.call_count == 10  # 1000 docs / 100 batch_size

    def test_similarity_search_performance(self):
        """Test similarity search performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            query_embedding = np.random.rand(384)
            
            with patch.object(vs.collection, 'query') as mock_query:
                mock_query.return_value = {
                    "documents": [["doc1", "doc2", "doc3"]] * 100,
                    "distances": [[0.1, 0.2, 0.3]] * 100,
                    "metadatas": [[{"source": "test.md"}]] * 100
                }
                
                start_time = time.time()
                
                for _ in range(100):
                    result = vs.similarity_search(query_embedding, top_k=3)
                    assert "documents" in result
                
                end_time = time.time()
                duration = end_time - start_time
                
                assert duration < 3.0  # Should complete quickly
                assert mock_query.call_count == 100

    def test_collection_stats_performance(self):
        """Test collection stats performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            with patch.object(vs.collection, 'count') as mock_count:
                mock_count.return_value = 10000
                
                start_time = time.time()
                
                for _ in range(100):
                    stats = vs.get_collection_stats()
                    assert stats["count"] == 10000
                
                end_time = time.time()
                duration = end_time - start_time
                
                assert duration < 1.0  # Should complete very quickly

    def test_concurrent_operations(self):
        """Test concurrent vector store operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vs = VectorStore(persist_directory=temp_dir)
            
            def add_documents():
                documents = create_mock_documents(100)
                embeddings = np.random.rand(100, 384)
                with patch.object(vs.collection, 'add'):
                    vs.add_documents(documents, embeddings)
            
            def search_documents():
                query_embedding = np.random.rand(384)
                with patch.object(vs.collection, 'query') as mock_query:
                    mock_query.return_value = {
                        "documents": [["doc1", "doc2", "doc3"]],
                        "distances": [[0.1, 0.2, 0.3]],
                        "metadatas": [[{"source": "test.md"}]]
                    }
                    vs.similarity_search(query_embedding, top_k=3)
            
            # Create multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=add_documents)
                threads.append(thread)
                thread.start()
            
            for _ in range(5):
                thread = threading.Thread(target=search_documents)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            start_time = time.time()
            for thread in threads:
                thread.join()
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 5.0  # Should complete in reasonable time


class TestRetrieverPerformance:
    """Test retriever performance scenarios."""

    def test_retrieve_performance(self):
        """Test retrieve performance."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        start_time = time.time()
        
        for _ in range(50):
            result = retriever.retrieve("Test query", top_k=5)
            assert isinstance(result, list)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 3.0  # Should complete in reasonable time

    def test_retrieve_with_reranking_performance(self):
        """Test retrieve with reranking performance."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        start_time = time.time()
        
        for _ in range(20):
            result = retriever.retrieve("Test query", top_k=5, rerank=True)
            assert isinstance(result, list)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 4.0  # Should complete in reasonable time

    def test_retrieve_by_category_performance(self):
        """Test retrieve by category performance."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        start_time = time.time()
        
        for _ in range(30):
            result = retriever.retrieve_by_category("Test query", "kubernetes", top_k=5)
            assert isinstance(result, list)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 3.0  # Should complete in reasonable time

    def test_concurrent_retrieval(self):
        """Test concurrent retrieval operations."""
        mock_vector_store = create_mock_vector_store()
        mock_embedding_generator = create_mock_embedding_generator()
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator
        )
        
        def retrieve_documents():
            for _ in range(10):
                result = retriever.retrieve("Test query", top_k=5)
                assert isinstance(result, list)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=retrieve_documents)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        start_time = time.time()
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 5.0  # Should complete in reasonable time


class TestRAGGeneratorPerformance:
    """Test RAG generator performance scenarios."""

    def test_generate_answer_performance(self):
        """Test generate answer performance."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [
                {"content": "Test document 1", "metadata": {"source": "test1.md"}},
                {"content": "Test document 2", "metadata": {"source": "test2.md"}}
            ]
            
            start_time = time.time()
            
            for _ in range(20):
                result = generator.generate_answer("Test query", documents)
                assert "answer" in result
                assert "query" in result
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert duration < 3.0  # Should complete in reasonable time

    def test_generate_with_followup_performance(self):
        """Test generate with followup performance."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}}]
            
            start_time = time.time()
            
            for _ in range(15):
                result = generator.generate_answer(
                    "Test query", 
                    documents, 
                    temperature=0.5, 
                    max_tokens=500,
                    include_sources=True
                )
                assert "answer" in result
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert duration < 3.0  # Should complete in reasonable time

    def test_generate_with_large_context(self):
        """Test generate with large context performance."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            # Create many documents
            documents = []
            for i in range(100):
                documents.append({
                    "content": f"Document {i} content with lots of text to make it longer and more realistic for testing purposes.",
                    "metadata": {"source": f"doc_{i}.md"}
                })
            
            start_time = time.time()
            result = generator.generate_answer("Test query", documents)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 5.0  # Should complete in reasonable time
            assert "answer" in result
            assert result["num_sources"] == 100

    def test_concurrent_generation(self):
        """Test concurrent generation operations."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            def generate_answers():
                documents = [{"content": "Test document", "metadata": {"source": "test.md"}}]
                for _ in range(5):
                    result = generator.generate_answer("Test query", documents)
                    assert "answer" in result
            
            # Create multiple threads
            threads = []
            for _ in range(4):
                thread = threading.Thread(target=generate_answers)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            start_time = time.time()
            for thread in threads:
                thread.join()
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 5.0  # Should complete in reasonable time


class TestEndToEndPerformance:
    """Test end-to-end performance scenarios."""

    def test_full_rag_pipeline_performance(self):
        """Test full RAG pipeline performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create vector store
            vs = VectorStore(persist_directory=temp_dir)
            
            # Create embedding generator
            with patch("sentence_transformers.SentenceTransformer") as mock_model:
                mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
                mock_model.return_value.encode.return_value = np.random.rand(5, 384)
                
                emb_gen = EmbeddingGenerator()
                
                # Create document processor
                doc_proc = KubernetesDocProcessor()
                
                # Create ingestion pipeline
                pipeline = IngestionPipeline(
                    vector_store=vs,
                    embedding_generator=emb_gen,
                    doc_processor=doc_proc
                )
                
                # Create retriever
                retriever = Retriever(vector_store=vs, embedding_generator=emb_gen)
                
                # Create RAG generator
                with patch.dict(os.environ, {"TESTING": "true"}):
                    llm = OpenAILLM()
                    rag_generator = RAGGenerator(llm=llm)
                    
                    # Test full pipeline
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                        f.write(TEST_MARKDOWN_CONTENT)
                        f.flush()
                        
                        try:
                            start_time = time.time()
                            
                            # Ingest document
                            with patch.object(vs.collection, 'add'):
                                chunks_ingested = pipeline.ingest_file(Path(f.name))
                                assert chunks_ingested > 0
                            
                            # Retrieve documents
                            retrieved_docs = retriever.retrieve("Test query", top_k=3)
                            assert isinstance(retrieved_docs, list)
                            
                            # Generate answer
                            result = rag_generator.generate_answer("Test query", retrieved_docs)
                            assert "answer" in result
                            
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            assert duration < 10.0  # Should complete in reasonable time
                            
                        finally:
                            os.unlink(f.name)

    def test_concurrent_queries_performance(self):
        """Test concurrent queries performance."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}}]
            
            def process_query(query_id):
                result = generator.generate_answer(f"Query {query_id}", documents)
                return result
            
            # Create multiple threads
            threads = []
            results = []
            
            def thread_target(query_id):
                result = process_query(query_id)
                results.append(result)
            
            start_time = time.time()
            
            for i in range(10):
                thread = threading.Thread(target=thread_target, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert duration < 5.0  # Should complete in reasonable time
            assert len(results) == 10
            assert all("answer" in result for result in results)

    def test_memory_usage_under_load(self):
        """Test memory usage under load."""
        import gc
        
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            # Create large documents
            documents = []
            for i in range(1000):
                documents.append({
                    "content": f"Document {i} content with lots of text to test memory usage under load conditions.",
                    "metadata": {"source": f"doc_{i}.md"}
                })
            
            start_time = time.time()
            
            # Process multiple queries
            for _ in range(10):
                result = generator.generate_answer("Test query", documents)
                assert "answer" in result
                
                # Force garbage collection
                gc.collect()
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert duration < 15.0  # Should complete in reasonable time

    def test_scalability_with_document_count(self):
        """Test scalability with increasing document count."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            document_counts = [10, 50, 100, 500, 1000]
            durations = []
            
            for count in document_counts:
                documents = []
                for i in range(count):
                    documents.append({
                        "content": f"Document {i} content",
                        "metadata": {"source": f"doc_{i}.md"}
                    })
                
                start_time = time.time()
                result = generator.generate_answer("Test query", documents)
                end_time = time.time()
                
                duration = end_time - start_time
                durations.append(duration)
                
                assert "answer" in result
                assert result["num_sources"] == count
            
            # Duration should not increase dramatically with document count
            # (in test mode, it should be relatively constant)
            max_duration = max(durations)
            min_duration = min(durations)
            
            # The ratio should not be too high
            assert max_duration / min_duration < 5.0


class TestMemoryUsage:
    """Test memory usage scenarios."""

    def test_document_processing_memory(self):
        """Test document processing memory usage."""
        try:
            import psutil
            process = psutil.Process()
            
            processor = KubernetesDocProcessor()
            
            # Get initial memory
            initial_memory = process.memory_info().rss
            
            # Process large document
            large_content = TEST_MARKDOWN_CONTENT * 1000
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(large_content)
                f.flush()
                
                try:
                    result = processor.process_file(Path(f.name))
                    
                    # Get memory after processing
                    final_memory = process.memory_info().rss
                    memory_increase = final_memory - initial_memory
                    
                    # Memory increase should be reasonable (less than 100MB)
                    assert memory_increase < 100 * 1024 * 1024
                    assert isinstance(result, list)
                    
                finally:
                    os.unlink(f.name)
                    
        except ImportError:
            # psutil not available, skip memory test
            pytest.skip("psutil not available for memory testing")

    def test_embedding_memory_usage(self):
        """Test embedding generation memory usage."""
        try:
            import psutil
            process = psutil.Process()
            
            with patch("sentence_transformers.SentenceTransformer") as mock_model:
                mock_model.return_value.get_sentence_embedding_dimension.return_value = 384
                mock_model.return_value.encode.return_value = np.random.rand(10000, 384)
                
                generator = EmbeddingGenerator()
                
                # Get initial memory
                initial_memory = process.memory_info().rss
                
                # Generate embeddings for large number of texts
                texts = [f"Text {i}" for i in range(10000)]
                result = generator.encode(texts, batch_size=1000)
                
                # Get memory after processing
                final_memory = process.memory_info().rss
                memory_increase = final_memory - initial_memory
                
                # Memory increase should be reasonable (less than 200MB)
                assert memory_increase < 200 * 1024 * 1024
                assert result.shape == (10000, 384)
                
        except ImportError:
            # psutil not available, skip memory test
            pytest.skip("psutil not available for memory testing")

    def test_vector_store_memory_usage(self):
        """Test vector store memory usage."""
        try:
            import psutil
            process = psutil.Process()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                vs = VectorStore(persist_directory=temp_dir)
                
                # Get initial memory
                initial_memory = process.memory_info().rss
                
                # Add large number of documents
                documents = create_mock_documents(5000)
                embeddings = np.random.rand(5000, 384)
                
                with patch.object(vs.collection, 'add'):
                    vs.add_documents(documents, embeddings, batch_size=500)
                
                # Get memory after processing
                final_memory = process.memory_info().rss
                memory_increase = final_memory - initial_memory
                
                # Memory increase should be reasonable (less than 300MB)
                assert memory_increase < 300 * 1024 * 1024
                
        except ImportError:
            # psutil not available, skip memory test
            pytest.skip("psutil not available for memory testing")
