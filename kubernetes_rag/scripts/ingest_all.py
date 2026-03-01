#!/usr/bin/env python3
"""Comprehensive ingestion script for local and remote technical corpora.

Usage:
    # Ingest everything (local + remote sources)
    python -m scripts.ingest_all

    # Local files only (skip GitHub fetch)
    python -m scripts.ingest_all --local-only

    # Remote fetch only (skip local)
    python -m scripts.ingest_all --github-only

    # Increase max PDFs per repo
    python -m scripts.ingest_all --max-per-repo 10
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ingestion.pipeline import create_ingestion_pipeline
from src.utils.config_loader import get_config
from src.utils.logger import get_logger, setup_logger


def ingest_local(pipeline, data_dir: Path) -> dict:
    """Ingest all local files into the vector DB."""
    stats = {
        "arxiv_papers": {"files": 0, "chunks": 0},
        "devops_exercises": {"files": 0, "chunks": 0},
        "sample_docs": {"files": 0, "chunks": 0},
        "runbooks": {"files": 0, "chunks": 0},
        "incidents": {"files": 0, "chunks": 0},
        "configs": {"files": 0, "chunks": 0},
        "github_pdfs_local": {"files": 0, "chunks": 0},
    }

    # 1. arXiv papers
    arxiv_dir = data_dir / "arxiv_papers"
    if arxiv_dir.exists():
        logger.info("=== Ingesting arXiv papers ===")
        for pdf in sorted(arxiv_dir.glob("*.pdf")):
            try:
                n = pipeline.ingest_file(pdf)
                stats["arxiv_papers"]["files"] += 1
                stats["arxiv_papers"]["chunks"] += n
                logger.info(f"  {pdf.name}: {n} chunks")
            except Exception as e:
                logger.error(f"  FAILED {pdf.name}: {e}")

    # 2. Sample docs
    sample_dir = data_dir / "sample_docs"
    if sample_dir.exists():
        logger.info("=== Ingesting sample docs ===")
        for f in sorted(sample_dir.iterdir()):
            if f.suffix.lower() in {".md", ".txt", ".pdf"}:
                try:
                    n = pipeline.ingest_file(f)
                    stats["sample_docs"]["files"] += 1
                    stats["sample_docs"]["chunks"] += n
                    logger.info(f"  {f.name}: {n} chunks")
                except Exception as e:
                    logger.error(f"  FAILED {f.name}: {e}")

    # 3. DevOps exercises (markdown files in topics/ subdirectory)
    exercises_dir = data_dir / "devops_exercises"
    topics_dir = exercises_dir / "topics"
    if topics_dir.exists():
        logger.info("=== Ingesting devops_exercises/topics ===")
        md_files = sorted(topics_dir.rglob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files")
        for f in md_files:
            try:
                n = pipeline.ingest_file(f)
                stats["devops_exercises"]["files"] += 1
                stats["devops_exercises"]["chunks"] += n
            except Exception as e:
                logger.error(f"  FAILED {f.name}: {e}")
        logger.info(
            f"  DevOps exercises: {stats['devops_exercises']['files']} files, "
            f"{stats['devops_exercises']['chunks']} chunks"
        )

    # 4. Already-downloaded GitHub PDFs
    github_dir = data_dir / "github_pdfs"
    if github_dir.exists():
        logger.info("=== Ingesting existing GitHub PDFs ===")
        pdfs = sorted(github_dir.rglob("*.pdf"))
        logger.info(f"Found {len(pdfs)} local GitHub PDFs")
        for pdf in pdfs:
            try:
                n = pipeline.ingest_file(pdf)
                stats["github_pdfs_local"]["files"] += 1
                stats["github_pdfs_local"]["chunks"] += n
                logger.info(f"  {pdf.name}: {n} chunks")
            except Exception as e:
                logger.error(f"  FAILED {pdf.name}: {e}")

    # 5. Internal runbooks
    runbooks_dir = data_dir / "runbooks"
    if runbooks_dir.exists():
        logger.info("=== Ingesting runbooks ===")
        files = sorted(
            f for f in runbooks_dir.rglob("*")
            if f.suffix.lower() in {".md", ".markdown", ".txt", ".pdf"}
        )
        logger.info(f"Found {len(files)} runbook files")
        for f in files:
            try:
                n = pipeline.ingest_file(f, source_type="runbook")
                stats["runbooks"]["files"] += 1
                stats["runbooks"]["chunks"] += n
            except Exception as e:
                logger.error(f"  FAILED {f.name}: {e}")

    # 6. Incident timelines
    incidents_dir = data_dir / "incidents"
    if incidents_dir.exists():
        logger.info("=== Ingesting incidents ===")
        files = sorted(
            f for f in incidents_dir.rglob("*")
            if f.suffix.lower() in {".md", ".markdown", ".txt", ".pdf"}
        )
        logger.info(f"Found {len(files)} incident files")
        for f in files:
            try:
                n = pipeline.ingest_file(f, source_type="incident")
                stats["incidents"]["files"] += 1
                stats["incidents"]["chunks"] += n
            except Exception as e:
                logger.error(f"  FAILED {f.name}: {e}")

    # 7. Config references
    configs_dir = data_dir / "configs"
    if configs_dir.exists():
        logger.info("=== Ingesting configs ===")
        files = sorted(
            f for f in configs_dir.rglob("*")
            if f.suffix.lower() in {".yaml", ".yml", ".json", ".conf", ".ini", ".txt", ".md"}
        )
        logger.info(f"Found {len(files)} config files")
        for f in files:
            try:
                n = pipeline.ingest_file(f, source_type="config")
                stats["configs"]["files"] += 1
                stats["configs"]["chunks"] += n
            except Exception as e:
                logger.error(f"  FAILED {f.name}: {e}")

    return stats


def fetch_and_ingest_github_pdfs(pipeline, data_dir: Path, max_per_repo: int = 5) -> dict:
    """Fetch PDFs from manjunath5496 GitHub repos and ingest them."""
    from src.connectors.github_pdf_connector import GitHubPDFConnector

    logger.info("=== Fetching + ingesting from manjunath5496 GitHub repos ===")

    connector = GitHubPDFConnector(
        download_dir=str(data_dir / "github_pdfs"),
        rate_limit_seconds=1.5,  # be gentle with GitHub API
        max_file_size_mb=50.0,
    )

    stats = connector.fetch_and_ingest(
        repos=None,  # use DEFAULT_REPOS
        owner="manjunath5496",
        max_per_repo=max_per_repo,
        pipeline=pipeline,
    )

    # Save knowledge graph
    connector.save_knowledge_graph()

    return stats


def fetch_and_ingest_devops_exercises(pipeline, data_dir: Path) -> dict:
    """Clone/pull devops-exercises and ingest all available topics."""
    from src.connectors.devops_exercises_connector import DevOpsExercisesConnector

    connector = DevOpsExercisesConnector(clone_dir=str(data_dir / "devops_exercises"))
    connector.clone_or_pull()
    topics = connector.list_available_topics()
    stats = connector.fetch_and_ingest(topics=topics, pipeline=pipeline)
    stats["topics"] = topics
    return stats


def fetch_and_ingest_system_design(pipeline, data_dir: Path) -> dict:
    """Clone/pull system-design repository and ingest all supported files."""
    from src.connectors.system_design_connector import SystemDesignConnector

    connector = SystemDesignConnector(clone_dir=str(data_dir / "system_design"))
    return connector.fetch_and_ingest(pipeline=pipeline)


def main():
    parser = argparse.ArgumentParser(description="Ingest all data into RAG vector DB")
    parser.add_argument("--local-only", action="store_true", help="Only ingest local files")
    parser.add_argument("--github-only", action="store_true", help="Only fetch+ingest from GitHub")
    parser.add_argument("--max-per-repo", type=int, default=5, help="Max PDFs per GitHub repo")
    parser.add_argument(
        "--skip-system-design",
        action="store_true",
        help="Skip ingesting the system-design repository",
    )
    parser.add_argument(
        "--skip-devops-refresh",
        action="store_true",
        help="Skip refreshing and ingesting all DevOps-Exercises topics",
    )
    args = parser.parse_args()

    setup_logger()
    global logger
    logger = get_logger()

    config, _ = get_config()
    pipeline = create_ingestion_pipeline(config)
    data_dir = ROOT / "data"

    t0 = time.time()
    total_chunks = 0

    if not args.github_only:
        logger.info("Phase 1: Ingesting local files")
        local_stats = ingest_local(pipeline, data_dir)
        for category, s in local_stats.items():
            logger.info(f"  {category}: {s['files']} files → {s['chunks']} chunks")
            total_chunks += s["chunks"]

    if not args.local_only:
        logger.info(f"Phase 2A: Fetching from manjunath5496 (max {args.max_per_repo}/repo)")
        gh_stats = fetch_and_ingest_github_pdfs(pipeline, data_dir, args.max_per_repo)
        logger.info(f"  GitHub PDFs: {gh_stats['total_ingested']} files → {gh_stats['total_chunks']} chunks")
        total_chunks += gh_stats.get("total_chunks", 0)

        if not args.skip_devops_refresh:
            logger.info("Phase 2B: Refreshing DevOps-Exercises all topics")
            devops_stats = fetch_and_ingest_devops_exercises(pipeline, data_dir)
            logger.info(
                "  DevOps Exercises: "
                f"{devops_stats['total_files']} files → {devops_stats['total_chunks']} chunks"
            )
            total_chunks += devops_stats.get("total_chunks", 0)

        if not args.skip_system_design:
            logger.info("Phase 2C: Ingesting system-design repository")
            sd_stats = fetch_and_ingest_system_design(pipeline, data_dir)
            logger.info(
                "  System Design: "
                f"{sd_stats['processed_files']}/{sd_stats['total_files']} files → "
                f"{sd_stats['total_chunks']} chunks"
            )
            total_chunks += sd_stats.get("total_chunks", 0)

    elapsed = time.time() - t0
    logger.info(f"\n{'='*50}")
    logger.info(f"DONE — {total_chunks} total chunks ingested in {elapsed:.0f}s")


if __name__ == "__main__":
    main()
