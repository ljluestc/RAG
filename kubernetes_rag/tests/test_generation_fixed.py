"""Fixed comprehensive test suite for generation module to achieve 100% coverage."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test configuration
from test_config_comprehensive import (
    create_mock_config,
    create_mock_settings,
    create_mock_llm,
    create_mock_retriever,
    create_mock_rag_generator,
    TEST_CONFIG_DATA
)

from src.generation.llm import (
    LLMBase,
    OpenAILLM,
    AnthropicLLM,
    LocalLLM,
    RAGGenerator,
    create_llm,
    create_rag_generator,
)


class TestLLMBase:
    """Test LLMBase class."""

    def test_llm_base_abstract(self):
        """Test that LLMBase is abstract."""
        with pytest.raises(TypeError):
            LLMBase()

    def test_llm_base_interface(self):
        """Test LLMBase interface methods."""
        class TestLLM(LLMBase):
            def generate(self, prompt, temperature=0.3, max_tokens=1000):
                return "test response"

        llm = TestLLM()
        assert llm.generate("test") == "test response"


class TestOpenAILLM:
    """Test OpenAILLM class."""

    def test_openai_llm_init(self):
        """Test OpenAILLM initialization."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = OpenAILLM(api_key="test-key", model="gpt-3.5-turbo")
            assert llm.model == "gpt-3.5-turbo"

    def test_openai_llm_init_from_env(self):
        """Test OpenAILLM initialization from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = OpenAILLM(model="gpt-4")
            assert llm.model == "gpt-4"

    def test_openai_llm_init_testing_mode(self):
        """Test OpenAILLM initialization in testing mode."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            assert llm.client is None

    def test_openai_llm_generate(self):
        """Test OpenAILLM generate method."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            result = llm.generate("Test prompt")
            assert result == "This is a mock response for testing purposes."

    def test_openai_llm_generate_with_params(self):
        """Test OpenAILLM generate with parameters."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            result = llm.generate("Test prompt", temperature=0.5, max_tokens=500)
            assert result == "This is a mock response for testing purposes."

    def test_openai_llm_missing_api_key(self):
        """Test OpenAILLM with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not found"):
                OpenAILLM()


class TestAnthropicLLM:
    """Test AnthropicLLM class."""

    def test_anthropic_llm_init(self):
        """Test AnthropicLLM initialization."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            llm = AnthropicLLM(api_key="test-key", model="claude-3-sonnet")
            assert llm.model == "claude-3-sonnet"

    def test_anthropic_llm_init_from_env(self):
        """Test AnthropicLLM initialization from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            llm = AnthropicLLM(model="claude-3-haiku")
            assert llm.model == "claude-3-haiku"

    def test_anthropic_llm_init_testing_mode(self):
        """Test AnthropicLLM initialization in testing mode."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = AnthropicLLM()
            assert llm.client is None

    def test_anthropic_llm_generate(self):
        """Test AnthropicLLM generate method."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = AnthropicLLM()
            result = llm.generate("Test prompt")
            assert result == "This is a mock response for testing purposes."

    def test_anthropic_llm_missing_api_key(self):
        """Test AnthropicLLM with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key not found"):
                AnthropicLLM()


class TestLocalLLM:
    """Test LocalLLM class."""

    def test_local_llm_init(self):
        """Test LocalLLM initialization."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = LocalLLM(model="test-model")
            assert llm.model == "test-model"

    def test_local_llm_generate(self):
        """Test LocalLLM generate method."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = LocalLLM()
            result = llm.generate("Test prompt")
            assert result == "This is a mock response for testing purposes."


class TestCreateLLM:
    """Test create_llm function."""

    def test_create_llm_openai(self):
        """Test create_llm with OpenAI provider."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = create_llm(provider="openai", model="gpt-3.5-turbo")
            assert isinstance(llm, OpenAILLM)

    def test_create_llm_anthropic(self):
        """Test create_llm with Anthropic provider."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            llm = create_llm(provider="anthropic", model="claude-3-sonnet")
            assert isinstance(llm, AnthropicLLM)

    def test_create_llm_local(self):
        """Test create_llm with Local provider."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = create_llm(provider="local", model="test-model")
            assert isinstance(llm, LocalLLM)

    def test_create_llm_unsupported(self):
        """Test create_llm with unsupported provider."""
        with pytest.raises(ValueError, match="Unknown provider: unsupported"):
            create_llm(provider="unsupported", model="test-model")


class TestRAGGenerator:
    """Test RAGGenerator class."""

    def test_rag_generator_init(self):
        """Test RAGGenerator initialization."""
        mock_llm = create_mock_llm()
        generator = RAGGenerator(llm=mock_llm)
        assert generator.llm == mock_llm

    def test_rag_generator_generate_answer(self):
        """Test RAGGenerator generate_answer method."""
        mock_llm = create_mock_llm()
        generator = RAGGenerator(llm=mock_llm)
        
        documents = [
            {"content": "Test document 1", "metadata": {"source": "test1.md"}},
            {"content": "Test document 2", "metadata": {"source": "test2.md"}}
        ]
        
        result = generator.generate_answer("Test query", documents)
        
        assert result["query"] == "Test query"
        assert "answer" in result
        assert result["num_sources"] == 2

    def test_rag_generator_generate_with_followup(self):
        """Test RAGGenerator generate with followup."""
        mock_llm = create_mock_llm()
        generator = RAGGenerator(llm=mock_llm)
        
        documents = [{"content": "Test document", "metadata": {"source": "test.md"}}]
        
        result = generator.generate_answer(
            "Test query", 
            documents, 
            temperature=0.5, 
            max_tokens=500,
            include_sources=True
        )
        
        assert result["query"] == "Test query"
        assert "answer" in result


class TestCreateRAGGenerator:
    """Test create_rag_generator function."""

    def test_create_rag_generator(self):
        """Test create_rag_generator function."""
        with patch("src.generation.llm.create_llm") as mock_create_llm:

            mock_llm = create_mock_llm()
            mock_create_llm.return_value = mock_llm

            mock_config = create_mock_config()
            generator = create_rag_generator(mock_config)

            assert isinstance(generator, RAGGenerator)
            mock_create_llm.assert_called_once()


class TestGenerationEdgeCases:
    """Test edge cases for generation module."""

    def test_rag_generator_no_documents(self):
        """Test RAGGenerator with no documents."""
        mock_llm = create_mock_llm()
        generator = RAGGenerator(llm=mock_llm)
        
        result = generator.generate_answer("Test query", [])
        
        assert result["query"] == "Test query"
        assert result["num_sources"] == 0

    def test_rag_generator_empty_query(self):
        """Test RAGGenerator with empty query."""
        mock_llm = create_mock_llm()
        generator = RAGGenerator(llm=mock_llm)
        
        documents = [{"content": "Test document", "metadata": {"source": "test.md"}}]
        result = generator.generate_answer("", documents)
        
        assert result["query"] == ""
        assert "answer" in result

    def test_llm_generate_with_special_characters(self):
        """Test LLM generate with special characters."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            result = llm.generate("Test prompt with special chars: @#$%^&*()")
            assert result == "This is a mock response for testing purposes."

    def test_rag_generator_large_context(self):
        """Test RAGGenerator with large context."""
        mock_llm = create_mock_llm()
        generator = RAGGenerator(llm=mock_llm)
        
        # Create many documents
        documents = []
        for i in range(100):
            documents.append({
                "content": f"Document {i} content",
                "metadata": {"source": f"doc_{i}.md"}
            })
        
        result = generator.generate_answer("Test query", documents)
        
        assert result["query"] == "Test query"
        assert result["num_sources"] == 100


class TestGenerationIntegration:
    """Test integration scenarios for generation module."""

    def test_full_generation_workflow(self):
        """Test full generation workflow."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            # Create LLM
            llm = create_llm(provider="openai", model="gpt-3.5-turbo")
            
            # Create RAG generator
            generator = RAGGenerator(llm=llm)
            
            # Test documents
            documents = [
                {"content": "Kubernetes is a container orchestration platform.", "metadata": {"source": "k8s.md"}},
                {"content": "Docker is a containerization platform.", "metadata": {"source": "docker.md"}}
            ]
            
            # Generate answer
            result = generator.generate_answer("What is Kubernetes?", documents)
            
            assert result["query"] == "What is Kubernetes?"
            assert "answer" in result
            assert result["num_sources"] == 2

    def test_multiple_llm_providers(self):
        """Test multiple LLM providers."""
        providers = ["openai", "anthropic", "local"]

        for provider in providers:
            with patch.dict(os.environ, {"TESTING": "true"}):
                llm = create_llm(provider=provider, model="test-model")
                result = llm.generate("Test prompt")
                assert result == "This is a mock response for testing purposes."


class TestGenerationPerformance:
    """Test performance scenarios for generation module."""

    def test_llm_generation_performance(self):
        """Test LLM generation performance."""
        import time
        
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            
            start_time = time.time()
            
            for _ in range(10):
                llm.generate("Test prompt")
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete quickly in test mode
            assert duration < 1.0

    def test_rag_generator_performance(self):
        """Test RAG generator performance."""
        import time
        
        mock_llm = create_mock_llm()
        generator = RAGGenerator(llm=mock_llm)
        
        documents = [{"content": f"Document {i}", "metadata": {"source": f"doc_{i}.md"}} for i in range(50)]
        
        start_time = time.time()
        
        for _ in range(5):
            generator.generate_answer("Test query", documents)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 2.0
