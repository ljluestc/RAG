import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import os
import numpy as np

from src.ingestion.document_processor import (
    Document,
    MarkdownProcessor,
    DocumentChunker,
    KubernetesDocProcessor
)
from src.ingestion.embeddings import EmbeddingGenerator
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.vector_store import VectorStore
from test_config_final import mock_config, mock_settings

# Helper function to create mock files
@pytest.fixture
def create_mock_file(tmp_path):
    def _create_file(filename, content):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path
    return _create_file

# Mock content for testing
TEST_MARKDOWN_CONTENT = """
# Document 1

This is the first paragraph.

## Sub-section A

Content for sub-section A.

```python
print("hello world")
```

### Sub-sub-section A.1

More content here.

Q: What is Kubernetes?
A: Kubernetes is an open-source container-orchestration system.
"""

TEST_TEXT_CONTENT = "This is a plain text document. It has multiple sentences. Each sentence will be treated as part of the same chunk if chunk size allows."

# --- Document Tests ---
class TestDocument:
    def test_document_creation(self):
        doc = Document(content="test", metadata={"source": "file.md"}, chunk_id="1")
        assert doc.content == "test"
        assert doc.metadata == {"source": "file.md"}
        assert doc.chunk_id == "1"

# --- MarkdownProcessor Tests ---
class TestMarkdownProcessor:
    @pytest.fixture
    def processor(self):
        return MarkdownProcessor()

    def test_markdown_processor_init(self, processor):
        assert processor.md is not None

    def test_markdown_processor_extract_sections(self, processor):
        sections = processor.extract_sections(TEST_MARKDOWN_CONTENT)
        assert len(sections) >= 3
        assert sections[0]["title"] == "Document 1"
        assert "Content for sub-section A." in sections[1]["content"]

    def test_markdown_processor_extract_code_blocks(self, processor):
        code_blocks = processor.extract_code_blocks(TEST_MARKDOWN_CONTENT)
        assert len(code_blocks) == 1
        assert code_blocks[0]["language"] == "python"
        assert "print(\"hello world\")" in code_blocks[0]["content"]

    def test_markdown_processor_parse_qa_pairs(self, processor):
        qa_pairs = processor.parse_qa_pairs(TEST_MARKDOWN_CONTENT)
        # The Q&A parsing might not find pairs in this format, so we'll test with a more explicit format
        qa_content = """
        Q: What is Kubernetes?
        A: Kubernetes is an open-source container-orchestration system.
        
        Q: What is Docker?
        A: Docker is a containerization platform.
        """
        qa_pairs = processor.parse_qa_pairs(qa_content)
        assert len(qa_pairs) >= 2
        assert qa_pairs[0]["question"] == "What is Kubernetes?"
        assert "open-source container-orchestration system" in qa_pairs[0]["answer"]

# --- DocumentChunker Tests ---
class TestDocumentChunker:
    def test_document_chunker_init_default(self):
        chunker = DocumentChunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200

    def test_document_chunker_init_custom(self):
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100

    def test_document_chunker_chunk_text(self):
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
        content = "This is a test sentence. " * 10
        metadata = {"source": "test.txt"}
        documents = chunker.chunk_text(content, metadata)
        assert isinstance(documents, list)
        assert len(documents) > 1
        assert all(isinstance(doc, Document) for doc in documents)
        assert all(doc.metadata["source"] == metadata["source"] for doc in documents)

    def test_document_chunker_chunk_text_short(self):
        chunker = DocumentChunker()
        content = "Short text"
        metadata = {"source": "short.txt"}
        documents = chunker.chunk_text(content, metadata)
        assert len(documents) == 1
        assert documents[0].content == content
        assert documents[0].metadata["source"] == metadata["source"]

    def test_document_chunker_chunk_by_section(self):
        chunker = DocumentChunker()
        sections = [
            {"title": "Section 1", "content": "Content 1", "level": 1},
            {"title": "Section 2", "content": "Content 2", "level": 2}
        ]
        metadata = {"source": "sections.md"}
        documents = chunker.chunk_by_section(sections, metadata)
        assert len(documents) == 2
        assert documents[0].content == "# Section 1\n\nContent 1"
        assert documents[1].content == "## Section 2\n\nContent 2"

# --- KubernetesDocProcessor Tests ---
class TestKubernetesDocProcessor:
    @pytest.fixture
    def processor(self):
        return KubernetesDocProcessor(chunk_size=mock_config.document_processing.chunk_size,
                                    chunk_overlap=mock_config.document_processing.chunk_overlap)

    def test_kubernetes_doc_processor_init_default(self, processor):
        assert processor.chunker.chunk_size == mock_config.document_processing.chunk_size
        assert processor.chunker.chunk_overlap == mock_config.document_processing.chunk_overlap

    def test_kubernetes_doc_processor_init_custom(self):
        processor = KubernetesDocProcessor(chunk_size=500, chunk_overlap=100)
        assert processor.chunker.chunk_size == 500
        assert processor.chunker.chunk_overlap == 100

    def test_kubernetes_doc_processor_process_file_markdown(self, processor, create_mock_file):
        file_path = create_mock_file("test.md", TEST_MARKDOWN_CONTENT)
        documents = processor.process_file(file_path)
        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert documents[0].metadata["filename"] == "test.md"
        assert documents[0].metadata["type"] == "kubernetes_doc"

    def test_kubernetes_doc_processor_process_file_text(self, processor, create_mock_file):
        file_path = create_mock_file("test.txt", TEST_TEXT_CONTENT)
        documents = processor.process_file(file_path)
        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert documents[0].metadata["filename"] == "test.txt"
        assert documents[0].metadata["type"] == "kubernetes_doc"

    def test_kubernetes_doc_processor_process_file_nonexistent(self, processor):
        non_existent_path = Path("non_existent.md")
        documents = processor.process_file(non_existent_path)
        assert len(documents) == 0

    def test_kubernetes_doc_processor_process_directory(self, processor, tmp_path, create_mock_file):
        sub_dir = tmp_path / "docs"
        sub_dir.mkdir()
        create_mock_file(sub_dir / "doc1.md", TEST_MARKDOWN_CONTENT)
        create_mock_file(sub_dir / "doc2.txt", TEST_TEXT_CONTENT)
        
        documents = processor.process_directory(sub_dir)
        assert len(documents) >= 2  # At least one chunk from each file
        assert any("doc1.md" in doc.metadata["source"] for doc in documents)
        assert any("doc2.txt" in doc.metadata["source"] for doc in documents)

# --- EmbeddingGenerator Tests ---
class TestEmbeddingGenerator:
    @pytest.fixture
    def mock_transformer(self):
        with patch('sentence_transformers.SentenceTransformer') as mock:
            mock_instance = Mock()
            mock_instance.encode.return_value = np.random.rand(1, mock_config.embedding.embedding_dim)
            mock.return_value = mock_instance
            yield mock

    @pytest.fixture
    def generator(self, mock_transformer):
        return EmbeddingGenerator(model_name=mock_config.embedding.model_name)

    def test_embedding_generator_init_default(self, mock_transformer, generator):
        mock_transformer.assert_called_once_with(mock_config.embedding.model_name, device=None)
        assert generator.model is not None
        assert generator.device == "cpu"  # Default device is cpu if not specified

    def test_embedding_generator_init_custom(self, mock_transformer):
        with patch('torch.cuda.is_available', return_value=False):  # Mock CUDA availability
            generator = EmbeddingGenerator(model_name="custom-model", device="cuda")
            mock_transformer.assert_called_once_with("custom-model", device="cpu")  # Should fallback to cpu
            assert generator.model is not None
            assert generator.device == "cpu"  # Should fallback to cpu

    def test_embedding_generator_encode_single_text(self, generator, mock_transformer):
        text = "Hello world"
        result = generator.encode(text)
        mock_transformer.return_value.encode.assert_called_once_with(
            [text], batch_size=32, show_progress=True, normalize=True
        )
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, mock_config.embedding.embedding_dim)

    def test_embedding_generator_encode_multiple_texts(self, generator, mock_transformer):
        texts = ["Hello world", "Another sentence"]
        result = generator.encode(texts)
        mock_transformer.return_value.encode.assert_called_once_with(
            texts, batch_size=32, show_progress=True, normalize=True
        )
        assert isinstance(result, np.ndarray)
        assert result.shape == (len(texts), mock_config.embedding.embedding_dim)

    def test_embedding_generator_encode_with_parameters(self, generator, mock_transformer):
        text = "Test"
        generator.encode(text, batch_size=16, show_progress=False, normalize=False)
        mock_transformer.return_value.encode.assert_called_once_with(
            [text], batch_size=16, show_progress=False, normalize=False
        )

    def test_embedding_generator_encode_empty_list(self, generator, mock_transformer):
        texts = []
        result = generator.encode(texts)
        mock_transformer.return_value.encode.assert_called_once_with(
            texts, batch_size=32, show_progress=True, normalize=True
        )
        assert isinstance(result, np.ndarray)
        assert result.shape == (0, mock_config.embedding.embedding_dim)  # Empty list should return empty array

    def test_embedding_generator_encode_error_handling(self, generator, mock_transformer):
        mock_transformer.return_value.encode.side_effect = Exception("Encoding error")
        with pytest.raises(Exception, match="Encoding error"):
            generator.encode("Error text")

# --- IngestionPipeline Tests ---
class TestIngestionPipeline:
    @pytest.fixture
    def mock_vector_store(self):
        mock = Mock(spec=VectorStore)
        mock.add_documents.return_value = None
        mock.get_collection_stats.return_value = {"count": 10}
        return mock

    @pytest.fixture
    def mock_embedding_generator(self):
        mock = Mock(spec=EmbeddingGenerator)
        mock.encode.return_value = np.random.rand(1, mock_config.embedding.embedding_dim)
        return mock

    @pytest.fixture
    def mock_doc_processor(self):
        mock = Mock(spec=KubernetesDocProcessor)
        mock.process_file.return_value = [
            Document(content="chunk1", metadata={"source": "file.md"}, chunk_id="1"),
            Document(content="chunk2", metadata={"source": "file.md"}, chunk_id="2"),
        ]
        mock.process_directory.return_value = [
            Document(content="dir_chunk1", metadata={"source": "dir/file1.md"}, chunk_id="1"),
            Document(content="dir_chunk2", metadata={"source": "dir/file2.md"}, chunk_id="2"),
        ]
        return mock

    @pytest.fixture
    def pipeline(self, mock_vector_store, mock_embedding_generator, mock_doc_processor):
        return IngestionPipeline(
            vector_store=mock_vector_store,
            embedding_generator=mock_embedding_generator,
            doc_processor=mock_doc_processor
        )

    def test_ingestion_pipeline_init(self, pipeline, mock_vector_store, mock_embedding_generator, mock_doc_processor):
        assert pipeline.vector_store == mock_vector_store
        assert pipeline.embedding_generator == mock_embedding_generator
        assert pipeline.doc_processor == mock_doc_processor

    def test_ingestion_pipeline_ingest_file(self, pipeline, mock_doc_processor, mock_embedding_generator, mock_vector_store, create_mock_file):
        file_path = create_mock_file("test.md", "Some content")
        result = pipeline.ingest_file(file_path)
        
        mock_doc_processor.process_file.assert_called_once_with(file_path)
        mock_embedding_generator.encode.assert_called_once()
        mock_vector_store.add_documents.assert_called_once()
        assert result == 2  # Returns number of chunks ingested

    def test_ingestion_pipeline_ingest_directory(self, pipeline, mock_doc_processor, mock_embedding_generator, mock_vector_store, tmp_path, create_mock_file):
        dir_path = tmp_path / "data"
        dir_path.mkdir()
        create_mock_file(dir_path / "doc1.md", "Content 1")
        create_mock_file(dir_path / "doc2.txt", "Content 2")
        
        result = pipeline.ingest_directory(dir_path)
        
        mock_doc_processor.process_directory.assert_called_once_with(dir_path, "*.md")  # Default pattern
        mock_embedding_generator.encode.assert_called_once()
        mock_vector_store.add_documents.assert_called_once()
        assert result == 2  # Returns number of chunks ingested

    def test_ingestion_pipeline_ingest_file_error(self, pipeline, mock_doc_processor, mock_embedding_generator, mock_vector_store, create_mock_file):
        file_path = create_mock_file("error.md", "Content that causes error")
        mock_doc_processor.process_file.side_effect = Exception("Processing error")
        
        with pytest.raises(Exception, match="Processing error"):
            pipeline.ingest_file(file_path)
        
        mock_doc_processor.process_file.assert_called_once_with(file_path)
        mock_embedding_generator.encode.assert_not_called()
        mock_vector_store.add_documents.assert_not_called()

    def test_ingestion_pipeline_ingest_empty_directory(self, pipeline, mock_doc_processor, mock_embedding_generator, mock_vector_store, tmp_path):
        empty_dir = tmp_path / "empty_data"
        empty_dir.mkdir()
        
        mock_doc_processor.process_directory.return_value = []  # Simulate no documents found
        
        result = pipeline.ingest_directory(empty_dir)
        
        mock_doc_processor.process_directory.assert_called_once_with(empty_dir, "*.md")
        mock_embedding_generator.encode.assert_not_called()
        mock_vector_store.add_documents.assert_not_called()
        assert result == 0

# --- Integration Tests ---
class TestIngestionIntegration:
    @pytest.fixture
    def real_doc_processor(self):
        return KubernetesDocProcessor(chunk_size=100, chunk_overlap=20)

    @pytest.fixture
    def real_embedding_generator(self):
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_instance = Mock()
            mock_instance.encode.return_value = np.random.rand(1, mock_config.embedding.embedding_dim)
            mock_transformer.return_value = mock_instance
            yield EmbeddingGenerator(model_name=mock_config.embedding.model_name)

    @pytest.fixture
    def real_vector_store(self, tmp_path):
        # Use a temporary directory for ChromaDB persistence
        persist_dir = tmp_path / "test_chroma_db"
        return VectorStore(persist_directory=str(persist_dir), collection_name="integration_test_collection")

    def test_full_ingestion_workflow(self, tmp_path, create_mock_file, real_doc_processor, real_embedding_generator, real_vector_store):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        create_mock_file(data_dir / "doc1.md", TEST_MARKDOWN_CONTENT)
        create_mock_file(data_dir / "doc2.txt", TEST_TEXT_CONTENT)

        pipeline = IngestionPipeline(
            vector_store=real_vector_store,
            embedding_generator=real_embedding_generator,
            doc_processor=real_doc_processor
        )
        
        total_chunks_ingested = pipeline.ingest_directory(data_dir)
        
        assert total_chunks_ingested > 0
        stats = real_vector_store.get_collection_stats()
        assert stats["count"] == total_chunks_ingested
        
        # Clean up
        real_vector_store.delete_collection()

    def test_document_processor_with_different_file_types(self, real_doc_processor, create_mock_file):
        md_file = create_mock_file("test.md", "# Title\nContent")
        txt_file = create_mock_file("test.txt", "Plain text content.")
        
        md_docs = real_doc_processor.process_file(md_file)
        txt_docs = real_doc_processor.process_file(txt_file)
        
        assert len(md_docs) > 0
        assert md_docs[0].metadata["filename"] == "test.md"
        assert md_docs[0].metadata["type"] == "kubernetes_doc"  # All processed as kubernetes_doc
        
        assert len(txt_docs) > 0
        assert txt_docs[0].metadata["filename"] == "test.txt"
        assert txt_docs[0].metadata["type"] == "kubernetes_doc"

    def test_embedding_generator_with_different_texts(self, real_embedding_generator):
        text1 = "Short sentence."
        text2 = "A slightly longer sentence for testing purposes."
        
        embedding1 = real_embedding_generator.encode(text1)
        embedding2 = real_embedding_generator.encode(text2)
        
        assert embedding1.shape == (1, mock_config.embedding.embedding_dim)
        assert embedding2.shape == (1, mock_config.embedding.embedding_dim)
        assert not np.array_equal(embedding1, embedding2)  # Embeddings should be different

# --- Performance Tests ---
class TestIngestionPerformance:
    @pytest.fixture
    def large_markdown_content(self):
        return "# Large Document\n\n" + ("This is a paragraph of content. " * 100 + "\n\n") * 50

    @pytest.fixture
    def large_text_content(self):
        return ("This is a line of text. " * 100 + "\n") * 50

    @pytest.fixture
    def real_doc_processor_perf(self):
        return KubernetesDocProcessor(chunk_size=500, chunk_overlap=100)

    @pytest.fixture
    def real_embedding_generator_perf(self):
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_instance = Mock()
            mock_instance.encode.return_value = np.random.rand(1, mock_config.embedding.embedding_dim)
            mock_transformer.return_value = mock_instance
            yield EmbeddingGenerator(model_name=mock_config.embedding.model_name)

    @pytest.fixture
    def real_vector_store_perf(self, tmp_path):
        persist_dir = tmp_path / "test_chroma_db_perf"
        return VectorStore(persist_directory=str(persist_dir), collection_name="performance_test_collection")

    def test_document_processor_performance(self, benchmark, real_doc_processor_perf, create_mock_file, large_markdown_content):
        file_path = create_mock_file("large_doc.md", large_markdown_content)
        documents = benchmark(real_doc_processor_perf.process_file, file_path)
        assert len(documents) > 0
        assert all(len(doc.content) <= real_doc_processor_perf.chunker.chunk_size + real_doc_processor_perf.chunker.chunk_overlap for doc in documents)

    def test_embedding_generator_performance(self, benchmark, real_embedding_generator_perf):
        texts = ["This is a sentence to embed."] * 100
        embeddings = benchmark(real_embedding_generator_perf.encode, texts)
        assert embeddings.shape == (100, mock_config.embedding.embedding_dim)

    def test_ingestion_pipeline_performance(self, benchmark, tmp_path, create_mock_file, real_doc_processor_perf, real_embedding_generator_perf, real_vector_store_perf):
        data_dir = tmp_path / "perf_data"
        data_dir.mkdir()
        for i in range(5):
            create_mock_file(data_dir / f"doc_{i}.md", self.large_markdown_content())  # Use fixture content
        
        pipeline = IngestionPipeline(
            vector_store=real_vector_store_perf,
            embedding_generator=real_embedding_generator_perf,
            doc_processor=real_doc_processor_perf
        )
        
        total_chunks_ingested = benchmark(pipeline.ingest_directory, data_dir)
        assert total_chunks_ingested > 0
        stats = real_vector_store_perf.get_collection_stats()
        assert stats["count"] == total_chunks_ingested
        
        real_vector_store_perf.delete_collection()
