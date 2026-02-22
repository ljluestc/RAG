"""Slack bot for the RAG system.

Listens for messages/mentions in Slack, queries the RAG system,
and returns answers with citation grounding.

Setup:
    1. Create a Slack app at https://api.slack.com/apps
    2. Enable Socket Mode and Event Subscriptions
    3. Subscribe to: message.channels, message.im, app_mention
    4. Add bot scopes: chat:write, app_mentions:read, channels:history, im:history
    5. Set env vars:
       - SLACK_BOT_TOKEN: xoxb-... Bot User OAuth Token
       - SLACK_APP_TOKEN: xapp-... App-Level Token (for Socket Mode)

Run:
    TESTING=true python -m src.bots.slack_bot
"""

import os
import sys
from pathlib import Path

from ..utils.logger import get_logger, setup_logger

logger = get_logger()


def create_rag_query_handler():
    """Create a handler function that queries the RAG system."""
    from ..generation.llm import create_rag_generator
    from ..retrieval.retriever import create_retriever
    from ..utils.config_loader import load_config

    config = load_config()
    retriever = create_retriever(config)
    generator = create_rag_generator(config)

    def query_rag(question: str, top_k: int = 5) -> dict:
        """Query RAG and return answer with citations."""
        results = retriever.retrieve(question, top_k=top_k)
        if not results:
            return {
                "answer": "I couldn't find any relevant documents for your question.",
                "citations": [],
                "num_sources": 0,
            }

        answer_data = generator.generate_answer(question, results)
        return answer_data

    return query_rag


def format_slack_response(answer_data: dict) -> str:
    """Format RAG response for Slack with citations."""
    text = answer_data["answer"]

    citations = answer_data.get("citations", [])
    if citations:
        text += "\n\n*Sources:*\n"
        for c in citations[:5]:  # Limit to top 5 citations
            source_info = f"`{c['filename']}`"
            if c.get("page_number"):
                source_info += f" (p.{c['page_number']})"
            if c.get("section_title"):
                source_info += f" — _{c['section_title']}_"
            score = c.get("relevance_score", 0)
            text += f"• {source_info} (relevance: {score:.2f})\n"

    return text


def create_slack_app():
    """Create and configure the Slack Bolt app."""
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not bot_token or not app_token:
        logger.error(
            "Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN environment variables. "
            "See docstring for setup instructions."
        )
        sys.exit(1)

    app = App(token=bot_token)
    query_rag = create_rag_query_handler()

    @app.event("app_mention")
    def handle_mention(event, say):
        """Handle @bot mentions in channels."""
        text = event.get("text", "")
        user = event.get("user", "")

        # Strip the bot mention from the text
        # Slack sends <@BOT_ID> text
        import re
        question = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()

        if not question:
            say(f"<@{user}> Please ask me a question! For example: `@bot What is a Kubernetes Pod?`")
            return

        logger.info(f"Slack mention from {user}: {question}")
        say(f"<@{user}> Searching... :mag:")

        answer_data = query_rag(question)
        response = format_slack_response(answer_data)
        say(f"<@{user}>\n{response}")

    @app.event("message")
    def handle_dm(event, say):
        """Handle direct messages to the bot."""
        # Skip bot's own messages
        if event.get("bot_id"):
            return

        text = event.get("text", "").strip()
        if not text:
            return

        # Skip if this is a channel message (not DM)
        channel_type = event.get("channel_type", "")
        if channel_type != "im":
            return

        logger.info(f"Slack DM: {text}")
        answer_data = query_rag(text)
        response = format_slack_response(answer_data)
        say(response)

    return app, app_token


def main():
    """Run the Slack bot."""
    setup_logger()
    logger.info("Starting Slack RAG bot...")

    app, app_token = create_slack_app()

    from slack_bolt.adapter.socket_mode import SocketModeHandler

    handler = SocketModeHandler(app, app_token)
    logger.info("Slack bot is running! Press Ctrl+C to stop.")
    handler.start()


if __name__ == "__main__":
    main()
