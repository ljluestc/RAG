# Kubernetes RAG System - Testing Guide

This document provides comprehensive information about testing the Kubernetes RAG system.

## Test Structure

The test suite is organized into several categories:

### Unit Tests
- **Location**: `tests/test_document_processor.py`, `tests/test_retriever.py`
- **Purpose**: Test individual components in isolation
- **Coverage**: Document processing, retrieval logic, basic functionality

### Integration Tests
- **Location**: `tests/test_integration.py`
- **Purpose**: Test component interactions and end-to-end workflows
- **Coverage**:
  - Embedding generation
  - Vector store operations
  - Ingestion pipeline
  - Retrieval with filtering
  - RAG generation
  - Configuration loading
  - Full RAG pipeline

### API Integration Tests
- **Location**: `tests/test_api_integration.py`
- **Purpose**: Test FastAPI endpoints and HTTP interactions
- **Coverage**: All REST API endpoints, error handling, request validation

### CLI Integration Tests
- **Location**: `tests/test_cli_integration.py`
- **Purpose**: Test command-line interface functionality
- **Coverage**: All CLI commands, configuration handling, user interactions

## Running Tests

### Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up development environment:
```bash
make setup
```

### Basic Test Commands

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-api
make test-cli

# Run with coverage
make test-coverage
```

### Individual Test Execution

```bash
# Run specific test file
pytest tests/test_integration.py -v

# Run specific test class
pytest tests/test_integration.py::TestEmbeddingGenerator -v

# Run specific test method
pytest tests/test_integration.py::TestEmbeddingGenerator::test_encode_single_text -v

# Run with detailed output
pytest tests/ -v --tb=short
```

## Test Configuration

### pytest.ini
The project uses pytest configuration with:
- Coverage reporting
- Custom markers for test categorization
- Warning filters
- Output formatting

### Test Fixtures
Common fixtures are available for:
- Temporary vector stores
- Mock components
- Test data
- Configuration objects

## Pre-commit Hooks

### Setup
```bash
pip install pre-commit
pre-commit install
```

### Available Hooks
- **Code formatting**: Black, isort
- **Linting**: flake8, mypy
- **Security**: bandit
- **File checks**: YAML, JSON, TOML validation
- **Documentation**: docstring checks
- **Testing**: pytest execution

### Running Hooks
```bash
# Run on all files
make pre-commit

# Run on staged files only
pre-commit run

# Run specific hook
pre-commit run black
```

## Continuous Integration

### GitHub Actions
The project includes a comprehensive CI/CD pipeline:

- **Multi-Python version testing** (3.9, 3.10, 3.11, 3.12)
- **Test execution** with coverage reporting
- **Code quality checks** (linting, formatting, type checking)
- **Security scanning** (bandit, safety)
- **Pre-commit validation**
- **Package building** and validation

### Local CI Simulation
```bash
# Run all CI checks locally
make check

# Run individual checks
make lint
make format
make test
```

## Test Data Management

### Temporary Data
- Tests use temporary directories for vector stores
- ChromaDB files are created in temp directories
- Automatic cleanup after test completion

### Mock Data
- Mock LLM responses for consistent testing
- Sample Kubernetes documentation
- Test embeddings and vectors

## Coverage Reports

### HTML Coverage Report
```bash
make test-coverage
# Opens htmlcov/index.html in browser
```

### Coverage Configuration
- Source coverage: `src/` directory
- Exclusions: Test files, configuration files
- Minimum coverage threshold: 80%

## Troubleshooting

### Common Issues

1. **ChromaDB File Lock Errors (Windows)**
   - Issue: Permission errors during test cleanup
   - Solution: Tests still pass, cleanup errors are non-critical

2. **Missing Dependencies**
   - Issue: Import errors during testing
   - Solution: Ensure all requirements are installed

3. **Configuration Errors**
   - Issue: Config file not found
   - Solution: Ensure `config/config.yaml` exists

### Debug Mode
```bash
# Run tests with debug output
pytest tests/ -v -s --tb=long

# Run single test with debug
pytest tests/test_integration.py::TestEmbeddingGenerator::test_encode_single_text -v -s
```

## Performance Testing

### Test Performance
- Integration tests: ~40 seconds
- Unit tests: ~15 seconds
- API tests: ~10 seconds
- CLI tests: ~5 seconds

### Optimization
- Parallel test execution where possible
- Mocked external dependencies
- Efficient temporary data handling

## Best Practices

### Writing Tests
1. Use descriptive test names
2. Follow AAA pattern (Arrange, Act, Assert)
3. Use appropriate fixtures
4. Mock external dependencies
5. Test both success and failure cases

### Test Organization
1. Group related tests in classes
2. Use meaningful fixture names
3. Keep tests independent
4. Clean up resources properly

### Maintenance
1. Update tests when changing functionality
2. Keep test data current
3. Monitor test performance
4. Regular dependency updates

## Contributing

When adding new features:
1. Write unit tests for new components
2. Add integration tests for workflows
3. Update API/CLI tests if applicable
4. Ensure all tests pass
5. Maintain or improve coverage

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Click Testing](https://click.palletsprojects.com/en/8.1.x/testing/)
- [Pre-commit Hooks](https://pre-commit.com/)
- [Coverage.py](https://coverage.readthedocs.io/)
