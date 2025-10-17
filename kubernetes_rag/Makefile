# Kubernetes RAG System - Makefile
# Comprehensive test and development automation

.PHONY: help install test test-unit test-integration test-performance test-coverage test-all lint format security clean setup pre-commit build docker docs

# Default target
help: ## Show this help message
	@echo "Kubernetes RAG System - Available Commands:"
	@echo "=========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment setup
setup: ## Setup development environment
	@echo "Setting up development environment..."
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install -r requirements-test.txt
	. venv/bin/activate && pre-commit install
	@echo "Environment setup complete!"

install: ## Install production dependencies
	@echo "Installing production dependencies..."
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-test.txt

# Testing commands
test: ## Run all tests
	@echo "Running comprehensive test suite..."
	. venv/bin/activate && python test_comprehensive.py

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	. venv/bin/activate && python test_comprehensive.py --unit-only

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	. venv/bin/activate && python test_comprehensive.py --integration-only

test-performance: ## Run performance tests only
	@echo "Running performance tests..."
	. venv/bin/activate && python test_comprehensive.py --performance-only

test-coverage: ## Run coverage analysis only
	@echo "Running coverage analysis..."
	. venv/bin/activate && python test_comprehensive.py --coverage-only

test-fast: ## Run fast tests (unit tests only)
	@echo "Running fast tests..."
	. venv/bin/activate && python -m pytest tests/test_generation_fixed.py tests/test_ingestion_fixed.py tests/test_retrieval_fixed.py tests/test_utils_fixed.py -v

test-api: ## Run API tests
	@echo "Running API tests..."
	. venv/bin/activate && python -m pytest tests/test_api_fixed.py tests/test_api_integration.py -v

test-cli: ## Run CLI tests
	@echo "Running CLI tests..."
	. venv/bin/activate && python -m pytest tests/test_cli_fixed.py -v

test-all: ## Run all tests with full coverage
	@echo "Running all tests with full coverage..."
	. venv/bin/activate && python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing --junitxml=test-results.xml

# Code quality
lint: ## Run linting checks
	@echo "Running linting checks..."
	. venv/bin/activate && flake8 src/ --max-line-length=100 --count --select=E9,F63,F7,F82 --show-source --statistics
	. venv/bin/activate && black --check src/
	. venv/bin/activate && isort --check-only src/
	. venv/bin/activate && mypy src/ --ignore-missing-imports

format: ## Format code
	@echo "Formatting code..."
	. venv/bin/activate && black src/ tests/ --line-length=100
	. venv/bin/activate && isort src/ tests/ --profile=black --line-length=100

format-check: ## Check code formatting
	@echo "Checking code formatting..."
	. venv/bin/activate && black --check src/ tests/ --line-length=100
	. venv/bin/activate && isort --check-only src/ tests/ --profile=black --line-length=100

# Security
security: ## Run security scans
	@echo "Running security scans..."
	. venv/bin/activate && bandit -r src/ -f json -o bandit-report.json
	. venv/bin/activate && safety check --json --output safety-report.json
	. venv/bin/activate && semgrep --config=auto src/ --json --output=semgrep-report.json

security-check: ## Check security vulnerabilities
	@echo "Checking security vulnerabilities..."
	. venv/bin/activate && bandit -r src/
	. venv/bin/activate && safety check

# Pre-commit
pre-commit: ## Run pre-commit hooks
	@echo "Running pre-commit hooks..."
	. venv/bin/activate && pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	. venv/bin/activate && pre-commit install

# Build and packaging
build: ## Build package
	@echo "Building package..."
	. venv/bin/activate && python -m build

build-check: ## Check package build
	@echo "Checking package build..."
	. venv/bin/activate && python -m build --sdist --wheel
	. venv/bin/activate && twine check dist/*

# Docker
docker: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t kubernetes-rag:latest .

docker-run: ## Run Docker container
	@echo "Running Docker container..."
	docker run -p 8000:8000 kubernetes-rag:latest

docker-test: ## Run tests in Docker
	@echo "Running tests in Docker..."
	docker run --rm kubernetes-rag:latest python -m pytest tests/ -v

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	. venv/bin/activate && mkdocs build

docs-serve: ## Serve documentation locally
	@echo "Serving documentation locally..."
	. venv/bin/activate && mkdocs serve

docs-deploy: ## Deploy documentation
	@echo "Deploying documentation..."
	. venv/bin/activate && mkdocs gh-deploy

# Coverage
coverage: ## Generate coverage report
	@echo "Generating coverage report..."
	. venv/bin/activate && python -m pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing

coverage-html: ## Open coverage report in browser
	@echo "Opening coverage report..."
	open htmlcov/index.html || xdg-open htmlcov/index.html

coverage-badge: ## Generate coverage badge
	@echo "Generating coverage badge..."
	. venv/bin/activate && coverage-badge -o coverage.svg

# Performance
benchmark: ## Run performance benchmarks
	@echo "Running performance benchmarks..."
	. venv/bin/activate && python -m pytest tests/test_performance_fixed.py --benchmark-only --benchmark-sort=mean

profile: ## Run performance profiling
	@echo "Running performance profiling..."
	. venv/bin/activate && python -m pytest tests/test_performance_fixed.py --profile

# Memory profiling
memory-profile: ## Run memory profiling
	@echo "Running memory profiling..."
	. venv/bin/activate && python -m memory_profiler test_comprehensive.py

# Cleanup
clean: ## Clean up generated files
	@echo "Cleaning up generated files..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .bandit
	rm -rf test_reports/
	rm -rf coverage.xml
	rm -rf test-results.xml
	rm -rf integration-results.xml
	rm -rf bandit-report.json
	rm -rf safety-report.json
	rm -rf semgrep-report.json
	rm -rf coverage.json
	rm -rf .coverage.*
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name "*.so" -delete

clean-venv: ## Clean virtual environment
	@echo "Cleaning virtual environment..."
	rm -rf venv/

clean-all: clean clean-venv ## Clean everything
	@echo "Cleaning everything..."

# Development
dev: ## Start development server
	@echo "Starting development server..."
	. venv/bin/activate && python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

dev-cli: ## Start CLI in development mode
	@echo "Starting CLI in development mode..."
	. venv/bin/activate && python -m src.cli --help

# CI/CD
ci: ## Run CI pipeline locally
	@echo "Running CI pipeline locally..."
	. venv/bin/activate && make lint
	. venv/bin/activate && make security-check
	. venv/bin/activate && make test-all
	. venv/bin/activate && make build-check

ci-full: ## Run full CI pipeline
	@echo "Running full CI pipeline..."
	. venv/bin/activate && make setup
	. venv/bin/activate && make ci
	. venv/bin/activate && make docker
	. venv/bin/activate && make docs

# Database
db-reset: ## Reset vector database
	@echo "Resetting vector database..."
	. venv/bin/activate && python -m src.cli reset

db-stats: ## Show database statistics
	@echo "Showing database statistics..."
	. venv/bin/activate && python -m src.cli stats

# Data ingestion
ingest: ## Ingest sample data
	@echo "Ingesting sample data..."
	. venv/bin/activate && python -m src.cli ingest docs/ --file-pattern "*.md"

# Query testing
query: ## Test query functionality
	@echo "Testing query functionality..."
	. venv/bin/activate && python -m src.cli query --query "What is Kubernetes?"

# Interactive mode
interactive: ## Start interactive mode
	@echo "Starting interactive mode..."
	. venv/bin/activate && python -m src.cli interactive

# Search testing
search: ## Test search functionality
	@echo "Testing search functionality..."
	. venv/bin/activate && python -m src.cli search --query "Kubernetes"

# Monitoring
monitor: ## Start monitoring
	@echo "Starting monitoring..."
	. venv/bin/activate && python -c "import psutil; print('CPU:', psutil.cpu_percent()); print('Memory:', psutil.virtual_memory().percent)"

# Version management
version: ## Show version information
	@echo "Version information:"
	@python -c "import sys; print('Python:', sys.version)"
	@. venv/bin/activate && pip list | grep -E "(pytest|coverage|black|flake8)"

# Dependencies
deps: ## Show dependency information
	@echo "Dependency information:"
	@. venv/bin/activate && pip list

deps-outdated: ## Show outdated dependencies
	@echo "Outdated dependencies:"
	@. venv/bin/activate && pip list --outdated

deps-update: ## Update dependencies
	@echo "Updating dependencies..."
	@. venv/bin/activate && pip install --upgrade pip
	@. venv/bin/activate && pip install --upgrade -r requirements.txt
	@. venv/bin/activate && pip install --upgrade -r requirements-test.txt

# Git hooks
git-hooks: ## Install git hooks
	@echo "Installing git hooks..."
	. venv/bin/activate && pre-commit install --hook-type pre-commit
	. venv/bin/activate && pre-commit install --hook-type commit-msg

# Release
release: ## Create a new release
	@echo "Creating new release..."
	. venv/bin/activate && bump2version patch
	. venv/bin/activate && git push --tags

release-minor: ## Create a minor release
	@echo "Creating minor release..."
	. venv/bin/activate && bump2version minor
	. venv/bin/activate && git push --tags

release-major: ## Create a major release
	@echo "Creating major release..."
	. venv/bin/activate && bump2version major
	. venv/bin/activate && git push --tags

# Status
status: ## Show project status
	@echo "Project Status:"
	@echo "=============="
	@echo "Python version: $(shell python --version)"
	@echo "Virtual env: $(shell if [ -d venv ]; then echo "Active"; else echo "Not found"; fi)"
	@echo "Tests: $(shell if [ -f test-results.xml ]; then echo "Last run: $(shell stat -c %y test-results.xml 2>/dev/null || echo 'Never')"; else echo "Never run"; fi)"
	@echo "Coverage: $(shell if [ -f coverage.xml ]; then echo "Available"; else echo "Not available"; fi)"
	@echo "Docker: $(shell if command -v docker >/dev/null 2>&1; then echo "Available"; else echo "Not installed"; fi)"

# Help for specific targets
test-help: ## Show test help
	@echo "Test Commands:"
	@echo "============="
	@echo "test          - Run all tests"
	@echo "test-unit     - Run unit tests only"
	@echo "test-integration - Run integration tests only"
	@echo "test-performance - Run performance tests only"
	@echo "test-coverage - Run coverage analysis only"
	@echo "test-fast     - Run fast tests (unit only)"
	@echo "test-api      - Run API tests"
	@echo "test-cli      - Run CLI tests"
	@echo "test-all      - Run all tests with full coverage"

lint-help: ## Show linting help
	@echo "Linting Commands:"
	@echo "================"
	@echo "lint          - Run all linting checks"
	@echo "format        - Format code"
	@echo "format-check  - Check code formatting"
	@echo "security      - Run security scans"
	@echo "security-check - Check security vulnerabilities"

# Default target
.DEFAULT_GOAL := help