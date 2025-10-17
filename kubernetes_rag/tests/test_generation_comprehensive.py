"""Comprehensive test suite for generation module to achieve 100% coverage."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.generation.llm import (
    LLMBase,
    OpenAILLM,
    AnthropicLLM,
    create_llm,
    create_rag_generator,
    RAGGenerator
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
    
    def test_openai_llm_init_success(self):
        """Test OpenAILLM initialization with valid API key."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            llm = OpenAILLM(model="gpt-3.5-turbo")
            assert llm.model == "gpt-3.5-turbo"
    
    def test_openai_llm_init_no_key(self):
        """Test OpenAILLM initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not found"):
                OpenAILLM()
    
    @patch('openai.OpenAI')
    def test_openai_llm_generate(self, mock_openai):
        """Test OpenAILLM generate method."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            llm = OpenAILLM(model="gpt-3.5-turbo")
            result = llm.generate("Test prompt")
            
            assert result == "Test response"
            mock_client.chat.completions.create.assert_called_once()
    
    @patch('openai.AsyncOpenAI')
    def test_openai_llm_agenerate(self, mock_openai):
        """Test OpenAILLM agenerate method."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test async response"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            llm = OpenAILLM(model="gpt-3.5-turbo")
            result = llm.agenerate("Test prompt")
            
            assert result == "Test async response"
            mock_client.chat.completions.create.assert_called_once()


class TestAnthropicLLM:
    """Test AnthropicLLM class."""
    
    def test_anthropic_llm_init_success(self):
        """Test AnthropicLLM initialization with valid API key."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            llm = AnthropicLLM(model="claude-3-sonnet")
            assert llm.model == "claude-3-sonnet"
    
    def test_anthropic_llm_init_no_key(self):
        """Test AnthropicLLM initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key not found"):
                AnthropicLLM()
    
    @patch('anthropic.Anthropic')
    def test_anthropic_llm_generate(self, mock_anthropic):
        """Test AnthropicLLM generate method."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "Test response"
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            llm = AnthropicLLM(model="claude-3-sonnet")
            result = llm.generate("Test prompt")
            
            assert result == "Test response"
            mock_client.messages.create.assert_called_once()
    
    @patch('anthropic.AsyncAnthropic')
    def test_anthropic_llm_agenerate(self, mock_anthropic):
        """Test AnthropicLLM agenerate method."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "Test async response"
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            llm = AnthropicLLM(model="claude-3-sonnet")
            result = llm.agenerate("Test prompt")
            
            assert result == "Test async response"
            mock_client.messages.create.assert_called_once()


class TestCreateLLM:
    """Test create_llm function."""
    
    def test_create_llm_openai(self):
        """Test creating OpenAI LLM."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            llm = create_llm(provider="openai", model="gpt-3.5-turbo")
            assert isinstance(llm, OpenAILLM)
    
    def test_create_llm_anthropic(self):
        """Test creating Anthropic LLM."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            llm = create_llm(provider="anthropic", model="claude-3-sonnet")
            assert isinstance(llm, AnthropicLLM)
    
    def test_create_llm_unsupported(self):
        """Test creating unsupported LLM provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            create_llm(provider="unsupported", model="test-model")


class TestRAGGenerator:
    """Test RAGGenerator class."""
    
    def test_rag_generator_init(self):
        """Test RAGGenerator initialization."""
        mock_llm = Mock()
        mock_retriever = Mock()
        
        generator = RAGGenerator(llm=mock_llm, retriever=mock_retriever)
        
        assert generator.llm == mock_llm
        assert generator.retriever == mock_retriever
    
    def test_rag_generator_generate_answer(self):
        """Test RAGGenerator generate_answer method."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "Test answer"
        mock_retriever = Mock()
        
        generator = RAGGenerator(llm=mock_llm, retriever=mock_retriever)
        
        query = "Test query"
        documents = [{"content": "Test doc", "metadata": {}}]
        
        result = generator.generate_answer(query, documents)
        
        assert result["answer"] == "Test answer"
        assert result["query"] == query
        assert result["documents"] == documents
        mock_llm.generate.assert_called_once()
    
    def test_rag_generator_generate_with_followup(self):
        """Test RAGGenerator generate_with_followup method."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "Test answer"
        mock_retriever = Mock()
        
        generator = RAGGenerator(llm=mock_llm, retriever=mock_retriever)
        
        query = "Test query"
        documents = [{"content": "Test doc", "metadata": {}}]
        conversation_history = []
        
        result = generator.generate_with_followup(query, documents, conversation_history)
        
        assert result["answer"] == "Test answer"
        assert result["query"] == query
        assert result["documents"] == documents
        assert "conversation_history" in result
        mock_llm.generate.assert_called_once()


class TestCreateRAGGenerator:
    """Test create_rag_generator function."""
    
    @patch('src.generation.llm.create_llm')
    @patch('src.retrieval.retriever.create_retriever')
    def test_create_rag_generator(self, mock_create_retriever, mock_create_llm):
        """Test creating RAG generator."""
        mock_llm = Mock()
        mock_retriever = Mock()
        mock_create_llm.return_value = mock_llm
        mock_create_retriever.return_value = mock_retriever
        
        mock_config = Mock()
        mock_config.llm.provider = "openai"
        mock_config.llm.model_name = "gpt-3.5-turbo"
        
        generator = create_rag_generator(mock_config)
        
        assert isinstance(generator, RAGGenerator)
        mock_create_llm.assert_called_once()
        mock_create_retriever.assert_called_once()


@pytest.mark.unit
class TestGenerationEdgeCases:
    """Test edge cases for generation module."""
    
    def test_openai_llm_empty_response(self):
        """Test OpenAI LLM with empty response."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = ""
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client
                
                llm = OpenAILLM(model="gpt-3.5-turbo")
                result = llm.generate("Test prompt")
                
                assert result == ""
    
    def test_anthropic_llm_empty_response(self):
        """Test Anthropic LLM with empty response."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock()]
                mock_response.content[0].text = ""
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_client
                
                llm = AnthropicLLM(model="claude-3-sonnet")
                result = llm.generate("Test prompt")
                
                assert result == ""
    
    def test_rag_generator_no_documents(self):
        """Test RAG generator with no documents."""
        mock_llm = Mock()
        mock_retriever = Mock()
        
        generator = RAGGenerator(llm=mock_llm, retriever=mock_retriever)
        
        query = "Test query"
        documents = []
        
        result = generator.generate_answer(query, documents)
        
        assert result["answer"] is not None
        assert result["query"] == query
        assert result["documents"] == documents


