# Quick Start - Testing & CI/CD

## 🚀 Getting Started (60 seconds)

```bash
cd kubernetes_rag
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# View coverage
open test_reports/coverage/index.html
```

## 📊 Current Status
- **Coverage**: 70%
- **Tests**: 328 total, 172 passing
- **CI/CD**: ✅ Fully operational
- **Pre-commit**: ✅ Active

## 🔧 Common Commands

### Testing
```bash
# All tests
pytest -v

# Specific test file
pytest tests/test_api.py -v

# Specific test
pytest tests/test_api.py::TestHealthEndpoint::test_health_get -v

# By category
pytest -m unit              # Unit tests
pytest -m integration       # Integration tests
pytest -m slow              # Performance tests

# With coverage
pytest --cov=src --cov-report=term-missing

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

### Pre-commit Hooks
```bash
# Install hooks
pre-commit install

# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Update hooks
pre-commit autoupdate
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/ --max-line-length=88

# Type check
mypy src/

# Security scan
bandit -r src/
```

## 📁 Key Files
- `.github/workflows/test.yml` - CI/CD pipeline
- `.pre-commit-config.yaml` - Pre-commit hooks
- `pytest.ini` - Pytest configuration
- `.taskmaster/docs/100-percent-testing-coverage.md` - Full PRD
- `TESTING_COMPLETE_SUMMARY.md` - Detailed summary

## 🎯 Next Steps to 100%
1. Review failing tests: `pytest --tb=short`
2. Check coverage gaps: `pytest --cov=src --cov-report=term-missing`
3. Implement missing features (see PRD)
4. Write tests for uncovered lines
5. Run full suite: `pytest -v`

## 💡 Tips
- Tests auto-run on `git push`
- Pre-commit hooks auto-fix formatting
- Coverage reports: `test_reports/coverage/`
- Use `-v` for verbose output
- Use `--tb=short` for concise errors
- Use `-k` to run tests by name pattern

## 🔗 CI/CD
When you push to GitHub:
1. Pre-commit hooks run locally
2. GitHub Actions trigger
3. Tests run on Ubuntu/macOS/Windows
4. Coverage uploaded to Codecov
5. PR gets status checks

## 📖 Full Documentation
See `TESTING_COMPLETE_SUMMARY.md` for complete guide!
