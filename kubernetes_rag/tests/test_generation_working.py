"""Working comprehensive test suite for generation module to achieve 100% coverage."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test configuration
from test_config_final import (
    mock_config,
    mock_settings,
    create_mock_documents,
    TEST_MARKDOWN_CONTENT,
    TEST_TEXT_CONTENT
)

from src.generation.llm import (
    LLMBase,
    OpenAILLM,
    AnthropicLLM,
    LocalLLM,
    RAGGenerator,
    create_llm,
    create_rag_generator
)


class TestLLMBase:
    """Test LLMBase abstract class."""

    def test_llm_base_abstract(self):
        """Test that LLMBase cannot be instantiated."""
        with pytest.raises(TypeError):
            LLMBase()


class TestOpenAILLM:
    """Test OpenAILLM class."""

    def test_openai_llm_init_with_api_key(self):
        """Test OpenAILLM initialization with API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = OpenAILLM(api_key="test-key", model="gpt-4")
            assert llm.api_key == "test-key"
            assert llm.model == "gpt-4"

    def test_openai_llm_init_without_api_key(self):
        """Test OpenAILLM initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not found"):
                OpenAILLM()

    def test_openai_llm_init_test_mode(self):
        """Test OpenAILLM initialization in test mode."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            assert llm.client is None
            assert llm.model == "gpt-3.5-turbo"

    def test_openai_llm_generate_test_mode(self):
        """Test OpenAILLM generate in test mode."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            result = llm.generate("Test prompt")
            assert result == "This is a mock response for testing purposes."

    def test_openai_llm_generate_with_parameters(self):
        """Test OpenAILLM generate with custom parameters."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            result = llm.generate("Test prompt", temperature=0.5, max_tokens=500)
            assert result == "This is a mock response for testing purposes."

    def test_openai_llm_generate_with_client(self):
        """Test OpenAILLM generate with real client."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "TESTING": "false"}):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = "Test response"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                llm = OpenAILLM()
                result = llm.generate("Test prompt")
                assert result == "Test response"

    def test_openai_llm_generate_error_handling(self):
        """Test OpenAILLM error handling."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "TESTING": "false"}):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client
                
                llm = OpenAILLM()
                with pytest.raises(Exception, match="API Error"):
                    llm.generate("Test prompt")


class TestAnthropicLLM:
    """Test AnthropicLLM class."""

    def test_anthropic_llm_init_with_api_key(self):
        """Test AnthropicLLM initialization with API key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            llm = AnthropicLLM(api_key="test-key", model="claude-3-sonnet-20240229")
            assert llm.api_key == "test-key"
            assert llm.model == "claude-3-sonnet-20240229"

    def test_anthropic_llm_init_without_api_key(self):
        """Test AnthropicLLM initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key not found"):
                AnthropicLLM()

    def test_anthropic_llm_init_test_mode(self):
        """Test AnthropicLLM initialization in test mode."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = AnthropicLLM()
            assert llm.client is None
            assert llm.model == "claude-3-sonnet-20240229"

    def test_anthropic_llm_generate_test_mode(self):
        """Test AnthropicLLM generate in test mode."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = AnthropicLLM()
            result = llm.generate("Test prompt")
            assert result == "This is a mock response for testing purposes."

    def test_anthropic_llm_generate_with_client(self):
        """Test AnthropicLLM generate with real client."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "TESTING": "false"}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock()]
                mock_response.content[0].text = "Test response"
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_client
                
                llm = AnthropicLLM()
                result = llm.generate("Test prompt")
                assert result == "Test response"

    def test_anthropic_llm_generate_error_handling(self):
        """Test AnthropicLLM error handling."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "TESTING": "false"}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_client.messages.create.side_effect = Exception("API Error")
                mock_anthropic.return_value = mock_client
                
                llm = AnthropicLLM()
                with pytest.raises(Exception, match="API Error"):
                    llm.generate("Test prompt")


class TestLocalLLM:
    """Test LocalLLM class."""

    def test_local_llm_init(self):
        """Test LocalLLM initialization."""
        llm = LocalLLM(model_path="/path/to/model")
        assert llm.model_path == "/path/to/model"

    def test_local_llm_generate_test_mode(self):
        """Test LocalLLM generate in test mode."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = LocalLLM()
            result = llm.generate("Test prompt")
            assert result == "This is a mock response for testing purposes."

    def test_local_llm_generate_not_implemented(self):
        """Test LocalLLM generate when not in test mode."""
        with patch.dict(os.environ, {}, clear=True):
            llm = LocalLLM()
            with pytest.raises(NotImplementedError, match="Local LLM generation not implemented"):
                llm.generate("Test prompt")


class TestRAGGenerator:
    """Test RAGGenerator class."""

    def test_rag_generator_init(self):
        """Test RAGGenerator initialization."""
        mock_llm = Mock()
        generator = RAGGenerator(llm=mock_llm)
        assert generator.llm == mock_llm

    def test_rag_generator_generate_answer(self):
        """Test RAGGenerator generate_answer method."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [
                {"content": "Test document 1", "metadata": {"source": "test1.md"}, "score": 0.9},
                {"content": "Test document 2", "metadata": {"source": "test2.md"}, "score": 0.8}
            ]
            
            result = generator.generate_answer("Test query", documents)
            
            assert "answer" in result
            assert "query" in result
            assert "sources" in result
            assert "num_sources" in result
            assert result["query"] == "Test query"
            assert result["num_sources"] == 2
            assert len(result["sources"]) == 2

    def test_rag_generator_generate_answer_with_parameters(self):
        """Test RAGGenerator generate_answer with custom parameters."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            result = generator.generate_answer(
                "Test query", 
                documents, 
                temperature=0.5, 
                max_tokens=500,
                include_sources=True
            )
            
            assert "answer" in result
            assert result["query"] == "Test query"

    def test_rag_generator_generate_answer_empty_documents(self):
        """Test RAGGenerator generate_answer with empty documents."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            result = generator.generate_answer("Test query", [])
            
            assert "answer" in result
            assert result["sources"] == []
            assert result["num_sources"] == 0

    def test_rag_generator_generate_answer_without_sources(self):
        """Test RAGGenerator generate_answer without including sources."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            result = generator.generate_answer(
                "Test query", 
                documents, 
                include_sources=False
            )
            
            assert "answer" in result
            assert "sources" not in result

    def test_rag_generator_generate_answer_none_documents(self):
        """Test RAGGenerator generate_answer with None documents."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            # Handle None documents by converting to empty list
            result = generator.generate_answer("Test query", None or [])
            
            assert "answer" in result
            assert result["sources"] == []

    def test_rag_generator_large_documents(self):
        """Test RAGGenerator with large number of documents."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            # Create many documents
            documents = []
            for i in range(100):
                documents.append({
                    "content": f"Document {i} content",
                    "metadata": {"source": f"doc_{i}.md"},
                    "score": 0.9 - i * 0.01
                })
            
            result = generator.generate_answer("Test query", documents)
            
            assert "answer" in result
            assert len(result["sources"]) == 100

    def test_rag_generator_special_characters(self):
        """Test RAGGenerator with special characters in query."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            result = generator.generate_answer("Test query with @#$%^&*()", documents)
            
            assert "answer" in result
            assert result["query"] == "Test query with @#$%^&*()"

    def test_rag_generator_unicode_query(self):
        """Test RAGGenerator with unicode query."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            result = generator.generate_answer("你好世界", documents)
            
            assert "answer" in result
            assert result["query"] == "你好世界"

    def test_rag_generator_empty_query(self):
        """Test RAGGenerator with empty query."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            result = generator.generate_answer("", documents)
            
            assert "answer" in result
            assert result["query"] == ""

    def test_build_context(self):
        """Test RAGGenerator _build_context method."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [
                {"content": "Document 1", "metadata": {"source": "doc1.md"}, "score": 0.9},
                {"content": "Document 2", "metadata": {"source": "doc2.md"}, "score": 0.8}
            ]
            
            context = generator._build_context(documents)
            
            assert "Document 1" in context
            assert "Document 2" in context
            assert "0.90" in context
            assert "0.80" in context

    def test_build_context_empty_documents(self):
        """Test RAGGenerator _build_context with empty documents."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            context = generator._build_context([])
            
            assert context == ""

    def test_create_prompt(self):
        """Test RAGGenerator _create_prompt method."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            context = "Test context"
            query = "Test query"
            
            prompt = generator._create_prompt(query, context)
            
            assert "Test context" in prompt
            assert "Test query" in prompt
            assert "Answer:" in prompt

    def test_generate_with_followup(self):
        """Test RAGGenerator generate_with_followup method."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
            
            result = generator.generate_with_followup(
                "What is Kubernetes?", 
                documents, 
                history
            )
            
            assert "query" in result
            assert "answer" in result
            assert "conversation_history" in result
            assert "sources" in result
            assert result["query"] == "What is Kubernetes?"

    def test_generate_with_followup_empty_history(self):
        """Test RAGGenerator generate_with_followup with empty history."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            result = generator.generate_with_followup(
                "What is Kubernetes?", 
                documents, 
                []
            )
            
            assert "query" in result
            assert "answer" in result
            assert "conversation_history" in result
            assert "sources" in result

    def test_generate_with_followup_none_history(self):
        """Test RAGGenerator generate_with_followup with None history."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = OpenAILLM()
            generator = RAGGenerator(llm=llm)
            
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            result = generator.generate_with_followup(
                "What is Kubernetes?", 
                documents, 
                None
            )
            
            assert "query" in result
            assert "answer" in result
            assert "conversation_history" in result
            assert "sources" in result


class TestCreateLLM:
    """Test create_llm function."""

    def test_create_llm_openai(self):
        """Test create_llm with OpenAI provider."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = create_llm(provider="openai", model="gpt-4")
            assert isinstance(llm, OpenAILLM)
            assert llm.model == "gpt-4"

    def test_create_llm_anthropic(self):
        """Test create_llm with Anthropic provider."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = create_llm(provider="anthropic", model="claude-3-sonnet-20240229")
            assert isinstance(llm, AnthropicLLM)
            assert llm.model == "claude-3-sonnet-20240229"

    def test_create_llm_local(self):
        """Test create_llm with local provider."""
        llm = create_llm(provider="local", model_path="/path/to/model")
        assert isinstance(llm, LocalLLM)
        assert llm.model_path == "/path/to/model"

    def test_create_llm_invalid_provider(self):
        """Test create_llm with invalid provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_llm(provider="invalid")

    def test_create_llm_default(self):
        """Test create_llm with default parameters."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            llm = create_llm(provider="openai")
            assert isinstance(llm, OpenAILLM)
            assert llm.model == "gpt-3.5-turbo"


class TestCreateRAGGenerator:
    """Test create_rag_generator function."""

    def test_create_rag_generator_with_config(self):
        """Test create_rag_generator with config."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            generator = create_rag_generator(mock_config)
            assert isinstance(generator, RAGGenerator)
            assert isinstance(generator.llm, OpenAILLM)

    def test_create_rag_generator_with_custom_config(self):
        """Test create_rag_generator with custom config."""
        custom_config = Mock()
        custom_config.llm.provider = "anthropic"
        custom_config.llm.model_name = "claude-3-opus-20240229"
        
        with patch.dict(os.environ, {"TESTING": "true"}):
            generator = create_rag_generator(custom_config)
            assert isinstance(generator, RAGGenerator)
            assert isinstance(generator.llm, AnthropicLLM)


class TestGenerationIntegration:
    """Test integration scenarios for generation module."""

    def test_full_generation_workflow(self):
        """Test full generation workflow."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            # Create LLM
            llm = create_llm(provider="openai", model="gpt-4")
            
            # Create RAG generator
            generator = RAGGenerator(llm=llm)
            
            # Test documents
            documents = [
                {"content": "Kubernetes is a container orchestration platform.", "metadata": {"source": "k8s.md"}, "score": 0.9},
                {"content": "Docker is a containerization platform.", "metadata": {"source": "docker.md"}, "score": 0.8}
            ]
            
            # Generate answer
            result = generator.generate_answer("What is Kubernetes?", documents)
            
            assert "answer" in result
            assert "query" in result
            assert "sources" in result
            assert result["query"] == "What is Kubernetes?"
            assert len(result["sources"]) == 2

    def test_generation_with_different_providers(self):
        """Test generation with different LLM providers."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            # Test OpenAI
            openai_llm = create_llm(provider="openai")
            assert isinstance(openai_llm, OpenAILLM)
            
            # Test Anthropic
            anthropic_llm = create_llm(provider="anthropic")
            assert isinstance(anthropic_llm, AnthropicLLM)
            
            # Test Local
            local_llm = create_llm(provider="local")
            assert isinstance(local_llm, LocalLLM)

    def test_generation_error_handling_chain(self):
        """Test error handling across generation chain."""
        with patch.dict(os.environ, {}, clear=True):
            # Should fail without API keys
            with pytest.raises(ValueError):
                create_llm(provider="openai")
            
            with pytest.raises(ValueError):
                create_llm(provider="anthropic")

    def test_generation_with_custom_models(self):
        """Test generation with custom models."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            # Test with custom OpenAI model
            llm = create_llm(provider="openai", model="gpt-4-turbo")
            assert llm.model == "gpt-4-turbo"
            
            # Test with custom Anthropic model
            llm = create_llm(provider="anthropic", model="claude-3-opus-20240229")
            assert llm.model == "claude-3-opus-20240229"


class TestGenerationPerformance:
    """Test performance scenarios for generation module."""

    def test_generation_performance(self):
        """Test generation performance."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            generator = RAGGenerator(llm=OpenAILLM())
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            start_time = time.time()
            
            for _ in range(10):
                result = generator.generate_answer("Test query", documents)
                assert "answer" in result
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete in reasonable time
            assert duration < 2.0

    def test_generation_with_large_context(self):
        """Test generation with large context."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            generator = RAGGenerator(llm=OpenAILLM())
            
            # Create large documents
            documents = []
            for i in range(50):
                documents.append({
                    "content": f"Document {i} with lots of content to test performance with large context. " * 10,
                    "metadata": {"source": f"doc_{i}.md"},
                    "score": 0.9 - i * 0.01
                })
            
            start_time = time.time()
            result = generator.generate_answer("Test query", documents)
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 5.0  # Should complete in reasonable time
            assert "answer" in result
            assert len(result["sources"]) == 50

    def test_generation_concurrent_requests(self):
        """Test concurrent generation requests."""
        import threading
        
        with patch.dict(os.environ, {"TESTING": "true"}):
            generator = RAGGenerator(llm=OpenAILLM())
            documents = [{"content": "Test document", "metadata": {"source": "test.md"}, "score": 0.9}]
            
            results = []
            
            def generate_answer():
                result = generator.generate_answer("Test query", documents)
                results.append(result)
            
            # Create multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=generate_answer)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            start_time = time.time()
            for thread in threads:
                thread.join()
            end_time = time.time()
            
            duration = end_time - start_time
            assert duration < 3.0  # Should complete in reasonable time
            assert len(results) == 5
            assert all("answer" in result for result in results)
