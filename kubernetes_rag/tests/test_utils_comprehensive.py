"""Comprehensive test suite for utils module to achieve 100% coverage."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.config_loader import Config, Settings, get_config, load_config
from src.utils.logger import get_logger, setup_logger


class TestConfig:
    """Test Config class."""

    def test_config_init(self):
        """Test Config initialization."""
        config_data = {
            "llm": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            "embeddings": {
                "provider": "openai",
                "model_name": "text-embedding-ada-002",
            },
            "vector_store": {
                "type": "chroma",
                "collection_name": "test_collection",
                "persist_directory": "/tmp/test",
            },
            "retrieval": {"top_k": 5, "similarity_threshold": 0.7},
        }

        config = Config(**config_data)

        assert config.llm.provider == "openai"
        assert config.llm.model_name == "gpt-3.5-turbo"
        assert config.embeddings.provider == "openai"
        assert config.vector_store.type == "chroma"
        assert config.retrieval.top_k == 5

    def test_config_validation(self):
        """Test Config validation."""
        with pytest.raises(ValueError):
            Config(llm={"provider": "invalid"})

    def test_config_defaults(self):
        """Test Config with default values."""
        config = Config()

        assert config.llm.provider == "openai"
        assert config.llm.temperature == 0.7
        assert config.retrieval.top_k == 5


class TestSettings:
    """Test Settings class."""

    def test_settings_init(self):
        """Test Settings initialization."""
        settings = Settings()

        assert settings.log_level == "INFO"
        assert settings.debug == False

    def test_settings_from_env(self):
        """Test Settings from environment variables."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "DEBUG": "true"}):
            settings = Settings()

            assert settings.log_level == "DEBUG"
            assert settings.debug == True


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_from_file(self):
        """Test loading config from file."""
        config_data = {
            "llm": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            "embeddings": {
                "provider": "openai",
                "model_name": "text-embedding-ada-002",
            },
            "vector_store": {
                "type": "chroma",
                "collection_name": "test_collection",
                "persist_directory": "/tmp/test",
            },
            "retrieval": {"top_k": 5, "similarity_threshold": 0.7},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()

            try:
                config, settings = load_config(f.name)

                assert isinstance(config, Config)
                assert isinstance(settings, Settings)
                assert config.llm.provider == "openai"
            finally:
                os.unlink(f.name)

    def test_load_config_default(self):
        """Test loading default config."""
        config, settings = load_config()

        assert isinstance(config, Config)
        assert isinstance(settings, Settings)

    def test_load_config_invalid_file(self):
        """Test loading config from invalid file."""
        with pytest.raises(FileNotFoundError):
            load_config("non_existent_file.yaml")

    def test_load_config_invalid_yaml(self):
        """Test loading config from invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            try:
                with pytest.raises(yaml.YAMLError):
                    load_config(f.name)
            finally:
                os.unlink(f.name)


class TestGetConfig:
    """Test get_config function."""

    def test_get_config(self):
        """Test get_config function."""
        with patch("src.utils.config_loader.load_config") as mock_load_config:
            mock_config = Mock()
            mock_settings = Mock()
            mock_load_config.return_value = (mock_config, mock_settings)

            config, settings = get_config()

            assert config == mock_config
            assert settings == mock_settings
            mock_load_config.assert_called_once()


class TestSetupLogger:
    """Test setup_logger function."""

    def test_setup_logger_default(self):
        """Test setup_logger with default parameters."""
        with patch("loguru.logger") as mock_logger:
            setup_logger()

            # Should not raise any exceptions
            assert True

    def test_setup_logger_custom_level(self):
        """Test setup_logger with custom log level."""
        with patch("loguru.logger") as mock_logger:
            setup_logger(log_level="DEBUG")

            # Should not raise any exceptions
            assert True

    def test_setup_logger_with_file(self):
        """Test setup_logger with file output."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                with patch("loguru.logger") as mock_logger:
                    setup_logger(log_file=f.name)

                    # Should not raise any exceptions
                    assert True
            finally:
                os.unlink(f.name)

    def test_setup_logger_remove_existing(self):
        """Test setup_logger removes existing handlers."""
        with patch("loguru.logger") as mock_logger:
            mock_logger.remove.return_value = None
            mock_logger.add.return_value = None

            setup_logger()

            mock_logger.remove.assert_called_once()


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger(self):
        """Test get_logger function."""
        with patch("loguru.logger") as mock_logger:
            logger = get_logger()

            assert logger == mock_logger


@pytest.mark.unit
class TestUtilsEdgeCases:
    """Test edge cases for utils module."""

    def test_config_missing_required_fields(self):
        """Test Config with missing required fields."""
        with pytest.raises(ValueError):
            Config(llm={})

    def test_config_invalid_llm_provider(self):
        """Test Config with invalid LLM provider."""
        with pytest.raises(ValueError):
            Config(llm={"provider": "invalid_provider"})

    def test_config_invalid_embeddings_provider(self):
        """Test Config with invalid embeddings provider."""
        with pytest.raises(ValueError):
            Config(embeddings={"provider": "invalid_provider"})

    def test_config_invalid_vector_store_type(self):
        """Test Config with invalid vector store type."""
        with pytest.raises(ValueError):
            Config(vector_store={"type": "invalid_type"})

    def test_settings_invalid_log_level(self):
        """Test Settings with invalid log level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            settings = Settings()
            # Should use default value
            assert settings.log_level == "INFO"

    def test_load_config_empty_file(self):
        """Test loading config from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()

            try:
                with pytest.raises(ValueError):
                    load_config(f.name)
            finally:
                os.unlink(f.name)

    def test_load_config_malformed_yaml(self):
        """Test loading config from malformed YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                "llm:\n  provider: openai\n  model_name: gpt-3.5-turbo\ninvalid_field: value"
            )
            f.flush()

            try:
                with pytest.raises(ValueError):
                    load_config(f.name)
            finally:
                os.unlink(f.name)


@pytest.mark.integration
class TestUtilsIntegration:
    """Test integration scenarios for utils module."""

    def test_config_and_settings_integration(self):
        """Test Config and Settings integration."""
        config_data = {
            "llm": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            "embeddings": {
                "provider": "openai",
                "model_name": "text-embedding-ada-002",
            },
            "vector_store": {
                "type": "chroma",
                "collection_name": "test_collection",
                "persist_directory": "/tmp/test",
            },
            "retrieval": {"top_k": 5, "similarity_threshold": 0.7},
        }

        config = Config(**config_data)
        settings = Settings()

        # Test that config and settings work together
        assert config.llm.provider == "openai"
        assert settings.log_level == "INFO"

    def test_logger_integration(self):
        """Test logger integration with config."""
        with patch("loguru.logger") as mock_logger:
            setup_logger(log_level="DEBUG")

            logger = get_logger()
            logger.info("Test message")

            # Should not raise any exceptions
            assert True


@pytest.mark.slow
class TestUtilsPerformance:
    """Test performance scenarios for utils module."""

    def test_config_loading_performance(self):
        """Test config loading performance."""
        import time

        config_data = {
            "llm": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            "embeddings": {
                "provider": "openai",
                "model_name": "text-embedding-ada-002",
            },
            "vector_store": {
                "type": "chroma",
                "collection_name": "test_collection",
                "persist_directory": "/tmp/test",
            },
            "retrieval": {"top_k": 5, "similarity_threshold": 0.7},
        }

        start_time = time.time()

        for _ in range(100):
            config = Config(**config_data)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 1 second for 100 iterations)
        assert duration < 1.0

    def test_logger_performance(self):
        """Test logger performance."""
        import time

        with patch("loguru.logger") as mock_logger:
            setup_logger()
            logger = get_logger()

            start_time = time.time()

            for _ in range(1000):
                logger.info("Test message")

            end_time = time.time()
            duration = end_time - start_time

            # Should complete in reasonable time (less than 1 second for 1000 messages)
            assert duration < 1.0
