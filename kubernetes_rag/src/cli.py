"""Command-line interface for Kubernetes RAG system."""

import sys
from pathlib import Path

import click

from .generation.llm import create_rag_generator
from .ingestion.pipeline import create_ingestion_pipeline
from .retrieval.retriever import create_retriever
from .utils.config_loader import get_config
from .utils.logger import setup_logger


@click.group()
@click.option("--config", default="config/config.yaml", help="Path to config file")
@click.option("--log-level", default="INFO", help="Logging level")
@click.pass_context
def cli(ctx, config, log_level):
    """Kubernetes RAG System CLI."""
    ctx.ensure_object(dict)

    # Setup logger
    setup_logger(log_level=log_level)

    # Load configuration
    try:
        config_obj, settings = get_config()
        ctx.obj["config"] = config_obj
        ctx.obj["settings"] = settings
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--file-pattern", default="*.md", help="File pattern to match")
@click.pass_context
def ingest(ctx, source, file_pattern):
    """Ingest documents into the RAG system."""
    config = ctx.obj["config"]

    click.echo(f"Starting ingestion from: {source}")

    # Create ingestion pipeline
    pipeline = create_ingestion_pipeline(config)

    # Ingest
    source_path = Path(source)

    if source_path.is_file():
        num_chunks = pipeline.ingest_file(source_path)
        click.echo(f"✓ Ingested {num_chunks} chunks from file")
    else:
        stats = pipeline.ingest_directory(source_path, file_pattern)
        click.echo(f"✓ Ingestion complete!")
        click.echo(
            f"  Files processed: {stats['processed_files']}/{stats['total_files']}"
        )
        click.echo(f"  Total chunks: {stats['total_chunks']}")

        if stats["failed_files"]:
            click.echo(f"  Failed files: {len(stats['failed_files'])}")


@cli.command()
@click.argument("query")
@click.option("--top-k", default=5, help="Number of results to retrieve")
@click.option(
    "--no-generate", is_flag=True, help="Only retrieve, do not generate answer"
)
@click.pass_context
def query(ctx, query, top_k, no_generate):
    """Query the RAG system."""
    config = ctx.obj["config"]

    click.echo(f"Query: {query}\n")

    # Create retriever
    retriever = create_retriever(config)

    # Retrieve documents
    with click.progressbar(length=1, label="Retrieving documents") as bar:
        results = retriever.retrieve(query, top_k=top_k)
        bar.update(1)

    if not results:
        click.echo("No relevant documents found.")
        return

    # Display retrieved documents
    click.echo(f"\n📚 Retrieved {len(results)} relevant documents:\n")

    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        content_preview = (
            result["content"][:150] + "..."
            if len(result["content"]) > 150
            else result["content"]
        )

        click.echo(f"{i}. [Score: {score:.3f}]")
        click.echo(f"   {content_preview}")
        click.echo()

    # Generate answer if requested
    if not no_generate:
        click.echo("Generating answer...\n")

        generator = create_rag_generator(config)

        answer_data = generator.generate_answer(
            query,
            results,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        click.echo("=" * 80)
        click.echo("ANSWER:")
        click.echo("=" * 80)
        click.echo(answer_data["answer"])
        click.echo("=" * 80)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive query mode."""
    config = ctx.obj["config"]

    click.echo("🚀 Kubernetes RAG - Interactive Mode")
    click.echo("Type 'exit' or 'quit' to end the session\n")

    # Create components
    retriever = create_retriever(config)
    generator = create_rag_generator(config)

    conversation_history = []

    while True:
        query_text = click.prompt("Your question", type=str)

        if query_text.lower() in ["exit", "quit"]:
            click.echo("Goodbye!")
            break

        # Retrieve
        results = retriever.retrieve(query_text, top_k=config.retrieval.top_k)

        if not results:
            click.echo("❌ No relevant documents found.\n")
            continue

        # Generate
        answer_data = generator.generate_with_followup(
            query_text, results, conversation_history
        )

        conversation_history = answer_data["conversation_history"]

        # Display answer
        click.echo(f"\n💡 Answer:")
        click.echo("-" * 80)
        click.echo(answer_data["answer"])
        click.echo("-" * 80 + "\n")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show RAG system statistics."""
    config = ctx.obj["config"]

    from .retrieval.vector_store import VectorStore

    vector_store = VectorStore(
        collection_name=config.vector_db.collection_name,
        persist_directory=config.vector_db.persist_directory,
    )

    stats = vector_store.get_collection_stats()

    click.echo("📊 RAG System Statistics")
    click.echo("=" * 50)
    click.echo(f"Collection: {stats['name']}")
    click.echo(f"Documents: {stats['count']}")
    click.echo(f"Storage: {stats['persist_directory']}")
    click.echo("=" * 50)


@cli.command()
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def reset(ctx, yes):
    """Reset the vector database (delete all data)."""
    config = ctx.obj["config"]

    if not yes:
        if not click.confirm("⚠️  This will delete all ingested data. Continue?"):
            click.echo("Cancelled.")
            return

    from .retrieval.vector_store import VectorStore

    vector_store = VectorStore(
        collection_name=config.vector_db.collection_name,
        persist_directory=config.vector_db.persist_directory,
    )

    vector_store.delete_collection()
    click.echo("✓ Vector database reset complete")


@cli.command()
@click.argument("query")
@click.option("--category", help="Filter by category (qa_pair, kubernetes_doc)")
@click.option("--top-k", default=5, help="Number of results")
@click.pass_context
def search(ctx, query, category, top_k):
    """Search for documents without generating an answer."""
    config = ctx.obj["config"]
    retriever = create_retriever(config)

    click.echo(f"🔍 Searching for: {query}\n")

    if category:
        results = retriever.retrieve_by_category(query, category, top_k)
    else:
        results = retriever.retrieve(query, top_k=top_k)

    if not results:
        click.echo("No results found.")
        return

    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        metadata = result.get("metadata", {})

        click.echo(f"\n{i}. Score: {score:.3f}")
        click.echo(f"   Type: {metadata.get('type', 'unknown')}")
        click.echo(f"   Source: {metadata.get('source', 'unknown')}")
        click.echo(f"   Content: {result['content'][:200]}...")


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
