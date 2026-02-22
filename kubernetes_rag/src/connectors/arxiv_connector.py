"""arXiv data pipeline connector.

Searches arXiv for papers, downloads PDFs, and ingests them into the RAG system.

Usage (standalone):
    python -m src.connectors.arxiv_connector --query "RAG retrieval augmented generation" --max-results 5

Usage (in code):
    from src.connectors.arxiv_connector import ArxivConnector
    connector = ArxivConnector(download_dir="data/arxiv_papers")
    papers = connector.search("transformer attention mechanism", max_results=5)
    connector.download_and_ingest(papers)
"""

import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from ..utils.logger import get_logger

logger = get_logger()

# arXiv API base URL
ARXIV_API_URL = "http://export.arxiv.org/api/query"


@dataclass
class ArxivPaper:
    """Represents an arXiv paper."""

    arxiv_id: str
    title: str
    summary: str
    authors: List[str]
    published: str
    updated: str
    pdf_url: str
    categories: List[str]
    primary_category: str
    doi: Optional[str] = None
    local_pdf_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArxivConnector:
    """Connector for searching and downloading arXiv papers."""

    def __init__(
        self,
        download_dir: str = "data/arxiv_papers",
        rate_limit_seconds: float = 3.0,
    ):
        """
        Initialize the arXiv connector.

        Args:
            download_dir: Directory to store downloaded PDFs
            rate_limit_seconds: Delay between API requests (arXiv asks for 3s)
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Enforce rate limiting for arXiv API."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        start: int = 0,
        categories: Optional[List[str]] = None,
    ) -> List[ArxivPaper]:
        """
        Search arXiv for papers.

        Args:
            query: Search query (supports arXiv query syntax)
            max_results: Maximum number of results
            sort_by: Sort field (relevance, lastUpdatedDate, submittedDate)
            sort_order: Sort order (ascending, descending)
            start: Starting index for pagination
            categories: Optional list of arXiv categories to filter (e.g., ["cs.IR", "cs.CL"])

        Returns:
            List of ArxivPaper objects
        """
        # Build query with optional category filter
        search_query = f"all:{query}"
        if categories:
            cat_filter = " OR ".join(f"cat:{c}" for c in categories)
            search_query = f"({search_query}) AND ({cat_filter})"

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        logger.info(f"Searching arXiv: '{query}' (max={max_results})")
        self._rate_limit()

        response = requests.get(ARXIV_API_URL, params=params, timeout=30)
        response.raise_for_status()

        papers = self._parse_atom_feed(response.text)
        logger.info(f"Found {len(papers)} papers")
        return papers

    def _parse_atom_feed(self, xml_text: str) -> List[ArxivPaper]:
        """Parse arXiv Atom feed XML into ArxivPaper objects."""
        import xml.etree.ElementTree as ET

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        root = ET.fromstring(xml_text)
        papers = []

        for entry in root.findall("atom:entry", ns):
            # Extract arxiv ID from the entry id URL
            entry_id = entry.find("atom:id", ns).text
            arxiv_id = entry_id.split("/abs/")[-1]

            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")

            authors = [
                a.find("atom:name", ns).text
                for a in entry.findall("atom:author", ns)
            ]

            published = entry.find("atom:published", ns).text
            updated = entry.find("atom:updated", ns).text

            # Find PDF link
            pdf_url = ""
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break

            # Categories
            categories = [
                c.get("term") for c in entry.findall("atom:category", ns)
            ]
            primary_cat_el = entry.find("arxiv:primary_category", ns)
            primary_category = primary_cat_el.get("term") if primary_cat_el is not None else (categories[0] if categories else "")

            # DOI
            doi_el = entry.find("arxiv:doi", ns)
            doi = doi_el.text if doi_el is not None else None

            papers.append(
                ArxivPaper(
                    arxiv_id=arxiv_id,
                    title=title,
                    summary=summary,
                    authors=authors,
                    published=published,
                    updated=updated,
                    pdf_url=pdf_url,
                    categories=categories,
                    primary_category=primary_category,
                    doi=doi,
                )
            )

        return papers

    def download_pdf(self, paper: ArxivPaper) -> Path:
        """
        Download a paper's PDF.

        Args:
            paper: ArxivPaper to download

        Returns:
            Path to the downloaded PDF
        """
        safe_id = paper.arxiv_id.replace("/", "_")
        pdf_path = self.download_dir / f"{safe_id}.pdf"

        if pdf_path.exists():
            logger.info(f"PDF already downloaded: {pdf_path}")
            paper.local_pdf_path = str(pdf_path)
            return pdf_path

        pdf_url = paper.pdf_url
        if not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{paper.arxiv_id}"

        logger.info(f"Downloading PDF: {paper.title[:60]}...")
        self._rate_limit()

        response = requests.get(pdf_url, timeout=60, stream=True)
        response.raise_for_status()

        with open(pdf_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        paper.local_pdf_path = str(pdf_path)
        logger.info(f"Downloaded to: {pdf_path}")
        return pdf_path

    def download_papers(self, papers: List[ArxivPaper]) -> List[Path]:
        """Download PDFs for multiple papers."""
        paths = []
        for paper in papers:
            try:
                path = self.download_pdf(paper)
                paths.append(path)
            except Exception as e:
                logger.error(f"Failed to download {paper.arxiv_id}: {e}")
        return paths

    def ingest_paper(self, paper: ArxivPaper, pipeline=None) -> int:
        """
        Ingest a single paper into the RAG system.

        Args:
            paper: ArxivPaper with local_pdf_path set
            pipeline: Optional IngestionPipeline instance

        Returns:
            Number of chunks ingested
        """
        if not paper.local_pdf_path or not Path(paper.local_pdf_path).exists():
            raise FileNotFoundError(f"PDF not downloaded for {paper.arxiv_id}")

        if pipeline is None:
            pipeline = self._create_pipeline()

        pdf_path = Path(paper.local_pdf_path)
        num_chunks = pipeline.ingest_file(pdf_path)

        logger.info(
            f"Ingested {num_chunks} chunks from: {paper.title[:60]} ({paper.arxiv_id})"
        )
        return num_chunks

    def download_and_ingest(
        self, papers: List[ArxivPaper], pipeline=None
    ) -> Dict[str, Any]:
        """
        Download and ingest multiple papers.

        Args:
            papers: List of papers to process
            pipeline: Optional IngestionPipeline instance

        Returns:
            Statistics dictionary
        """
        if pipeline is None:
            pipeline = self._create_pipeline()

        stats = {
            "total_papers": len(papers),
            "downloaded": 0,
            "ingested": 0,
            "total_chunks": 0,
            "failed": [],
        }

        for paper in papers:
            try:
                self.download_pdf(paper)
                stats["downloaded"] += 1

                num_chunks = self.ingest_paper(paper, pipeline)
                stats["ingested"] += 1
                stats["total_chunks"] += num_chunks
            except Exception as e:
                logger.error(f"Failed to process {paper.arxiv_id}: {e}")
                stats["failed"].append(
                    {"arxiv_id": paper.arxiv_id, "error": str(e)}
                )

        logger.info(f"arXiv ingestion complete: {stats}")
        return stats

    def save_metadata(self, papers: List[ArxivPaper], output_path: Optional[str] = None):
        """Save paper metadata to JSON for tracking."""
        if output_path is None:
            output_path = str(self.download_dir / "metadata.json")

        data = [p.to_dict() for p in papers]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Metadata saved to {output_path}")

    def _create_pipeline(self):
        """Create an ingestion pipeline from config."""
        from ..ingestion.pipeline import create_ingestion_pipeline
        from ..utils.config_loader import load_config

        config = load_config()
        return create_ingestion_pipeline(config)


def main():
    """CLI entry point for arXiv connector."""
    import argparse

    parser = argparse.ArgumentParser(description="arXiv paper connector for RAG")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--max-results", type=int, default=5, help="Max papers")
    parser.add_argument(
        "--categories", nargs="*", help="arXiv categories (e.g., cs.IR cs.CL)"
    )
    parser.add_argument(
        "--download-dir", default="data/arxiv_papers", help="PDF download directory"
    )
    parser.add_argument(
        "--download-only", action="store_true", help="Download without ingesting"
    )
    parser.add_argument(
        "--sort-by",
        default="relevance",
        choices=["relevance", "lastUpdatedDate", "submittedDate"],
    )
    args = parser.parse_args()

    from ..utils.logger import setup_logger

    setup_logger()

    connector = ArxivConnector(download_dir=args.download_dir)

    # Search
    papers = connector.search(
        args.query,
        max_results=args.max_results,
        sort_by=args.sort_by,
        categories=args.categories,
    )

    if not papers:
        print("No papers found.")
        return

    print(f"\nFound {len(papers)} papers:\n")
    for i, p in enumerate(papers, 1):
        print(f"  {i}. [{p.arxiv_id}] {p.title[:80]}")
        print(f"     Authors: {', '.join(p.authors[:3])}")
        print(f"     Categories: {', '.join(p.categories[:3])}")
        print()

    if args.download_only:
        paths = connector.download_papers(papers)
        print(f"Downloaded {len(paths)} PDFs to {args.download_dir}/")
    else:
        stats = connector.download_and_ingest(papers)
        print(f"\nIngestion stats: {json.dumps(stats, indent=2)}")

    # Save metadata
    connector.save_metadata(papers)


if __name__ == "__main__":
    main()
