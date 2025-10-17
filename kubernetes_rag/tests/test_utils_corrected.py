import pytest
from unittest.mock import patch, mock_open, Mock
from pathlib import Path
import os
import yaml

from src.utils.config_loader import load_config, load_env_settings, get_config, Config, Settings, EmbeddingConfig, VectorDBConfig, DocumentProcessingConfig, RetrievalConfig, LLMConfig, APIConfig, LoggingConfig, PathsConfig

# Fixture for a temporary config file
@pytest.fixture
def temp_config_file(tmp_path):
    config_data = {
        "embedding": {"model_name": "test-embed", "embedding_dim": 768, "batch_size": 32},
        "vector_db": {"type": "chroma", "persist_directory": "/tmp/test_db", "collection_name": "test_col", "distance_metric": "cosine"},
        "document_processing": {"chunk_size": 500, "chunk_overlap": 100, "separators": ["\n\n", "\n"]},
        "retrieval": {"top_k": 3, "score_threshold": 0.8, "rerank": False, "rerank_top_k": 2},
        "llm": {"provider": "openai", "model_name": "gpt-test", "temperature": 0.5, "max_tokens": 500, "local_model_path": None},
        "api": {"host": "127.0.0.1", "port": 8080, "reload": True},
        "logging": {"level": "DEBUG", "format": "{message}"},
        "paths": {"raw_data": "./data/raw", "processed_data": "./data/processed", "vector_db": "./data/vector_db"},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    return config_path

# Test for load_config
def test_load_config(temp_config_file):
    config = load_config(str(temp_config_file))
    assert isinstance(config, Config)
    assert config.embedding.model_name == "test-embed"
    assert config.api.port == 8080

def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")

def test_load_config_invalid_yaml(tmp_path):
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("invalid: yaml: content: [")
    
    with pytest.raises(yaml.YAMLError):
        load_config(str(config_path))

# Test for load_env_settings
def test_load_env_settings():
    os.environ["OPENAI_API_KEY"] = "env_openai_key"
    os.environ["LLM_MODEL"] = "env_llm_model"
    os.environ["DEBUG"] = "true"
    
    settings = load_env_settings()
    assert isinstance(settings, Settings)
    assert settings.openai_api_key == "env_openai_key"
    assert settings.llm_model == "env_llm_model"
    assert settings.debug is True
    
    del os.environ["OPENAI_API_KEY"]
    del os.environ["LLM_MODEL"]
    del os.environ["DEBUG"]

def test_load_env_settings_defaults():
    # Clear environment variables
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "EMBEDDING_MODEL", "LLM_MODEL", "VECTOR_DB_PATH", "COLLECTION_NAME", "DEBUG", "LOG_LEVEL"]:
        if key in os.environ:
            del os.environ[key]
    
    settings = load_env_settings()
    assert settings.openai_api_key == ""
    assert settings.anthropic_api_key == ""
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.llm_model == "gpt-3.5-turbo"
    assert settings.vector_db_path == "./data/vector_db"
    assert settings.collection_name == "kubernetes_docs"
    assert settings.debug is False
    assert settings.log_level == "INFO"

def test_load_env_settings_boolean_parsing():
    os.environ["DEBUG"] = "true"
    settings = load_env_settings()
    assert settings.debug is True
    
    os.environ["DEBUG"] = "false"
    settings = load_env_settings()
    assert settings.debug is False
    
    del os.environ["DEBUG"]

def test_load_env_settings_invalid_boolean():
    os.environ["DEBUG"] = "invalid"
    with pytest.raises(Exception):  # Pydantic validation error
        load_env_settings()
    del os.environ["DEBUG"]

# Test for get_config
def test_get_config_success(temp_config_file):
    with patch("src.utils.config_loader.load_config") as mock_load_config, \
         patch("src.utils.config_loader.load_env_settings") as mock_load_env_settings:
        
        mock_config = Mock()
        mock_settings = Mock()
        mock_load_config.return_value = mock_config
        mock_load_env_settings.return_value = mock_settings
        
        config, settings = get_config()
        
        mock_load_config.assert_called_once()
        mock_load_env_settings.assert_called_once()
        assert config == mock_config
        assert settings == mock_settings

def test_get_config_file_error():
    with patch("src.utils.config_loader.load_config") as mock_load_config:
        mock_load_config.side_effect = FileNotFoundError("Config file not found")
        
        with pytest.raises(FileNotFoundError):
            get_config()

# Test individual config classes
def test_embedding_config_creation():
    config = EmbeddingConfig(
        model_name="test-model",
        embedding_dim=768,
        batch_size=32
    )
    assert config.model_name == "test-model"
    assert config.embedding_dim == 768
    assert config.batch_size == 32

def test_embedding_config_validation():
    with pytest.raises(Exception):  # Pydantic validation error
        EmbeddingConfig(model_name="test")  # Missing required fields

def test_vector_db_config_creation():
    config = VectorDBConfig(
        type="chroma",
        persist_directory="/tmp/test",
        collection_name="test_col",
        distance_metric="cosine"
    )
    assert config.type == "chroma"
    assert config.persist_directory == "/tmp/test"
    assert config.collection_name == "test_col"
    assert config.distance_metric == "cosine"

def test_document_processing_config_creation():
    config = DocumentProcessingConfig(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n"]
    )
    assert config.chunk_size == 500
    assert config.chunk_overlap == 100
    assert config.separators == ["\n\n", "\n"]

def test_retrieval_config_creation():
    config = RetrievalConfig(
        top_k=5,
        score_threshold=0.7,
        rerank=True,
        rerank_top_k=3
    )
    assert config.top_k == 5
    assert config.score_threshold == 0.7
    assert config.rerank is True
    assert config.rerank_top_k == 3

def test_llm_config_creation():
    config = LLMConfig(
        provider="openai",
        model_name="gpt-3.5-turbo",
        temperature=0.3,
        max_tokens=1000,
        local_model_path=None
    )
    assert config.provider == "openai"
    assert config.model_name == "gpt-3.5-turbo"
    assert config.temperature == 0.3
    assert config.max_tokens == 1000
    assert config.local_model_path is None

def test_api_config_creation():
    config = APIConfig(
        host="localhost",
        port=8000,
        reload=True
    )
    assert config.host == "localhost"
    assert config.port == 8000
    assert config.reload is True

def test_logging_config_creation():
    config = LoggingConfig(
        level="INFO",
        format="{time} {level} {message}"
    )
    assert config.level == "INFO"
    assert config.format == "{time} {level} {message}"

def test_paths_config_creation():
    config = PathsConfig(
        raw_data="./data/raw",
        processed_data="./data/processed",
        vector_db="./data/vector_db"
    )
    assert config.raw_data == "./data/raw"
    assert config.processed_data == "./data/processed"
    assert config.vector_db == "./data/vector_db"

def test_config_creation():
    config = Config(
        embedding=EmbeddingConfig(model_name="test", embedding_dim=768, batch_size=32),
        vector_db=VectorDBConfig(type="chroma", persist_directory="/tmp", collection_name="test", distance_metric="cosine"),
        document_processing=DocumentProcessingConfig(chunk_size=500, chunk_overlap=100, separators=["\n\n"]),
        retrieval=RetrievalConfig(top_k=5, score_threshold=0.7, rerank=False, rerank_top_k=3),
        llm=LLMConfig(provider="openai", model_name="gpt-3.5-turbo", temperature=0.3, max_tokens=1000),
        api=APIConfig(host="localhost", port=8000, reload=True),
        logging=LoggingConfig(level="INFO", format="{message}"),
        paths=PathsConfig(raw_data="./data/raw", processed_data="./data/processed", vector_db="./data/vector_db")
    )
    assert isinstance(config, Config)
    assert config.embedding.model_name == "test"

def test_settings_creation():
    settings = Settings(
        openai_api_key="test-key",
        anthropic_api_key="test-key",
        embedding_model="test-model",
        llm_model="test-llm",
        vector_db_path="/tmp/test",
        collection_name="test_col",
        debug=True,
        log_level="DEBUG"
    )
    assert settings.openai_api_key == "test-key"
    assert settings.debug is True

def test_settings_defaults():
    # Clear environment variables to test defaults
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "EMBEDDING_MODEL", "LLM_MODEL", "VECTOR_DB_PATH", "COLLECTION_NAME", "DEBUG", "LOG_LEVEL"]:
        if key in os.environ:
            del os.environ[key]
    
    settings = Settings()
    assert settings.openai_api_key == ""
    assert settings.anthropic_api_key == ""
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.llm_model == "gpt-3.5-turbo"
    assert settings.vector_db_path == "./data/vector_db"
    assert settings.collection_name == "kubernetes_docs"
    assert settings.debug is False
    assert settings.log_level == "INFO"

# Edge cases
def test_config_with_none_values():
    config = Config(
        embedding=EmbeddingConfig(model_name="test", embedding_dim=768, batch_size=32),
        vector_db=VectorDBConfig(type="chroma", persist_directory="/tmp", collection_name="test", distance_metric="cosine"),
        document_processing=DocumentProcessingConfig(chunk_size=500, chunk_overlap=100, separators=["\n\n"]),
        retrieval=RetrievalConfig(top_k=5, score_threshold=0.7, rerank=False, rerank_top_k=3),
        llm=LLMConfig(provider="openai", model_name="gpt-3.5-turbo", temperature=0.3, max_tokens=1000, local_model_path=None),
        api=APIConfig(host="localhost", port=8000, reload=True),
        logging=LoggingConfig(level="INFO", format="{message}"),
        paths=PathsConfig(raw_data="./data/raw", processed_data="./data/processed", vector_db="./data/vector_db")
    )
    assert config.llm.local_model_path is None

def test_settings_with_empty_strings():
    settings = Settings(
        openai_api_key="",
        anthropic_api_key="",
        embedding_model="",
        llm_model="",
        vector_db_path="",
        collection_name="",
        debug=False,
        log_level=""
    )
    assert settings.openai_api_key == ""
    assert settings.anthropic_api_key == ""

def test_config_serialization():
    config = Config(
        embedding=EmbeddingConfig(model_name="test", embedding_dim=768, batch_size=32),
        vector_db=VectorDBConfig(type="chroma", persist_directory="/tmp", collection_name="test", distance_metric="cosine"),
        document_processing=DocumentProcessingConfig(chunk_size=500, chunk_overlap=100, separators=["\n\n"]),
        retrieval=RetrievalConfig(top_k=5, score_threshold=0.7, rerank=False, rerank_top_k=3),
        llm=LLMConfig(provider="openai", model_name="gpt-3.5-turbo", temperature=0.3, max_tokens=1000),
        api=APIConfig(host="localhost", port=8000, reload=True),
        logging=LoggingConfig(level="INFO", format="{message}"),
        paths=PathsConfig(raw_data="./data/raw", processed_data="./data/processed", vector_db="./data/vector_db")
    )
    
    # Test that config can be serialized to dict
    config_dict = config.model_dump()
    assert isinstance(config_dict, dict)
    assert "embedding" in config_dict
    assert "vector_db" in config_dict

def test_settings_serialization():
    settings = Settings(
        openai_api_key="test-key",
        anthropic_api_key="test-key",
        embedding_model="test-model",
        llm_model="test-llm",
        vector_db_path="/tmp/test",
        collection_name="test_col",
        debug=True,
        log_level="DEBUG"
    )
    
    # Test that settings can be serialized to dict
    settings_dict = settings.model_dump()
    assert isinstance(settings_dict, dict)
    assert "openai_api_key" in settings_dict
    assert "debug" in settings_dict

def test_config_with_extra_fields():
    # Test that extra fields are ignored
    config_data = {
        "embedding": {"model_name": "test", "embedding_dim": 768, "batch_size": 32},
        "vector_db": {"type": "chroma", "persist_directory": "/tmp", "collection_name": "test", "distance_metric": "cosine"},
        "document_processing": {"chunk_size": 500, "chunk_overlap": 100, "separators": ["\n\n"]},
        "retrieval": {"top_k": 5, "score_threshold": 0.7, "rerank": False, "rerank_top_k": 3},
        "llm": {"provider": "openai", "model_name": "gpt-3.5-turbo", "temperature": 0.3, "max_tokens": 1000},
        "api": {"host": "localhost", "port": 8000, "reload": True},
        "logging": {"level": "INFO", "format": "{message}"},
        "paths": {"raw_data": "./data/raw", "processed_data": "./data/processed", "vector_db": "./data/vector_db"},
        "extra_field": "should_be_ignored"
    }
    
    config = Config(**config_data)
    assert isinstance(config, Config)
    # Extra field should be ignored
    assert not hasattr(config, "extra_field")
