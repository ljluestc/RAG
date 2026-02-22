"""GitHub PDF Knowledge Graph Connector.

Fetches PDF books/papers from GitHub repositories (e.g., manjunath5496 collections),
downloads them, ingests into the RAG system, and builds knowledge graph edges
linking topics → documents → concepts.

Usage:
    from src.connectors.github_pdf_connector import GitHubPDFConnector
    connector = GitHubPDFConnector()
    stats = connector.fetch_and_ingest(
        repos=["DevOps-Books", "Linux-Books", "Networking-Books"],
        owner="manjunath5496",
        max_per_repo=5,
    )

    # Access the knowledge graph
    graph = connector.get_knowledge_graph()
"""

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from ..utils.logger import get_logger

logger = get_logger()

GITHUB_API = "https://api.github.com"

# Relevant repos on manjunath5496 for DevOps/CS knowledge
DEFAULT_REPOS = [
    "DevOps-Books",
    "Linux-Books",
    "Networking-Books",
    "Cyber-Security-Books",
    "Microservices-Books",
    "Algorithm-Books",
    "Computer-Science-Reference-Books",
    "Data-Technology-Books",
    "The-Best-Books-on-Blockchain",
]


@dataclass
class PDFEntry:
    """A PDF file found in a GitHub repo."""

    owner: str
    repo: str
    filename: str
    download_url: str
    size_bytes: int
    sha: str
    topic: str  # derived from repo name
    local_path: Optional[str] = None


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""

    source: str  # e.g. topic name
    target: str  # e.g. document filename
    relation: str  # e.g. "has_document", "covers_topic"
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class GitHubPDFConnector:
    """Connector that fetches PDFs from GitHub repos and ingests them."""

    def __init__(
        self,
        download_dir: str = "data/github_pdfs",
        github_token: Optional[str] = None,
        rate_limit_seconds: float = 1.0,
        max_file_size_mb: float = 50.0,
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.rate_limit = rate_limit_seconds
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self._last_request = 0.0
        self.knowledge_graph: List[KnowledgeEdge] = []

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            h["Authorization"] = f"token {self.token}"
        return h

    def _wait(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def _topic_from_repo(self, repo_name: str) -> str:
        """Derive a topic name from a repo name like 'DevOps-Books' → 'devops'."""
        name = repo_name.lower()
        for suffix in ["-books", "-papers", "-study-material", "-tutorial"]:
            name = name.replace(suffix, "")
        return name.replace("-", "_").strip("_")

    def list_pdfs(
        self, owner: str, repo: str, path: str = ""
    ) -> List[PDFEntry]:
        """List all PDF files in a GitHub repo (recursive)."""
        self._wait()
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        logger.info(f"Listing PDFs in {owner}/{repo}/{path}")

        try:
            resp = requests.get(url, headers=self._headers(), timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to list {owner}/{repo}: {e}")
            return []

        entries = []
        topic = self._topic_from_repo(repo)

        for item in resp.json():
            if item["type"] == "file" and item["name"].lower().endswith(".pdf"):
                if item["size"] <= self.max_file_size:
                    entries.append(
                        PDFEntry(
                            owner=owner,
                            repo=repo,
                            filename=item["name"],
                            download_url=item["download_url"],
                            size_bytes=item["size"],
                            sha=item["sha"],
                            topic=topic,
                        )
                    )
            elif item["type"] == "dir":
                # Recurse into subdirectories
                sub = self.list_pdfs(owner, repo, item["path"])
                entries.extend(sub)

        logger.info(f"Found {len(entries)} PDFs in {owner}/{repo}")
        return entries

    def download_pdf(self, entry: PDFEntry) -> Path:
        """Download a single PDF."""
        topic_dir = self.download_dir / entry.topic
        topic_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^\w\-.]", "_", entry.filename)
        local_path = topic_dir / safe_name

        if local_path.exists():
            logger.info(f"Already downloaded: {local_path}")
            entry.local_path = str(local_path)
            return local_path

        logger.info(f"Downloading: {entry.filename} ({entry.size_bytes // 1024}KB)")
        self._wait()

        resp = requests.get(entry.download_url, timeout=120, stream=True)
        resp.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        entry.local_path = str(local_path)
        logger.info(f"Downloaded to: {local_path}")
        return local_path

    def ingest_pdf(self, entry: PDFEntry, pipeline=None) -> int:
        """Ingest a single PDF into the RAG system."""
        if not entry.local_path or not Path(entry.local_path).exists():
            raise FileNotFoundError(f"PDF not downloaded: {entry.filename}")

        if pipeline is None:
            pipeline = self._create_pipeline()

        num_chunks = pipeline.ingest_file(Path(entry.local_path))

        # Add knowledge graph edges
        self.knowledge_graph.append(
            KnowledgeEdge(
                source=entry.topic,
                target=entry.filename,
                relation="has_document",
                metadata={
                    "repo": f"{entry.owner}/{entry.repo}",
                    "size_bytes": entry.size_bytes,
                    "chunks": num_chunks,
                    "url": f"https://github.com/{entry.owner}/{entry.repo}",
                },
            )
        )

        logger.info(f"Ingested {num_chunks} chunks from {entry.filename}")
        return num_chunks

    def fetch_and_ingest(
        self,
        repos: Optional[List[str]] = None,
        owner: str = "manjunath5496",
        max_per_repo: int = 5,
        pipeline=None,
    ) -> Dict[str, Any]:
        """Fetch PDFs from multiple repos and ingest them.

        Args:
            repos: List of repo names (default: DEFAULT_REPOS)
            owner: GitHub username
            max_per_repo: Max PDFs to download per repo
            pipeline: Optional IngestionPipeline

        Returns:
            Statistics dictionary
        """
        if repos is None:
            repos = DEFAULT_REPOS

        if pipeline is None:
            pipeline = self._create_pipeline()

        stats = {
            "repos_processed": [],
            "total_pdfs_found": 0,
            "total_downloaded": 0,
            "total_ingested": 0,
            "total_chunks": 0,
            "failed": [],
        }

        for repo_name in repos:
            logger.info(f"Processing repo: {owner}/{repo_name}")

            pdfs = self.list_pdfs(owner, repo_name)
            stats["total_pdfs_found"] += len(pdfs)

            # Take only max_per_repo (sorted by size, smallest first for faster processing)
            pdfs.sort(key=lambda p: p.size_bytes)
            pdfs = pdfs[:max_per_repo]

            repo_stats = {"repo": repo_name, "found": len(pdfs), "ingested": 0, "chunks": 0}

            for pdf in pdfs:
                try:
                    self.download_pdf(pdf)
                    stats["total_downloaded"] += 1

                    num_chunks = self.ingest_pdf(pdf, pipeline)
                    stats["total_ingested"] += 1
                    stats["total_chunks"] += num_chunks
                    repo_stats["ingested"] += 1
                    repo_stats["chunks"] += num_chunks
                except Exception as e:
                    logger.error(f"Failed to process {pdf.filename}: {e}")
                    stats["failed"].append({"file": pdf.filename, "error": str(e)})

            stats["repos_processed"].append(repo_stats)

        logger.info(f"GitHub PDF ingestion complete: {stats['total_ingested']} PDFs, {stats['total_chunks']} chunks")
        return stats

    def get_knowledge_graph(self) -> Dict[str, Any]:
        """Return the knowledge graph as a JSON-serializable dict."""
        # Collect unique nodes
        nodes = set()
        for edge in self.knowledge_graph:
            nodes.add(edge.source)
            nodes.add(edge.target)

        return {
            "nodes": [
                {"id": n, "type": "topic" if "_" in n or n.isalpha() else "document"}
                for n in sorted(nodes)
            ],
            "edges": [asdict(e) for e in self.knowledge_graph],
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(self.knowledge_graph),
                "topics": len({e.source for e in self.knowledge_graph}),
                "documents": len({e.target for e in self.knowledge_graph}),
            },
        }

    def save_knowledge_graph(self, output_path: Optional[str] = None):
        """Save the knowledge graph to a JSON file."""
        if output_path is None:
            output_path = str(self.download_dir / "knowledge_graph.json")

        graph = self.get_knowledge_graph()
        with open(output_path, "w") as f:
            json.dump(graph, f, indent=2)

        logger.info(f"Knowledge graph saved to {output_path}")
        return output_path

    def save_metadata(self, entries: List[PDFEntry], output_path: Optional[str] = None):
        """Save PDF metadata to JSON."""
        if output_path is None:
            output_path = str(self.download_dir / "metadata.json")

        data = [asdict(e) for e in entries]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Metadata saved to {output_path}")

    def _create_pipeline(self):
        from ..ingestion.pipeline import create_ingestion_pipeline
        from ..utils.config_loader import load_config

        config = load_config()
        return create_ingestion_pipeline(config)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GitHub PDF Knowledge Graph Connector")
    parser.add_argument("--owner", default="manjunath5496", help="GitHub username")
    parser.add_argument(
        "--repos",
        nargs="*",
        default=None,
        help="Repo names (default: DevOps/Linux/Networking collections)",
    )
    parser.add_argument("--max-per-repo", type=int, default=5, help="Max PDFs per repo")
    parser.add_argument("--download-dir", default="data/github_pdfs", help="Download directory")
    parser.add_argument("--download-only", action="store_true", help="Download without ingesting")
    parser.add_argument("--list-only", action="store_true", help="List PDFs without downloading")
    args = parser.parse_args()

    from ..utils.logger import setup_logger

    setup_logger()

    connector = GitHubPDFConnector(download_dir=args.download_dir)

    repos = args.repos or DEFAULT_REPOS

    if args.list_only:
        for repo in repos:
            pdfs = connector.list_pdfs(args.owner, repo)
            print(f"\n{args.owner}/{repo}: {len(pdfs)} PDFs")
            for p in pdfs[:10]:
                print(f"  - {p.filename} ({p.size_bytes // 1024}KB)")
        return

    if args.download_only:
        for repo in repos:
            pdfs = connector.list_pdfs(args.owner, repo)
            pdfs.sort(key=lambda p: p.size_bytes)
            for p in pdfs[: args.max_per_repo]:
                try:
                    connector.download_pdf(p)
                except Exception as e:
                    print(f"  Failed: {p.filename}: {e}")
        print(f"\nDownloaded to {args.download_dir}/")
        return

    stats = connector.fetch_and_ingest(
        repos=repos, owner=args.owner, max_per_repo=args.max_per_repo
    )

    print(f"\nIngestion complete:")
    print(f"  PDFs found: {stats['total_pdfs_found']}")
    print(f"  Downloaded: {stats['total_downloaded']}")
    print(f"  Ingested:   {stats['total_ingested']}")
    print(f"  Chunks:     {stats['total_chunks']}")

    # Save knowledge graph
    graph_path = connector.save_knowledge_graph()
    print(f"  Knowledge graph: {graph_path}")


if __name__ == "__main__":
    main()
