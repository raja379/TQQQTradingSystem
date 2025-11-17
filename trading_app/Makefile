.PHONY: test test-unit test-integration test-cov clean install help

# Default target
help:
	@echo "📝 Trading System Test Commands"
	@echo "================================"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make test-quick    - Run tests without coverage (faster)"
	@echo ""
	@echo "📦 Setup:"
	@echo "  make install       - Install dependencies"
	@echo "  make clean         - Clean test artifacts"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make lint          - Run code linting (if available)"
	@echo "  make format        - Format code (if available)"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Run all tests
test:
	@echo "🧪 Running all tests..."
	python3 -m pytest tests/ -v --tb=short

# Run unit tests only
test-unit:
	@echo "🔬 Running unit tests..."
	python3 -m pytest tests/unit/ -v --tb=short

# Run integration tests only
test-integration:
	@echo "🔗 Running integration tests..."
	python3 -m pytest tests/integration/ -v --tb=short

# Run tests with coverage
test-cov:
	@echo "📊 Running tests with coverage..."
	python3 -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html:htmlcov -v
	@echo ""
	@echo "📈 Coverage report generated in 'htmlcov/' directory"
	@echo "📂 Open htmlcov/index.html in your browser to view detailed coverage"

# Run tests quickly (no coverage)
test-quick:
	@echo "⚡ Running tests (quick mode)..."
	python3 -m pytest tests/ -v -x --tb=line

# Clean test artifacts
clean:
	@echo "🧹 Cleaning test artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleaned test artifacts"

# Lint code (placeholder for future)
lint:
	@echo "⚠️  Linting not configured yet"
	@echo "💡 Consider adding: flake8, black, isort, mypy"

# Format code (placeholder for future)
format:
	@echo "⚠️  Code formatting not configured yet"
	@echo "💡 Consider adding: black, isort"