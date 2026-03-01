"""Ingestion pipeline for processing and indexing Kubernetes documentation."""

import json
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

from ..retrieval.vector_store import VectorStore
from ..utils.logger import get_logger
from .document_processor import KubernetesDocProcessor, UnifiedDocProcessor
from .embeddings import EmbeddingGenerator

logger = get_logger()


class IngestionPipeline:
    """Pipeline for ingesting Kubernetes documentation into the RAG system."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator,
        doc_processor: KubernetesDocProcessor,
    ):
        """
        Initialize the ingestion pipeline.

        Args:
            vector_store: Vector store instance
            embedding_generator: Embedding generator instance
            doc_processor: Document processor instance
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.doc_processor = doc_processor

    def _get_source_type(self, file_path: Path) -> str:
        """Infer doc_type from path for runbooks, incidents, configs."""
        path_str = str(file_path).lower()
        if "runbook" in path_str:
            return "runbook"
        if "incident" in path_str:
            return "incident"
        if "config" in path_str:
            return "config"
        if "system_design" in path_str or "system-design" in path_str:
            return "system_design"
        return "kubernetes_doc"

    def ingest_file(self, file_path: Path, source_type: Optional[str] = None) -> int:
        """
        Ingest a single file (markdown or PDF).

        Args:
            file_path: Path to the file
            source_type: Optional override for doc type (runbook, incident, config)

        Returns:
            Number of documents ingested
        """
        logger.info(f"Processing file: {file_path}")
        file_path = Path(file_path)

        # Use unified processor for PDF files, original for MD
        if file_path.suffix.lower() == ".pdf":
            from .document_processor import PDFProcessor
            pdf_proc = PDFProcessor(
                chunk_size=self.doc_processor.chunker.chunk_size,
                chunk_overlap=self.doc_processor.chunker.chunk_overlap,
            )
            documents = pdf_proc.process_file(file_path)
        else:
            documents = self.doc_processor.process_file(file_path)

        if not documents:
            logger.warning(f"No documents extracted from {file_path}")
            return 0

        # Override metadata type for runbooks, incidents, configs
        doc_type = source_type or self._get_source_type(file_path)
        if doc_type != "kubernetes_doc":
            for doc in documents:
                doc.metadata["type"] = doc_type

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} chunks")
        embeddings = self.embedding_generator.encode_documents(
            documents, show_progress=False
        )

        # Add to vector store
        logger.info(f"Adding documents to vector store")
        self.vector_store.add_documents(documents, embeddings)

        logger.info(f"Successfully ingested {len(documents)} chunks from {file_path}")
        return len(documents)

    def ingest_directory(self, directory: Path, file_pattern: str = "*") -> dict:
        """
        Ingest all files from a directory.

        Args:
            directory: Directory path
            file_pattern: File pattern to match

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting ingestion from directory: {directory}")

        directory = Path(directory)
        if not directory.exists():
            raise ValueError(f"Directory not found: {directory}")

        # Find all matching files including config formats
        supported_extensions = {
            ".md",
            ".markdown",
            ".txt",
            ".pdf",
            ".yaml",
            ".yml",
            ".json",
            ".ini",
            ".conf",
        }
        if file_pattern == "*":
            files = [f for f in directory.rglob("*") if f.suffix.lower() in supported_extensions]
        else:
            files = list(directory.rglob(file_pattern))
        logger.info(f"Found {len(files)} files to process")

        stats = {
            "total_files": len(files),
            "processed_files": 0,
            "total_chunks": 0,
            "failed_files": [],
        }

        # Process each file
        for file_path in tqdm(files, desc="Ingesting files"):
            try:
                num_chunks = self.ingest_file(file_path)
                stats["processed_files"] += 1
                stats["total_chunks"] += num_chunks
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                stats["failed_files"].append(str(file_path))

        logger.info(f"Ingestion complete. Stats: {stats}")
        return stats

    def ingest_from_text(
        self, text: str, metadata: dict = None, source_name: str = "inline_text"
    ) -> int:
        """
        Ingest text directly.

        Args:
            text: Text content
            metadata: Optional metadata
            source_name: Name for the source

        Returns:
            Number of chunks created
        """
        if metadata is None:
            metadata = {}

        metadata["source"] = source_name
        metadata["type"] = "inline_text"

        # Create a temporary file-like structure
        from ..ingestion.document_processor import Document

        # Chunk the text
        chunks = self.doc_processor.chunker.chunk_text(text, metadata)

        if not chunks:
            return 0

        # Generate embeddings
        embeddings = self.embedding_generator.encode_documents(chunks)

        # Add to vector store
        self.vector_store.add_documents(chunks, embeddings)

        return len(chunks)

    def save_processing_stats(self, stats: dict, output_path: Path):
        """Save processing statistics to a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2)

        logger.info(f"Stats saved to {output_path}")


def create_ingestion_pipeline(config: dict) -> IngestionPipeline:
    """
    Create an ingestion pipeline from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        IngestionPipeline instance
    """
    # Create components
    vector_store = VectorStore(
        collection_name=config.vector_db.collection_name,
        persist_directory=config.vector_db.persist_directory,
        distance_metric=config.vector_db.distance_metric,
    )

    embedding_generator = EmbeddingGenerator(model_name=config.embedding.model_name)

    doc_processor = KubernetesDocProcessor(
        chunk_size=config.document_processing.chunk_size,
        chunk_overlap=config.document_processing.chunk_overlap,
    )

    return IngestionPipeline(
        vector_store=vector_store,
        embedding_generator=embedding_generator,
        doc_processor=doc_processor,
    )
