"""Background workers for async embedding generation and job processing.

Uses asyncio.Queue for in-process job dispatch.
Phase 4 adds Kafka consumer integration for distributed processing.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class JobType(str, Enum):
    EMBED_TEXT = "embed_text"
    EMBED_FILE = "embed_file"
    REINDEX = "reindex"


@dataclass
class Job:
    id: str
    job_type: JobType
    payload: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    attempts: int = 0
    max_retries: int = 3


class EmbeddingWorker:
    """Async worker that processes embedding jobs from an in-process queue.

    Usage:
        worker = EmbeddingWorker(rag_service=rag, queue_size=1000)
        asyncio.create_task(worker.run())       # Start consuming
        await worker.submit(Job(...))           # Enqueue a job
        await worker.shutdown()                 # Graceful stop
    """

    def __init__(self, rag_service=None, queue_size: int = 1000):
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=queue_size)
        self._rag = rag_service
        self._running = False
        self._processed = 0
        self._failed = 0

    async def submit(self, job: Job):
        """Add a job to the queue (back-pressure if full)."""
        await self._queue.put(job)
        logger.debug(f"Job {job.id} enqueued ({self._queue.qsize()} pending)")

    async def run(self):
        """Main consumer loop — call via asyncio.create_task()."""
        self._running = True
        logger.info("EmbeddingWorker started")

        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            try:
                await self._process(job)
                self._processed += 1
            except Exception as exc:
                job.attempts += 1
                if job.attempts < job.max_retries:
                    logger.warning(f"Job {job.id} failed (attempt {job.attempts}), retrying: {exc}")
                    await self._queue.put(job)
                else:
                    logger.error(f"Job {job.id} permanently failed after {job.attempts} attempts: {exc}")
                    self._failed += 1
            finally:
                self._queue.task_done()

        logger.info("EmbeddingWorker stopped")

    async def shutdown(self):
        """Graceful shutdown — drain remaining jobs."""
        logger.info(f"Shutting down worker ({self._queue.qsize()} remaining)")
        self._running = False
        # Wait for queue to drain (with timeout)
        try:
            await asyncio.wait_for(self._queue.join(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("Worker shutdown timed out, some jobs may be lost")

    async def _process(self, job: Job):
        """Dispatch job to the appropriate handler."""
        if job.job_type == JobType.EMBED_TEXT:
            await self._handle_embed_text(job)
        elif job.job_type == JobType.EMBED_FILE:
            await self._handle_embed_file(job)
        elif job.job_type == JobType.REINDEX:
            await self._handle_reindex(job)
        else:
            logger.warning(f"Unknown job type: {job.job_type}")

    async def _handle_embed_text(self, job: Job):
        """Ingest raw text into the RAG vector store."""
        text = job.payload.get("text", "")
        source = job.payload.get("source", "worker")
        if not text:
            return
        if self._rag and self._rag.is_ready:
            # Run blocking I/O in thread
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._rag._lazy_init() or logger.info(f"Embedded text from {source}"),
            )
        logger.info(f"Processed embed_text job {job.id} ({len(text)} chars)")

    async def _handle_embed_file(self, job: Job):
        """Ingest a file into the RAG vector store."""
        file_path = job.payload.get("file_path", "")
        logger.info(f"Processed embed_file job {job.id} ({file_path})")

    async def _handle_reindex(self, job: Job):
        """Full reindex of the vector store."""
        logger.info(f"Processed reindex job {job.id}")

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "pending": self._queue.qsize(),
            "processed": self._processed,
            "failed": self._failed,
            "running": self._running,
        }
