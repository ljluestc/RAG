"""DevOps Exercises connector.

Fetches content from https://github.com/bregman-arie/devops-exercises
and ingests the markdown Q&A content into the RAG system by topic
(Kubernetes, Docker, AWS, Linux, Networking, CI/CD, etc.).

Usage:
    from src.connectors.devops_exercises_connector import DevOpsExercisesConnector
    connector = DevOpsExercisesConnector()
    stats = connector.fetch_and_ingest(topics=["kubernetes", "docker", "aws"])
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger()

REPO_URL = "https://github.com/bregman-arie/devops-exercises.git"

# Map topic names to directory paths within the repo
TOPIC_DIRS = {
    "kubernetes": "topics/kubernetes",
    "docker": "topics/docker",
    "aws": "topics/aws",
    "azure": "topics/azure",
    "gcp": "topics/gcp",
    "linux": "topics/linux",
    "networking": "topics/networking",
    "git": "topics/git",
    "cicd": "topics/cicd",
    "ansible": "topics/ansible",
    "terraform": "topics/terraform",
    "prometheus": "topics/prometheus",
    "python": "topics/python",
    "go": "topics/go",
    "shell": "topics/shell",
    "sql": "topics/sql",
    "general": "topics/general",
    "cloud": "topics/cloud",
    "containers": "topics/containers",
}

# All known topic directories (fallback: scan topics/ folder)
ALL_TOPICS_DIR = "topics"


class DevOpsExercisesConnector:
    """Connector for bregman-arie/devops-exercises GitHub repository."""

    def __init__(
        self,
        clone_dir: str = "data/devops_exercises",
        repo_url: str = REPO_URL,
    ):
        """
        Initialize the connector.

        Args:
            clone_dir: Local directory to clone/store the repo
            repo_url: Git repository URL
        """
        self.clone_dir = Path(clone_dir)
        self.repo_url = repo_url

    def clone_or_pull(self) -> Path:
        """
        Clone the repo if not present, or pull latest changes.

        Returns:
            Path to the repo root
        """
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

    def list_available_topics(self) -> List[str]:
        """List topics available in the cloned repo."""
        self.clone_or_pull()
        topics_dir = self.clone_dir / ALL_TOPICS_DIR

        if not topics_dir.exists():
            # Fallback: scan for known topic dirs
            return [t for t, d in TOPIC_DIRS.items() if (self.clone_dir / d).exists()]

        topics = []
        for child in sorted(topics_dir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                topics.append(child.name)
        return topics

    def get_topic_files(self, topic: str) -> List[Path]:
        """
        Get all markdown files for a topic.

        Args:
            topic: Topic name (e.g., "kubernetes", "docker")

        Returns:
            List of markdown file paths
        """
        # Try known mapping first
        if topic.lower() in TOPIC_DIRS:
            topic_path = self.clone_dir / TOPIC_DIRS[topic.lower()]
        else:
            topic_path = self.clone_dir / ALL_TOPICS_DIR / topic.lower()

        if not topic_path.exists():
            logger.warning(f"Topic directory not found: {topic_path}")
            return []

        files = list(topic_path.rglob("*.md"))
        logger.info(f"Found {len(files)} markdown files for topic '{topic}'")
        return files

    def ingest_topic(self, topic: str, pipeline=None) -> Dict[str, Any]:
        """
        Ingest all markdown files for a specific topic.

        Args:
            topic: Topic name
            pipeline: Optional IngestionPipeline instance

        Returns:
            Ingestion statistics
        """
        if pipeline is None:
            pipeline = self._create_pipeline()

        files = self.get_topic_files(topic)

        stats = {
            "topic": topic,
            "total_files": len(files),
            "processed_files": 0,
            "total_chunks": 0,
            "failed_files": [],
        }

        for md_file in files:
            try:
                num_chunks = pipeline.ingest_file(md_file)
                stats["processed_files"] += 1
                stats["total_chunks"] += num_chunks
            except Exception as e:
                logger.error(f"Failed to process {md_file}: {e}")
                stats["failed_files"].append(str(md_file))

        logger.info(f"Topic '{topic}' ingestion: {stats}")
        return stats

    def fetch_and_ingest(
        self,
        topics: Optional[List[str]] = None,
        pipeline=None,
    ) -> Dict[str, Any]:
        """
        Clone/pull repo and ingest specified topics.

        Args:
            topics: List of topics to ingest (None = all available)
            pipeline: Optional IngestionPipeline instance

        Returns:
            Overall ingestion statistics
        """
        self.clone_or_pull()

        if pipeline is None:
            pipeline = self._create_pipeline()

        if topics is None:
            topics = self.list_available_topics()

        logger.info(f"Ingesting topics: {topics}")

        overall = {
            "topics_processed": [],
            "total_files": 0,
            "total_chunks": 0,
            "failed_topics": [],
        }

        for topic in topics:
            try:
                stats = self.ingest_topic(topic, pipeline)
                overall["topics_processed"].append(topic)
                overall["total_files"] += stats["total_files"]
                overall["total_chunks"] += stats["total_chunks"]
            except Exception as e:
                logger.error(f"Failed topic '{topic}': {e}")
                overall["failed_topics"].append({"topic": topic, "error": str(e)})

        logger.info(f"DevOps exercises ingestion complete: {overall}")
        return overall

    def _create_pipeline(self):
        """Create an ingestion pipeline from config."""
        from ..ingestion.pipeline import create_ingestion_pipeline
        from ..utils.config_loader import load_config

        config = load_config()
        return create_ingestion_pipeline(config)
