.PHONY: help install install-dev test test-unit test-integration test-api test-cli test-coverage lint format check pre-commit clean docs

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pre-commit
	pre-commit install

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/test_document_processor.py tests/test_retriever.py -v

test-integration: ## Run integration tests only
	pytest tests/test_integration.py -v

test-api: ## Run API integration tests
	pytest tests/test_api_integration.py -v

test-cli: ## Run CLI integration tests
	pytest tests/test_cli_integration.py -v

test-coverage: ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

lint: ## Run linting checks
	flake8 src/ tests/
	mypy src/
	bandit -r src/ -f json -o bandit-report.json

format: ## Format code
	black src/ tests/
	isort src/ tests/

check: ## Run all checks (lint + format + test)
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/
	mypy src/
	pytest tests/ -v

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "bandit-report.json" -delete
	find . -type f -name "safety-report.json" -delete

docs: ## Generate documentation
	@echo "Documentation generation not implemented yet"

setup: install-dev ## Set up development environment
	@echo "Development environment set up successfully!"
	@echo "Run 'make test' to verify everything is working."
