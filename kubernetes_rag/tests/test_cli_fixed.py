"""Fixed comprehensive test suite for CLI module to achieve 100% coverage."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from click.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import test configuration
from test_config_comprehensive import (
    create_mock_config,
    create_mock_settings,
    create_mock_vector_store,
    create_mock_retriever,
    create_mock_rag_generator,
    TEST_MARKDOWN_CONTENT,
    TEST_TEXT_CONTENT,
    TEST_CONFIG_DATA
)

from src.cli import cli, ingest, query, interactive, stats, reset, search


class TestCLIBasic:
    """Test basic CLI functionality."""

    def test_cli_group(self):
        """Test CLI group command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Kubernetes RAG System CLI" in result.output

    def test_cli_with_config(self):
        """Test CLI with custom config file."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--config', 'test_config.yaml', '--help'])
        assert result.exit_code == 0

    def test_cli_with_log_level(self):
        """Test CLI with custom log level."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--log-level', 'DEBUG', '--help'])
        assert result.exit_code == 0


class TestIngestCommand:
    """Test ingest command."""

    def test_ingest_command_help(self):
        """Test ingest command help."""
        runner = CliRunner()
        result = runner.invoke(ingest, ['--help'])
        assert result.exit_code == 0
        assert "Ingest documents into the RAG system" in result.output

    def test_ingest_file_success(self):
        """Test successful file ingestion."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(TEST_MARKDOWN_CONTENT)
            f.flush()
            
            try:
                with patch('src.ingestion.pipeline.create_ingestion_pipeline') as mock_create_pipeline:
                    mock_pipeline = Mock()
                    mock_pipeline.ingest_file.return_value = 5
                    mock_create_pipeline.return_value = mock_pipeline
                    
                    result = runner.invoke(ingest, [f.name])
                    assert result.exit_code == 0
                    assert "Successfully ingested 5 chunks" in result.output
            finally:
                os.unlink(f.name)

    def test_ingest_file_with_pattern(self):
        """Test file ingestion with file pattern."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test1.md").write_text(TEST_MARKDOWN_CONTENT)
            (temp_path / "test2.txt").write_text(TEST_TEXT_CONTENT)
            
            with patch('src.ingestion.pipeline.create_ingestion_pipeline') as mock_create_pipeline:
                mock_pipeline = Mock()
                mock_pipeline.ingest_file.return_value = 3
                mock_create_pipeline.return_value = mock_pipeline
                
                result = runner.invoke(ingest, [str(temp_path), '--file-pattern', '*.md'])
                assert result.exit_code == 0

    def test_ingest_file_not_found(self):
        """Test file ingestion with non-existent file."""
        runner = CliRunner()
        
        result = runner.invoke(ingest, ['non_existent_file.md'])
        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_ingest_pipeline_error(self):
        """Test file ingestion with pipeline error."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(TEST_MARKDOWN_CONTENT)
            f.flush()
            
            try:
                with patch('src.ingestion.pipeline.create_ingestion_pipeline') as mock_create_pipeline:
                    mock_pipeline = Mock()
                    mock_pipeline.ingest_file.side_effect = Exception("Pipeline error")
                    mock_create_pipeline.return_value = mock_pipeline
                    
                    result = runner.invoke(ingest, [f.name])
                    assert result.exit_code == 1
                    assert "Error ingesting file" in result.output
            finally:
                os.unlink(f.name)


class TestQueryCommand:
    """Test query command."""

    def test_query_command_help(self):
        """Test query command help."""
        runner = CliRunner()
        result = runner.invoke(query, ['--help'])
        assert result.exit_code == 0
        assert "Query the RAG system" in result.output

    def test_query_success(self):
        """Test successful query."""
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": []
            }
            mock_create_generator.return_value = mock_generator
            
            result = runner.invoke(query, ['--query', 'Test query'])
            assert result.exit_code == 0
            assert "Test answer" in result.output

    def test_query_with_top_k(self):
        """Test query with custom top_k."""
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": []
            }
            mock_create_generator.return_value = mock_generator
            
            result = runner.invoke(query, ['--query', 'Test query', '--top-k', '10'])
            assert result.exit_code == 0

    def test_query_generator_error(self):
        """Test query with generator error."""
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.side_effect = Exception("Generator error")
            mock_create_generator.return_value = mock_generator
            
            result = runner.invoke(query, ['--query', 'Test query'])
            assert result.exit_code == 1
            assert "Error generating answer" in result.output


class TestInteractiveCommand:
    """Test interactive command."""

    def test_interactive_command_help(self):
        """Test interactive command help."""
        runner = CliRunner()
        result = runner.invoke(interactive, ['--help'])
        assert result.exit_code == 0
        assert "Start interactive mode" in result.output

    def test_interactive_mode(self):
        """Test interactive mode."""
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": []
            }
            mock_create_generator.return_value = mock_generator
            
            # Simulate user input
            input_data = "Test query\nquit\n"
            result = runner.invoke(interactive, input=input_data)
            assert result.exit_code == 0

    def test_interactive_mode_error(self):
        """Test interactive mode with error."""
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.side_effect = Exception("Generator error")
            mock_create_generator.return_value = mock_generator
            
            # Simulate user input
            input_data = "Test query\nquit\n"
            result = runner.invoke(interactive, input=input_data)
            # Should handle error gracefully
            assert result.exit_code == 0


class TestStatsCommand:
    """Test stats command."""

    def test_stats_command_help(self):
        """Test stats command help."""
        runner = CliRunner()
        result = runner.invoke(stats, ['--help'])
        assert result.exit_code == 0
        assert "Show collection statistics" in result.output

    def test_stats_success(self):
        """Test successful stats display."""
        runner = CliRunner()
        
        with patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.get_collection_stats.return_value = {
                "name": "test_collection",
                "count": 100,
                "persist_directory": "/tmp/test"
            }
            mock_create_vs.return_value = mock_vector_store
            
            result = runner.invoke(stats)
            assert result.exit_code == 0
            assert "Collection: test_collection" in result.output
            assert "Documents: 100" in result.output

    def test_stats_vector_store_error(self):
        """Test stats with vector store error."""
        runner = CliRunner()
        
        with patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.get_collection_stats.side_effect = Exception("Vector store error")
            mock_create_vs.return_value = mock_vector_store
            
            result = runner.invoke(stats)
            assert result.exit_code == 1
            assert "Error getting statistics" in result.output


class TestResetCommand:
    """Test reset command."""

    def test_reset_command_help(self):
        """Test reset command help."""
        runner = CliRunner()
        result = runner.invoke(reset, ['--help'])
        assert result.exit_code == 0
        assert "Reset the vector database" in result.output

    def test_reset_success(self):
        """Test successful reset."""
        runner = CliRunner()
        
        with patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.delete_collection.return_value = None
            mock_create_vs.return_value = mock_vector_store
            
            # Simulate user confirmation
            result = runner.invoke(reset, input='y\n')
            assert result.exit_code == 0
            assert "Vector database reset successfully" in result.output

    def test_reset_cancelled(self):
        """Test reset cancelled by user."""
        runner = CliRunner()
        
        with patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            mock_vector_store = Mock()
            mock_create_vs.return_value = mock_vector_store
            
            # Simulate user cancellation
            result = runner.invoke(reset, input='n\n')
            assert result.exit_code == 0
            assert "Reset cancelled" in result.output

    def test_reset_vector_store_error(self):
        """Test reset with vector store error."""
        runner = CliRunner()
        
        with patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.delete_collection.side_effect = Exception("Vector store error")
            mock_create_vs.return_value = mock_vector_store
            
            result = runner.invoke(reset, input='y\n')
            assert result.exit_code == 1
            assert "Error resetting database" in result.output


class TestSearchCommand:
    """Test search command."""

    def test_search_command_help(self):
        """Test search command help."""
        runner = CliRunner()
        result = runner.invoke(search, ['--help'])
        assert result.exit_code == 0
        assert "Search for documents" in result.output

    def test_search_success(self):
        """Test successful search."""
        runner = CliRunner()
        
        with patch('src.retrieval.retriever.create_retriever') as mock_create_retriever:
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = [
                {
                    "content": "Test document",
                    "metadata": {"source": "test.md"},
                    "score": 0.9
                }
            ]
            mock_create_retriever.return_value = mock_retriever
            
            result = runner.invoke(search, ['--query', 'Test query'])
            assert result.exit_code == 0
            assert "Test document" in result.output

    def test_search_with_top_k(self):
        """Test search with custom top_k."""
        runner = CliRunner()
        
        with patch('src.retrieval.retriever.create_retriever') as mock_create_retriever:
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = []
            mock_create_retriever.return_value = mock_retriever
            
            result = runner.invoke(search, ['--query', 'Test query', '--top-k', '10'])
            assert result.exit_code == 0

    def test_search_retriever_error(self):
        """Test search with retriever error."""
        runner = CliRunner()
        
        with patch('src.retrieval.retriever.create_retriever') as mock_create_retriever:
            mock_retriever = Mock()
            mock_retriever.retrieve.side_effect = Exception("Retriever error")
            mock_create_retriever.return_value = mock_retriever
            
            result = runner.invoke(search, ['--query', 'Test query'])
            assert result.exit_code == 1
            assert "Error searching documents" in result.output


class TestCLIEdgeCases:
    """Test edge cases for CLI module."""

    def test_ingest_with_unsupported_file_format(self):
        """Test ingest with unsupported file format."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
            f.write("Some content")
            f.flush()
            
            try:
                result = runner.invoke(ingest, [f.name])
                assert result.exit_code == 1
                assert "Unsupported file type" in result.output
            finally:
                os.unlink(f.name)

    def test_query_with_empty_query(self):
        """Test query with empty query."""
        runner = CliRunner()
        
        result = runner.invoke(query, ['--query', ''])
        assert result.exit_code == 1
        assert "Query cannot be empty" in result.output

    def test_search_with_empty_query(self):
        """Test search with empty query."""
        runner = CliRunner()
        
        result = runner.invoke(search, ['--query', ''])
        assert result.exit_code == 1
        assert "Query cannot be empty" in result.output

    def test_interactive_with_keyboard_interrupt(self):
        """Test interactive mode with keyboard interrupt."""
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": []
            }
            mock_create_generator.return_value = mock_generator
            
            # Simulate Ctrl+C
            result = runner.invoke(interactive, input='Test query\n')
            # Should handle gracefully
            assert result.exit_code == 0

    def test_stats_with_empty_collection(self):
        """Test stats with empty collection."""
        runner = CliRunner()
        
        with patch('src.retrieval.vector_store.create_vector_store') as mock_create_vs:
            mock_vector_store = Mock()
            mock_vector_store.get_collection_stats.return_value = {
                "name": "test_collection",
                "count": 0,
                "persist_directory": "/tmp/test"
            }
            mock_create_vs.return_value = mock_vector_store
            
            result = runner.invoke(stats)
            assert result.exit_code == 0
            assert "Documents: 0" in result.output

    def test_query_with_special_characters(self):
        """Test query with special characters."""
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer with special chars",
                "query": "Test query with @#$%^&*()",
                "documents": []
            }
            mock_create_generator.return_value = mock_generator
            
            result = runner.invoke(query, ['--query', 'Test query with @#$%^&*()'])
            assert result.exit_code == 0
            assert "special chars" in result.output


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def test_full_workflow(self):
        """Test full CLI workflow: ingest -> search -> query."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test.md").write_text(TEST_MARKDOWN_CONTENT)
            
            # Mock all dependencies
            with patch('src.ingestion.pipeline.create_ingestion_pipeline') as mock_create_pipeline, \
                 patch('src.retrieval.retriever.create_retriever') as mock_create_retriever, \
                 patch('src.generation.llm.create_rag_generator') as mock_create_generator:
                
                # Setup mocks
                mock_pipeline = Mock()
                mock_pipeline.ingest_file.return_value = 3
                mock_create_pipeline.return_value = mock_pipeline
                
                mock_retriever = Mock()
                mock_retriever.retrieve.return_value = [
                    {
                        "content": "Test document",
                        "metadata": {"source": "test.md"},
                        "score": 0.9
                    }
                ]
                mock_create_retriever.return_value = mock_retriever
                
                mock_generator = Mock()
                mock_generator.generate_answer.return_value = {
                    "answer": "Test answer",
                    "query": "Test query",
                    "documents": []
                }
                mock_create_generator.return_value = mock_generator
                
                # Test ingest
                result = runner.invoke(ingest, [str(temp_path / "test.md")])
                assert result.exit_code == 0
                
                # Test search
                result = runner.invoke(search, ['--query', 'Test query'])
                assert result.exit_code == 0
                
                # Test query
                result = runner.invoke(query, ['--query', 'Test query'])
                assert result.exit_code == 0

    def test_error_handling_chain(self):
        """Test error handling across multiple commands."""
        runner = CliRunner()
        
        # Test with missing dependencies
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(query, ['--query', 'Test query'])
            assert result.exit_code == 1
            
            result = runner.invoke(search, ['--query', 'Test query'])
            assert result.exit_code == 1

    def test_config_file_handling(self):
        """Test CLI with custom config file."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(TEST_CONFIG_DATA, f)
            f.flush()
            
            try:
                result = runner.invoke(cli, ['--config', f.name, '--help'])
                assert result.exit_code == 0
            finally:
                os.unlink(f.name)

    def test_invalid_config_file(self):
        """Test CLI with invalid config file."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['--config', 'non_existent_config.yaml', '--help'])
        # Should still work as config loading is deferred
        assert result.exit_code == 0


class TestCLIPerformance:
    """Test performance scenarios for CLI module."""

    def test_ingest_performance(self):
        """Test ingest command performance."""
        import time
        
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(TEST_MARKDOWN_CONTENT * 100)  # Large content
            f.flush()
            
            try:
                with patch('src.ingestion.pipeline.create_ingestion_pipeline') as mock_create_pipeline:
                    mock_pipeline = Mock()
                    mock_pipeline.ingest_file.return_value = 100
                    mock_create_pipeline.return_value = mock_pipeline
                    
                    start_time = time.time()
                    result = runner.invoke(ingest, [f.name])
                    end_time = time.time()
                    
                    duration = end_time - start_time
                    assert duration < 2.0  # Should complete quickly
                    assert result.exit_code == 0
            finally:
                os.unlink(f.name)

    def test_query_performance(self):
        """Test query command performance."""
        import time
        
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": []
            }
            mock_create_generator.return_value = mock_generator
            
            start_time = time.time()
            
            for _ in range(10):
                result = runner.invoke(query, ['--query', 'Test query'])
                assert result.exit_code == 0
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete in reasonable time
            assert duration < 3.0

    def test_search_performance(self):
        """Test search command performance."""
        import time
        
        runner = CliRunner()
        
        with patch('src.retrieval.retriever.create_retriever') as mock_create_retriever:
            mock_retriever = Mock()
            mock_retriever.retrieve.return_value = [
                {
                    "content": "Test document",
                    "metadata": {"source": "test.md"},
                    "score": 0.9
                }
            ]
            mock_create_retriever.return_value = mock_retriever
            
            start_time = time.time()
            
            for _ in range(10):
                result = runner.invoke(search, ['--query', 'Test query'])
                assert result.exit_code == 0
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete in reasonable time
            assert duration < 3.0

    def test_interactive_performance(self):
        """Test interactive mode performance."""
        import time
        
        runner = CliRunner()
        
        with patch('src.generation.llm.create_rag_generator') as mock_create_generator:
            mock_generator = Mock()
            mock_generator.generate_answer.return_value = {
                "answer": "Test answer",
                "query": "Test query",
                "documents": []
            }
            mock_create_generator.return_value = mock_generator
            
            start_time = time.time()
            
            # Simulate multiple queries
            input_data = "Test query 1\nTest query 2\nTest query 3\nquit\n"
            result = runner.invoke(interactive, input=input_data)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete in reasonable time
            assert duration < 5.0
            assert result.exit_code == 0
