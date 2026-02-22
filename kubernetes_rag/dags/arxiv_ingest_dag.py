"""Airflow DAG: arXiv paper ingestion pipeline.

Schedules periodic fetching of arXiv papers and ingestion into the RAG system.

Setup:
    1. Set AIRFLOW_HOME or copy this file to your Airflow dags/ folder
    2. Configure variables in Airflow UI or env:
       - ARXIV_QUERY: search query (default: "retrieval augmented generation")
       - ARXIV_MAX_RESULTS: max papers per run (default: 5)
       - ARXIV_CATEGORIES: comma-separated categories (default: "cs.IR,cs.CL,cs.AI")
    3. Set PYTHONPATH to include the kubernetes_rag directory
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Ensure the project is importable
PROJECT_ROOT = os.environ.get(
    "RAG_PROJECT_ROOT",
    str(Path(__file__).resolve().parent.parent),
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Default DAG arguments
default_args = {
    "owner": "rag-pipeline",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def search_arxiv(**context):
    """Task: Search arXiv for papers."""
    from src.connectors.arxiv_connector import ArxivConnector

    query = os.environ.get("ARXIV_QUERY", "retrieval augmented generation")
    max_results = int(os.environ.get("ARXIV_MAX_RESULTS", "5"))
    categories_str = os.environ.get("ARXIV_CATEGORIES", "cs.IR,cs.CL,cs.AI")
    categories = [c.strip() for c in categories_str.split(",") if c.strip()]

    connector = ArxivConnector(download_dir=os.path.join(PROJECT_ROOT, "data/arxiv_papers"))
    papers = connector.search(query, max_results=max_results, categories=categories)

    # Push paper data to XCom for downstream tasks
    paper_dicts = [p.to_dict() for p in papers]
    context["ti"].xcom_push(key="papers", value=json.dumps(paper_dicts))
    print(f"Found {len(papers)} papers for query: '{query}'")
    return len(papers)


def download_pdfs(**context):
    """Task: Download PDFs for discovered papers."""
    from src.connectors.arxiv_connector import ArxivConnector, ArxivPaper

    papers_json = context["ti"].xcom_pull(key="papers", task_ids="search_arxiv")
    if not papers_json:
        print("No papers to download")
        return 0

    paper_dicts = json.loads(papers_json)
    papers = [ArxivPaper(**d) for d in paper_dicts]

    connector = ArxivConnector(download_dir=os.path.join(PROJECT_ROOT, "data/arxiv_papers"))
    paths = connector.download_papers(papers)

    # Update papers with local paths and push back
    updated = [p.to_dict() for p in papers]
    context["ti"].xcom_push(key="downloaded_papers", value=json.dumps(updated))
    print(f"Downloaded {len(paths)} PDFs")
    return len(paths)


def ingest_papers(**context):
    """Task: Ingest downloaded PDFs into the RAG vector store."""
    from src.connectors.arxiv_connector import ArxivConnector, ArxivPaper

    papers_json = context["ti"].xcom_pull(key="downloaded_papers", task_ids="download_pdfs")
    if not papers_json:
        print("No papers to ingest")
        return 0

    paper_dicts = json.loads(papers_json)
    papers = [ArxivPaper(**d) for d in paper_dicts]

    connector = ArxivConnector(download_dir=os.path.join(PROJECT_ROOT, "data/arxiv_papers"))
    stats = connector.download_and_ingest(papers)

    # Save metadata
    connector.save_metadata(papers)

    context["ti"].xcom_push(key="ingest_stats", value=json.dumps(stats))
    print(f"Ingestion stats: {json.dumps(stats, indent=2)}")
    return stats["total_chunks"]


def report_results(**context):
    """Task: Log final pipeline results."""
    stats_json = context["ti"].xcom_pull(key="ingest_stats", task_ids="ingest_papers")
    if stats_json:
        stats = json.loads(stats_json)
        print("=" * 60)
        print("arXiv Ingestion Pipeline Complete")
        print(f"  Papers processed: {stats['total_papers']}")
        print(f"  Downloaded: {stats['downloaded']}")
        print(f"  Ingested: {stats['ingested']}")
        print(f"  Total chunks: {stats['total_chunks']}")
        if stats["failed"]:
            print(f"  Failed: {len(stats['failed'])}")
            for f in stats["failed"]:
                print(f"    - {f['arxiv_id']}: {f['error']}")
        print("=" * 60)
    else:
        print("No ingestion stats available")


# Define the DAG
with DAG(
    dag_id="arxiv_rag_ingestion",
    default_args=default_args,
    description="Fetch arXiv papers and ingest into RAG system",
    schedule_interval=timedelta(days=1),  # Daily
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["rag", "arxiv", "ingestion"],
) as dag:

    t_search = PythonOperator(
        task_id="search_arxiv",
        python_callable=search_arxiv,
    )

    t_download = PythonOperator(
        task_id="download_pdfs",
        python_callable=download_pdfs,
    )

    t_ingest = PythonOperator(
        task_id="ingest_papers",
        python_callable=ingest_papers,
    )

    t_report = PythonOperator(
        task_id="report_results",
        python_callable=report_results,
    )

    t_search >> t_download >> t_ingest >> t_report
