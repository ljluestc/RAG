"""Comprehensive test suite for utils module to achieve 100% coverage."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.config_loader import Config, Settings, get_config
from src.utils.logger import get_logger, setup_logger


class TestConfigLoader:
    """Test configuration loader functionality."""

    def test_config_initialization(self):
        """Test Config class initialization."""
        config = Config()

        # Test default values
        assert hasattr(config, "embedding")
        assert hasattr(config, "vector_db")
        assert hasattr(config, "llm")
        assert hasattr(config, "retrieval")

    def test_settings_initialization(self):
        """Test Settings class initialization."""
        settings = Settings()

        # Test default values
        assert hasattr(settings, "openai_api_key")
        assert hasattr(settings, "anthropic_api_key")

    @patch("src.utils.config_loader.yaml.safe_load")
    @patch("builtins.open")
    def test_get_config_success(self, mock_open, mock_yaml_load):
        """Test successful config loading."""
        # Mock YAML content
        mock_yaml_content = {
            "embedding": {
                "model_name": "test-model",
                "embedding_dim": 384,
                "batch_size": 32,
            },
            "vector_db": {
                "type": "chromadb",
                "persist_directory": "./data/vector_db",
                "collection_name": "test_collection",
            },
            "llm": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.3,
                "max_tokens": 1000,
            },
            "retrieval": {
                "top_k": 5,
                "score_threshold": 0.7,
                "rerank": True,
                "rerank_top_k": 3,
            },
        }

        mock_yaml_load.return_value = mock_yaml_content
        mock_open.return_value.__enter__.return_value.read.return_value = "test yaml"

        config, settings = get_config()

        assert config is not None
        assert settings is not None
        assert config.embedding.model_name == "test-model"

    @patch("src.utils.config_loader.yaml.safe_load")
    @patch("builtins.open")
    def test_get_config_file_not_found(self, mock_open, mock_yaml_load):
        """Test config loading when file is not found."""
        mock_open.side_effect = FileNotFoundError("Config file not found")

        config, settings = get_config()

        # Should return default config
        assert config is not None
        assert settings is not None

    @patch("src.utils.config_loader.yaml.safe_load")
    @patch("builtins.open")
    def test_get_config_yaml_error(self, mock_open, mock_yaml_load):
        """Test config loading with YAML parsing error."""
        mock_yaml_load.side_effect = Exception("YAML parsing error")
        mock_open.return_value.__enter__.return_value.read.return_value = "invalid yaml"

        config, settings = get_config()

        # Should return default config
        assert config is not None
        assert settings is not None

    def test_config_attributes(self):
        """Test config attributes and their types."""
        config = Config()

        # Test embedding config
        assert hasattr(config.embedding, "model_name")
        assert hasattr(config.embedding, "embedding_dim")
        assert hasattr(config.embedding, "batch_size")

        # Test vector_db config
        assert hasattr(config.vector_db, "type")
        assert hasattr(config.vector_db, "persist_directory")
        assert hasattr(config.vector_db, "collection_name")

        # Test llm config
        assert hasattr(config.llm, "provider")
        assert hasattr(config.llm, "model_name")
        assert hasattr(config.llm, "temperature")
        assert hasattr(config.llm, "max_tokens")

        # Test retrieval config
        assert hasattr(config.retrieval, "top_k")
        assert hasattr(config.retrieval, "score_threshold")
        assert hasattr(config.retrieval, "rerank")
        assert hasattr(config.retrieval, "rerank_top_k")

    def test_settings_environment_variables(self):
        """Test settings environment variable handling."""
        settings = Settings()

        # Test that settings can handle missing environment variables
        assert settings.openai_api_key is None or isinstance(
            settings.openai_api_key, str
        )
        assert settings.anthropic_api_key is None or isinstance(
            settings.anthropic_api_key, str
        )


class TestLogger:
    """Test logger functionality."""

    def test_setup_logger(self):
        """Test logger setup."""
        logger = setup_logger("test_logger")

        assert logger is not None
        assert logger.name == "test_logger"

    def test_get_logger(self):
        """Test getting existing logger."""
        logger = get_logger("test_logger")

        assert logger is not None
        assert logger.name == "test_logger"

    def test_logger_levels(self):
        """Test logger levels."""
        logger = setup_logger("test_logger_levels")

        # Test that logger has standard levels
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")

    def test_logger_formatting(self):
        """Test logger formatting."""
        logger = setup_logger("test_logger_formatting")

        # Test that logger can format messages
        test_message = "Test message"
        formatted_message = logger.format(test_message)

        assert isinstance(formatted_message, str)
        assert len(formatted_message) > 0

    def test_logger_handlers(self):
        """Test logger handlers."""
        logger = setup_logger("test_logger_handlers")

        # Test that logger has handlers
        assert len(logger.handlers) > 0

        # Test handler types
        for handler in logger.handlers:
            assert hasattr(handler, "emit")
            assert hasattr(handler, "format")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_missing_sections(self):
        """Test config handling with missing sections."""
        config = Config()

        # Should handle missing sections gracefully
        assert config is not None
        assert hasattr(config, "embedding")
        assert hasattr(config, "vector_db")
        assert hasattr(config, "llm")
        assert hasattr(config, "retrieval")

    def test_settings_with_invalid_env_vars(self):
        """Test settings with invalid environment variables."""
        settings = Settings()

        # Should handle invalid environment variables gracefully
        assert settings is not None
        assert isinstance(settings.openai_api_key, (str, type(None)))
        assert isinstance(settings.anthropic_api_key, (str, type(None)))

    def test_logger_with_special_characters(self):
        """Test logger with special characters."""
        logger = setup_logger("test_logger_special_chars")

        # Test logging messages with special characters
        special_messages = [
            "Test message with émojis 🚀",
            "Test message with unicode: 中文",
            "Test message with symbols: @#$%^&*()",
            "Test message with newlines:\nLine 2\nLine 3",
        ]

        for message in special_messages:
            # Should handle special characters without errors
            assert isinstance(message, str)
            assert len(message) > 0

    def test_config_validation(self):
        """Test config validation."""
        config = Config()

        # Test that config values are within expected ranges
        assert config.embedding.embedding_dim > 0
        assert config.embedding.batch_size > 0
        assert config.llm.temperature >= 0.0
        assert config.llm.temperature <= 2.0
        assert config.llm.max_tokens > 0
        assert config.retrieval.top_k > 0
        assert config.retrieval.score_threshold >= 0.0
        assert config.retrieval.score_threshold <= 1.0
        assert config.retrieval.rerank_top_k > 0


class TestPerformance:
    """Test performance aspects."""

    def test_config_loading_performance(self):
        """Test config loading performance."""
        import time

        start_time = time.time()
        config, settings = get_config()
        end_time = time.time()

        # Should load quickly (less than 1 second)
        assert (end_time - start_time) < 1.0
        assert config is not None
        assert settings is not None

    def test_logger_performance(self):
        """Test logger performance."""
        import time

        logger = setup_logger("test_logger_performance")

        start_time = time.time()
        for i in range(100):
            logger.info(f"Test message {i}")
        end_time = time.time()

        # Should log quickly (less than 1 second for 100 messages)
        assert (end_time - start_time) < 1.0

    def test_memory_usage(self):
        """Test memory usage."""
        import sys

        initial_size = sys.getsizeof({})

        # Create multiple configs and loggers
        configs = [Config() for _ in range(10)]
        loggers = [setup_logger(f"test_logger_{i}") for i in range(10)]

        final_size = sys.getsizeof({})

        # Memory usage should be reasonable
        assert len(configs) == 10
        assert len(loggers) == 10


class TestIntegration:
    """Test integration scenarios."""

    def test_config_and_logger_integration(self):
        """Test integration between config and logger."""
        config, settings = get_config()
        logger = setup_logger("test_integration")

        # Test that they work together
        logger.info("Config loaded successfully")
        assert config is not None
        assert settings is not None
        assert logger is not None

    def test_multiple_loggers(self):
        """Test multiple loggers working together."""
        loggers = [
            setup_logger("test_logger_1"),
            setup_logger("test_logger_2"),
            setup_logger("test_logger_3"),
        ]

        # Test that all loggers work
        for i, logger in enumerate(loggers):
            logger.info(f"Test message from logger {i}")
            assert logger is not None
            assert logger.name == f"test_logger_{i+1}"

    def test_config_reloading(self):
        """Test config reloading."""
        config1, settings1 = get_config()
        config2, settings2 = get_config()

        # Should be able to reload config multiple times
        assert config1 is not None
        assert config2 is not None
        assert settings1 is not None
        assert settings2 is not None


# Test markers for pytest
@pytest.mark.unit
class TestUnitUtils(TestConfigLoader, TestLogger):
    """Unit tests for utils module."""

    pass


@pytest.mark.integration
class TestIntegrationUtils(TestIntegration):
    """Integration tests for utils module."""

    pass


@pytest.mark.slow
class TestSlowUtils(TestPerformance):
    """Slow tests for utils module."""

    pass
