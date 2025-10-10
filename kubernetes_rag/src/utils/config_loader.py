"""Configuration loader for the Kubernetes RAG system."""

import yaml
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    model_name: str
    embedding_dim: int
    batch_size: int


class VectorDBConfig(BaseModel):
    """Vector database configuration."""
    type: str
    persist_directory: str
    collection_name: str
    distance_metric: str


class DocumentProcessingConfig(BaseModel):
    """Document processing configuration."""
    chunk_size: int
    chunk_overlap: int
    separators: list[str]


class RetrievalConfig(BaseModel):
    """Retrieval configuration."""
    top_k: int
    score_threshold: float
    rerank: bool
    rerank_top_k: int


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    local_model_path: str | None = None


class APIConfig(BaseModel):
    """API configuration."""
    host: str
    port: int
    reload: bool


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str
    format: str


class PathsConfig(BaseModel):
    """Paths configuration."""
    raw_data: str
    processed_data: str
    vector_db: str


class Config(BaseModel):
    """Main configuration class."""
    embedding: EmbeddingConfig
    vector_db: VectorDBConfig
    document_processing: DocumentProcessingConfig
    retrieval: RetrievalConfig
    llm: LLMConfig
    api: APIConfig
    logging: LoggingConfig
    paths: PathsConfig


class Settings(BaseSettings):
    """Environment settings."""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "gpt-3.5-turbo"
    vector_db_path: str = "./data/vector_db"
    collection_name: str = "kubernetes_docs"
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load configuration from YAML file."""
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        config_dict = yaml.safe_load(f)

    return Config(**config_dict)


def load_env_settings() -> Settings:
    """Load environment settings."""
    load_dotenv()
    return Settings()


def get_config() -> tuple[Config, Settings]:
    """Get both configuration and settings."""
    config = load_config()
    settings = load_env_settings()
    return config, settings
