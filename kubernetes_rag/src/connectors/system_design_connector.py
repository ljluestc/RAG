"""System design repository connector for RAG ingestion."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from ..utils.logger import get_logger

logger = get_logger()

SYSTEM_DESIGN_REPO_URL = "https://github.com/ljluestc/system-design.git"


class SystemDesignConnector:
    """Connector for cloning/pulling and ingesting system-design materials."""

    def __init__(
        self,
        clone_dir: str = "data/system_design",
        repo_url: str = SYSTEM_DESIGN_REPO_URL,
    ):
        self.clone_dir = Path(clone_dir)
        self.repo_url = repo_url

    def clone_or_pull(self) -> Path:
        """Clone repository if missing, otherwise fast-forward pull."""
        if (self.clone_dir / ".git").exists():
            logger.info(f"Pulling latest changes in {self.clone_dir}")
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(self.clone_dir),
                capture_output=True,
                text=True,
            )
        else:
            logger.info(f"Cloning {self.repo_url} to {self.clone_dir}")
            self.clone_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth=1", self.repo_url, str(self.clone_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
        return self.clone_dir

    def list_supported_files(self) -> List[Path]:
        """List files that can be ingested into the RAG pipeline."""
        self.clone_or_pull()
        supported_suffixes = {
            ".md",
            ".markdown",
            ".txt",
            ".pdf",
            ".yaml",
            ".yml",
            ".json",
        }
        return sorted(
            f
            for f in self.clone_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in supported_suffixes
        )

    def fetch_and_ingest(self, pipeline=None) -> Dict[str, Any]:
        """Clone/pull the repository and ingest all supported files."""
        if pipeline is None:
            pipeline = self._create_pipeline()

        files = self.list_supported_files()
        stats: Dict[str, Any] = {
            "repo": self.repo_url,
            "total_files": len(files),
            "processed_files": 0,
            "total_chunks": 0,
            "failed_files": [],
        }

        for file_path in files:
            try:
                chunks = pipeline.ingest_file(file_path, source_type="system_design")
                stats["processed_files"] += 1
                stats["total_chunks"] += chunks
            except Exception as exc:
                logger.error(f"Failed to ingest {file_path}: {exc}")
                stats["failed_files"].append(str(file_path))

        logger.info(
            "System design ingestion: "
            f"{stats['processed_files']}/{stats['total_files']} files, "
            f"{stats['total_chunks']} chunks"
        )
        return stats

    def _create_pipeline(self):
        from ..ingestion.pipeline import create_ingestion_pipeline
        from ..utils.config_loader import load_config

        config = load_config()
        return create_ingestion_pipeline(config)

