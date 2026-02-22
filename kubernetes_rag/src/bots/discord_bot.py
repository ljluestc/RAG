"""Discord bot for the RAG system.

Listens for messages in Discord, queries the RAG system,
and returns answers with citation grounding.

Setup:
    1. Create a Discord app at https://discord.com/developers/applications
    2. Create a Bot under the application
    3. Enable MESSAGE CONTENT intent in the Bot settings
    4. Generate an invite URL with bot + applications.commands scopes
       and Send Messages, Read Message History permissions
    5. Set env var:
       - DISCORD_BOT_TOKEN: Your bot token

Run:
    TESTING=true python -m src.bots.discord_bot

The bot responds to:
    - !ask <question>  — Query the RAG system
    - !search <query>  — Search without generating an answer
    - !help            — Show available commands
"""

import os
import sys

import discord
from discord.ext import commands

from ..utils.logger import get_logger, setup_logger

logger = get_logger()


def create_rag_components():
    """Initialize RAG retriever and generator."""
    from ..generation.llm import create_rag_generator
    from ..retrieval.retriever import create_retriever
    from ..utils.config_loader import load_config

    config = load_config()
    retriever = create_retriever(config)
    generator = create_rag_generator(config)
    return retriever, generator


def format_discord_response(answer_data: dict) -> str:
    """Format RAG response for Discord with citations."""
    text = answer_data["answer"]

    citations = answer_data.get("citations", [])
    if citations:
        text += "\n\n**Sources:**\n"
        for c in citations[:5]:
            source_info = f"`{c['filename']}`"
            if c.get("page_number"):
                source_info += f" (p.{c['page_number']})"
            if c.get("section_title"):
                source_info += f" — *{c['section_title']}*"
            score = c.get("relevance_score", 0)
            text += f"• {source_info} (relevance: {score:.2f})\n"

    return text


def format_search_results(results: list) -> str:
    """Format search results for Discord."""
    if not results:
        return "No results found."

    text = f"**Found {len(results)} results:**\n\n"
    for i, r in enumerate(results[:5], 1):
        score = r.get("score", 0)
        meta = r.get("metadata", {})
        preview = r["content"][:150].replace("\n", " ")
        source = meta.get("filename", "unknown")
        text += f"**{i}.** `{source}` (score: {score:.3f})\n{preview}...\n\n"

    return text


def create_bot():
    """Create and configure the Discord bot."""
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    retriever = None
    generator = None

    @bot.event
    async def on_ready():
        nonlocal retriever, generator
        logger.info(f"Discord bot connected as {bot.user}")
        retriever, generator = create_rag_components()
        logger.info("RAG components initialized")

    @bot.command(name="ask")
    async def ask_command(ctx, *, question: str):
        """Ask a question to the RAG system."""
        logger.info(f"Discord ask from {ctx.author}: {question}")
        await ctx.send(f":mag: Searching for: *{question}*...")

        results = retriever.retrieve(question, top_k=5)
        if not results:
            await ctx.send("I couldn't find any relevant documents for your question.")
            return

        answer_data = generator.generate_answer(question, results)
        response = format_discord_response(answer_data)

        # Discord has a 2000 char limit
        if len(response) > 1900:
            # Split into chunks
            for i in range(0, len(response), 1900):
                await ctx.send(response[i : i + 1900])
        else:
            await ctx.send(response)

    @bot.command(name="search")
    async def search_command(ctx, *, query: str):
        """Search documents without generating an answer."""
        logger.info(f"Discord search from {ctx.author}: {query}")

        results = retriever.retrieve(query, top_k=5)
        response = format_search_results(results)

        if len(response) > 1900:
            for i in range(0, len(response), 1900):
                await ctx.send(response[i : i + 1900])
        else:
            await ctx.send(response)

    @bot.command(name="help")
    async def help_command(ctx):
        """Show available commands."""
        help_text = (
            "**RAG Bot Commands:**\n"
            "`!ask <question>` — Ask a question (retrieval + answer generation)\n"
            "`!search <query>` — Search documents (no answer generation)\n"
            "`!help` — Show this help message\n"
            "\n**Examples:**\n"
            "`!ask What is a Kubernetes Pod?`\n"
            "`!search Docker networking bridge`\n"
        )
        await ctx.send(help_text)

    return bot


def main():
    """Run the Discord bot."""
    setup_logger()

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        logger.error(
            "Missing DISCORD_BOT_TOKEN environment variable. "
            "See docstring for setup instructions."
        )
        sys.exit(1)

    logger.info("Starting Discord RAG bot...")
    bot = create_bot()
    bot.run(token)


if __name__ == "__main__":
    main()
