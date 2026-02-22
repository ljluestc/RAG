"""Application configuration using Pydantic settings."""

from __future__ import annotations

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All application settings, loaded from env vars / .env."""

    # --- API ---
    app_name: str = "ChatGPT RAG"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # --- LLM providers ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_provider: str = "openai"  # openai | anthropic | local
    default_model: str = "gpt-4o-mini"

    # --- Rate limiting ---
    rate_limit_rpm: int = 60  # requests per minute per user
    rate_limit_tpm: int = 100_000  # tokens per minute per user

    # --- PostgreSQL (Phase 2) ---
    database_url: str = "postgresql+asyncpg://chatgpt:chatgpt@localhost:5432/chatgpt"

    # --- Redis (Phase 4) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Kafka (Phase 4) ---
    kafka_bootstrap: str = "localhost:9092"

    # --- RAG (reuse parent project) ---
    rag_config_path: str = "../../config/config.yaml"

    # --- Embedding worker ---
    embedding_queue_size: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
