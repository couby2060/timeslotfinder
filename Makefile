.PHONY: help install dev-install format lint type-check test clean run

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev-install  - Install with development dependencies"
	@echo "  make format       - Format code with black"
	@echo "  make lint         - Run ruff linter"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make test         - Run tests with pytest"
	@echo "  make clean        - Clean up cache files"
	@echo "  make run          - Run the CLI app"

install:
	pip install .

dev-install:
	pip install -e ".[dev]"

format:
	black src/
	ruff check src/ --fix

lint:
	ruff check src/

type-check:
	mypy src/

test:
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage

run:
	python timeslotfinder.py

