"""Fixed comprehensive test suite for utils module to achieve 100% coverage."""

import os
import sys
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test configuration
from test_config_comprehensive import (
    create_mock_config,
    create_mock_settings,
    TEST_CONFIG_DATA
)

from src.utils.config_loader import (
    Config,
    EmbeddingConfig,
    VectorDBConfig,
    DocumentProcessingConfig,
    RetrievalConfig,
    LLMConfig,
    APIConfig,
    LoggingConfig,
    PathsConfig,
    Settings,
    load_config,
    load_env_settings,
    get_config
)


class TestEmbeddingConfig:
    """Test EmbeddingConfig class."""

    def test_embedding_config_creation(self):
        """Test creating EmbeddingConfig instance."""
        config = EmbeddingConfig(
            model_name="test-model",
            embedding_dim=384,
            batch_size=32
        )
        
        assert config.model_name == "test-model"
        assert config.embedding_dim == 384
        assert config.batch_size == 32

    def test_embedding_config_defaults(self):
        """Test EmbeddingConfig with defaults."""
        config = EmbeddingConfig()
        
        assert config.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.embedding_dim == 384
        assert config.batch_size == 32

    def test_embedding_config_validation(self):
        """Test EmbeddingConfig validation."""
        # Test valid config
        config = EmbeddingConfig(
            model_name="valid-model",
            embedding_dim=512,
            batch_size=64
        )
        assert config.embedding_dim == 512
        
        # Test invalid embedding_dim
        with pytest.raises(ValueError):
            EmbeddingConfig(embedding_dim=-1)
        
        # Test invalid batch_size
        with pytest.raises(ValueError):
            EmbeddingConfig(batch_size=0)


class TestVectorDBConfig:
    """Test VectorDBConfig class."""

    def test_vector_db_config_creation(self):
        """Test creating VectorDBConfig instance."""
        config = VectorDBConfig(
            type="chroma",
            persist_directory="/tmp/test",
            collection_name="test_collection",
            distance_metric="cosine"
        )
        
        assert config.type == "chroma"
        assert config.persist_directory == "/tmp/test"
        assert config.collection_name == "test_collection"
        assert config.distance_metric == "cosine"

    def test_vector_db_config_defaults(self):
        """Test VectorDBConfig with defaults."""
        config = VectorDBConfig()
        
        assert config.type == "chroma"
        assert config.persist_directory == "./data/vector_db"
        assert config.collection_name == "kubernetes_docs"
        assert config.distance_metric == "cosine"

    def test_vector_db_config_validation(self):
        """Test VectorDBConfig validation."""
        # Test valid config
        config = VectorDBConfig(
            type="faiss",
            persist_directory="/tmp/test",
            collection_name="test",
            distance_metric="euclidean"
        )
        assert config.type == "faiss"
        
        # Test invalid type
        with pytest.raises(ValueError):
            VectorDBConfig(type="invalid")
        
        # Test invalid distance_metric
        with pytest.raises(ValueError):
            VectorDBConfig(distance_metric="invalid")


class TestDocumentProcessingConfig:
    """Test DocumentProcessingConfig class."""

    def test_document_processing_config_creation(self):
        """Test creating DocumentProcessingConfig instance."""
        config = DocumentProcessingConfig(
            chunk_size=2000,
            chunk_overlap=400,
            separators=["\n\n", "\n", " ", ""]
        )
        
        assert config.chunk_size == 2000
        assert config.chunk_overlap == 400
        assert config.separators == ["\n\n", "\n", " ", ""]

    def test_document_processing_config_defaults(self):
        """Test DocumentProcessingConfig with defaults."""
        config = DocumentProcessingConfig()
        
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.separators == ["\n\n", "\n", " ", ""]

    def test_document_processing_config_validation(self):
        """Test DocumentProcessingConfig validation."""
        # Test valid config
        config = DocumentProcessingConfig(
            chunk_size=1500,
            chunk_overlap=300,
            separators=["\n", " "]
        )
        assert config.chunk_size == 1500
        
        # Test invalid chunk_size
        with pytest.raises(ValueError):
            DocumentProcessingConfig(chunk_size=0)
        
        # Test invalid chunk_overlap
        with pytest.raises(ValueError):
            DocumentProcessingConfig(chunk_overlap=-1)
        
        # Test chunk_overlap >= chunk_size
        with pytest.raises(ValueError):
            DocumentProcessingConfig(chunk_size=100, chunk_overlap=150)


class TestRetrievalConfig:
    """Test RetrievalConfig class."""

    def test_retrieval_config_creation(self):
        """Test creating RetrievalConfig instance."""
        config = RetrievalConfig(
            top_k=10,
            score_threshold=0.8,
            rerank=True,
            rerank_top_k=5
        )
        
        assert config.top_k == 10
        assert config.score_threshold == 0.8
        assert config.rerank is True
        assert config.rerank_top_k == 5

    def test_retrieval_config_defaults(self):
        """Test RetrievalConfig with defaults."""
        config = RetrievalConfig()
        
        assert config.top_k == 5
        assert config.score_threshold == 0.7
        assert config.rerank is False
        assert config.rerank_top_k == 3

    def test_retrieval_config_validation(self):
        """Test RetrievalConfig validation."""
        # Test valid config
        config = RetrievalConfig(
            top_k=15,
            score_threshold=0.9,
            rerank=True,
            rerank_top_k=8
        )
        assert config.top_k == 15
        
        # Test invalid top_k
        with pytest.raises(ValueError):
            RetrievalConfig(top_k=0)
        
        # Test invalid score_threshold
        with pytest.raises(ValueError):
            RetrievalConfig(score_threshold=1.5)
        
        # Test invalid rerank_top_k
        with pytest.raises(ValueError):
            RetrievalConfig(rerank_top_k=0)


class TestLLMConfig:
    """Test LLMConfig class."""

    def test_llm_config_creation(self):
        """Test creating LLMConfig instance."""
        config = LLMConfig(
            provider="openai",
            model_name="gpt-4",
            temperature=0.5,
            max_tokens=2000,
            local_model_path="/path/to/model"
        )
        
        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000
        assert config.local_model_path == "/path/to/model"

    def test_llm_config_defaults(self):
        """Test LLMConfig with defaults."""
        config = LLMConfig()
        
        assert config.provider == "openai"
        assert config.model_name == "gpt-3.5-turbo"
        assert config.temperature == 0.3
        assert config.max_tokens == 1000
        assert config.local_model_path is None

    def test_llm_config_validation(self):
        """Test LLMConfig validation."""
        # Test valid config
        config = LLMConfig(
            provider="anthropic",
            model_name="claude-3",
            temperature=0.7,
            max_tokens=1500
        )
        assert config.provider == "anthropic"
        
        # Test invalid provider
        with pytest.raises(ValueError):
            LLMConfig(provider="invalid")
        
        # Test invalid temperature
        with pytest.raises(ValueError):
            LLMConfig(temperature=2.0)
        
        # Test invalid max_tokens
        with pytest.raises(ValueError):
            LLMConfig(max_tokens=0)


class TestAPIConfig:
    """Test APIConfig class."""

    def test_api_config_creation(self):
        """Test creating APIConfig instance."""
        config = APIConfig(
            host="127.0.0.1",
            port=9000,
            reload=True
        )
        
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.reload is True

    def test_api_config_defaults(self):
        """Test APIConfig with defaults."""
        config = APIConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.reload is False

    def test_api_config_validation(self):
        """Test APIConfig validation."""
        # Test valid config
        config = APIConfig(host="localhost", port=3000)
        assert config.host == "localhost"
        
        # Test invalid port
        with pytest.raises(ValueError):
            APIConfig(port=0)
        
        # Test invalid port range
        with pytest.raises(ValueError):
            APIConfig(port=70000)


class TestLoggingConfig:
    """Test LoggingConfig class."""

    def test_logging_config_creation(self):
        """Test creating LoggingConfig instance."""
        config = LoggingConfig(
            level="DEBUG",
            format="{time} {level} {message} {file}"
        )
        
        assert config.level == "DEBUG"
        assert config.format == "{time} {level} {message} {file}"

    def test_logging_config_defaults(self):
        """Test LoggingConfig with defaults."""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert config.format == "{time} {level} {message}"

    def test_logging_config_validation(self):
        """Test LoggingConfig validation."""
        # Test valid config
        config = LoggingConfig(level="WARNING", format="Custom format")
        assert config.level == "WARNING"
        
        # Test invalid level
        with pytest.raises(ValueError):
            LoggingConfig(level="INVALID")


class TestPathsConfig:
    """Test PathsConfig class."""

    def test_paths_config_creation(self):
        """Test creating PathsConfig instance."""
        config = PathsConfig(
            raw_data="/data/raw",
            processed_data="/data/processed",
            vector_db="/data/vector_db"
        )
        
        assert config.raw_data == "/data/raw"
        assert config.processed_data == "/data/processed"
        assert config.vector_db == "/data/vector_db"

    def test_paths_config_defaults(self):
        """Test PathsConfig with defaults."""
        config = PathsConfig()
        
        assert config.raw_data == "./data/raw"
        assert config.processed_data == "./data/processed"
        assert config.vector_db == "./data/vector_db"


class TestConfig:
    """Test main Config class."""

    def test_config_creation(self):
        """Test creating Config instance."""
        config = Config(
            embedding=EmbeddingConfig(),
            vector_db=VectorDBConfig(),
            document_processing=DocumentProcessingConfig(),
            retrieval=RetrievalConfig(),
            llm=LLMConfig(),
            api=APIConfig(),
            logging=LoggingConfig(),
            paths=PathsConfig()
        )
        
        assert isinstance(config.embedding, EmbeddingConfig)
        assert isinstance(config.vector_db, VectorDBConfig)
        assert isinstance(config.document_processing, DocumentProcessingConfig)
        assert isinstance(config.retrieval, RetrievalConfig)
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.paths, PathsConfig)

    def test_config_validation(self):
        """Test Config validation."""
        # Test valid config
        config = Config(
            embedding=EmbeddingConfig(model_name="test"),
            vector_db=VectorDBConfig(type="chroma"),
            document_processing=DocumentProcessingConfig(chunk_size=1000),
            retrieval=RetrievalConfig(top_k=5),
            llm=LLMConfig(provider="openai"),
            api=APIConfig(port=8000),
            logging=LoggingConfig(level="INFO"),
            paths=PathsConfig(raw_data="./data")
        )
        assert config.embedding.model_name == "test"


class TestSettings:
    """Test Settings class."""

    def test_settings_creation(self):
        """Test creating Settings instance."""
        settings = Settings(
            openai_api_key="test-key",
            anthropic_api_key="test-key",
            embedding_model="test-model",
            llm_model="gpt-4",
            vector_db_path="/tmp/test",
            collection_name="test_collection",
            debug=True,
            log_level="DEBUG"
        )
        
        assert settings.openai_api_key == "test-key"
        assert settings.anthropic_api_key == "test-key"
        assert settings.embedding_model == "test-model"
        assert settings.llm_model == "gpt-4"
        assert settings.vector_db_path == "/tmp/test"
        assert settings.collection_name == "test_collection"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"

    def test_settings_defaults(self):
        """Test Settings with defaults."""
        settings = Settings()
        
        assert settings.openai_api_key is None
        assert settings.anthropic_api_key is None
        assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.llm_model == "gpt-3.5-turbo"
        assert settings.vector_db_path == "./data/vector_db"
        assert settings.collection_name == "kubernetes_docs"
        assert settings.debug is False
        assert settings.log_level == "INFO"


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_from_file(self):
        """Test loading config from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(TEST_CONFIG_DATA, f)
            f.flush()
            
            try:
                config = load_config(f.name)
                assert isinstance(config, Config)
                assert config.embedding.model_name == "test-embedding-model"
                assert config.vector_db.type == "chroma"
            finally:
                os.unlink(f.name)

    def test_load_config_default_path(self):
        """Test loading config with default path."""
        with patch('src.utils.config_loader.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with patch('builtins.open', mock_open_yaml_content()):
                config = load_config()
                assert isinstance(config, Config)

    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_config("non_existent_file.yaml")

    def test_load_config_invalid_yaml(self):
        """Test loading config with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            
            try:
                with pytest.raises(yaml.YAMLError):
                    load_config(f.name)
            finally:
                os.unlink(f.name)

    def test_load_config_validation_error(self):
        """Test loading config with validation error."""
        invalid_config = {
            "embedding": {
                "model_name": "test",
                "embedding_dim": -1,  # Invalid
                "batch_size": 32
            },
            "vector_db": {
                "type": "chroma",
                "persist_directory": "/tmp",
                "collection_name": "test",
                "distance_metric": "cosine"
            },
            "document_processing": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "separators": ["\n\n", "\n", " ", ""]
            },
            "retrieval": {
                "top_k": 5,
                "score_threshold": 0.7,
                "rerank": False,
                "rerank_top_k": 3
            },
            "llm": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.3,
                "max_tokens": 1000,
                "local_model_path": None
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "reload": False
            },
            "logging": {
                "level": "INFO",
                "format": "{time} {level} {message}"
            },
            "paths": {
                "raw_data": "./data/raw",
                "processed_data": "./data/processed",
                "vector_db": "./data/vector_db"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            f.flush()
            
            try:
                with pytest.raises(ValueError):
                    load_config(f.name)
            finally:
                os.unlink(f.name)


class TestLoadEnvSettings:
    """Test load_env_settings function."""

    def test_load_env_settings_with_env_vars(self):
        """Test loading settings from environment variables."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-openai-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "EMBEDDING_MODEL": "test-embedding-model",
            "LLM_MODEL": "gpt-4",
            "VECTOR_DB_PATH": "/tmp/test",
            "COLLECTION_NAME": "test_collection",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG"
        }):
            settings = load_env_settings()
            
            assert settings.openai_api_key == "test-openai-key"
            assert settings.anthropic_api_key == "test-anthropic-key"
            assert settings.embedding_model == "test-embedding-model"
            assert settings.llm_model == "gpt-4"
            assert settings.vector_db_path == "/tmp/test"
            assert settings.collection_name == "test_collection"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"

    def test_load_env_settings_defaults(self):
        """Test loading settings with default values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = load_env_settings()
            
            assert settings.openai_api_key is None
            assert settings.anthropic_api_key is None
            assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
            assert settings.llm_model == "gpt-3.5-turbo"
            assert settings.vector_db_path == "./data/vector_db"
            assert settings.collection_name == "kubernetes_docs"
            assert settings.debug is False
            assert settings.log_level == "INFO"

    def test_load_env_settings_boolean_parsing(self):
        """Test boolean parsing in environment variables."""
        with patch.dict(os.environ, {
            "DEBUG": "false",
            "TESTING": "1",
            "PRODUCTION": "0"
        }):
            settings = load_env_settings()
            
            assert settings.debug is False

    def test_load_env_settings_invalid_boolean(self):
        """Test handling of invalid boolean values."""
        with patch.dict(os.environ, {
            "DEBUG": "invalid"
        }):
            settings = load_env_settings()
            
            # Should default to False for invalid boolean
            assert settings.debug is False


class TestGetConfig:
    """Test get_config function."""

    def test_get_config_success(self):
        """Test successful config loading."""
        with patch('src.utils.config_loader.load_config') as mock_load_config, \
             patch('src.utils.config_loader.load_env_settings') as mock_load_env:
            
            mock_config = Mock()
            mock_settings = Mock()
            mock_load_config.return_value = mock_config
            mock_load_env.return_value = mock_settings
            
            config, settings = get_config()
            
            assert config == mock_config
            assert settings == mock_settings
            mock_load_config.assert_called_once_with("config/config.yaml")
            mock_load_env.assert_called_once()

    def test_get_config_with_custom_path(self):
        """Test config loading with custom path."""
        with patch('src.utils.config_loader.load_config') as mock_load_config, \
             patch('src.utils.config_loader.load_env_settings') as mock_load_env:
            
            mock_config = Mock()
            mock_settings = Mock()
            mock_load_config.return_value = mock_config
            mock_load_env.return_value = mock_settings
            
            config, settings = get_config("custom/path.yaml")
            
            assert config == mock_config
            assert settings == mock_settings
            mock_load_config.assert_called_once_with("custom/path.yaml")

    def test_get_config_file_error(self):
        """Test config loading with file error."""
        with patch('src.utils.config_loader.load_config') as mock_load_config:
            mock_load_config.side_effect = FileNotFoundError("Config file not found")
            
            with pytest.raises(FileNotFoundError):
                get_config()

    def test_get_config_validation_error(self):
        """Test config loading with validation error."""
        with patch('src.utils.config_loader.load_config') as mock_load_config:
            mock_load_config.side_effect = ValueError("Validation error")
            
            with pytest.raises(ValueError):
                get_config()


class TestConfigEdgeCases:
    """Test edge cases for config module."""

    def test_config_with_none_values(self):
        """Test config handling with None values."""
        config = Config(
            embedding=EmbeddingConfig(),
            vector_db=VectorDBConfig(),
            document_processing=DocumentProcessingConfig(),
            retrieval=RetrievalConfig(),
            llm=LLMConfig(local_model_path=None),
            api=APIConfig(),
            logging=LoggingConfig(),
            paths=PathsConfig()
        )
        
        assert config.llm.local_model_path is None

    def test_settings_with_empty_strings(self):
        """Test settings with empty string values."""
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
        assert settings.embedding_model == ""
        assert settings.llm_model == ""

    def test_config_serialization(self):
        """Test config serialization to dict."""
        config = Config(
            embedding=EmbeddingConfig(model_name="test"),
            vector_db=VectorDBConfig(type="chroma"),
            document_processing=DocumentProcessingConfig(chunk_size=1000),
            retrieval=RetrievalConfig(top_k=5),
            llm=LLMConfig(provider="openai"),
            api=APIConfig(port=8000),
            logging=LoggingConfig(level="INFO"),
            paths=PathsConfig(raw_data="./data")
        )
        
        config_dict = config.dict()
        assert isinstance(config_dict, dict)
        assert config_dict["embedding"]["model_name"] == "test"
        assert config_dict["vector_db"]["type"] == "chroma"

    def test_settings_serialization(self):
        """Test settings serialization to dict."""
        settings = Settings(
            openai_api_key="test-key",
            debug=True
        )
        
        settings_dict = settings.dict()
        assert isinstance(settings_dict, dict)
        assert settings_dict["openai_api_key"] == "test-key"
        assert settings_dict["debug"] is True

    def test_config_with_extra_fields(self):
        """Test config with extra fields (should be ignored)."""
        extra_config_data = {
            **TEST_CONFIG_DATA,
            "extra_field": "should_be_ignored",
            "embedding": {
                **TEST_CONFIG_DATA["embedding"],
                "extra_embedding_field": "ignored"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(extra_config_data, f)
            f.flush()
            
            try:
                config = load_config(f.name)
                assert isinstance(config, Config)
                # Extra fields should be ignored
                assert not hasattr(config, "extra_field")
            finally:
                os.unlink(f.name)


def mock_open_yaml_content():
    """Mock open function that returns YAML content."""
    from unittest.mock import mock_open
    return mock_open(read_data=yaml.dump(TEST_CONFIG_DATA))