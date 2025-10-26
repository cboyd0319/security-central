.PHONY: help install test lint format clean security coverage

help:
	@echo "Security-Central Development Commands"
	@echo "======================================"
	@echo "make install    - Install dependencies and setup environment"
	@echo "make test       - Run full test suite"
	@echo "make test-fast  - Run fast tests only"
	@echo "make lint       - Run linters"
	@echo "make format     - Format code with black and isort"
	@echo "make security   - Run security scans"
	@echo "make coverage   - Generate test coverage report"
	@echo "make clean      - Clean generated files"
	@echo "make all        - Run format, lint, test"

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -r requirements.txt
	. .venv/bin/activate && pip install -r requirements-dev.txt
	. .venv/bin/activate && pre-commit install

test:
	. .venv/bin/activate && python -m pytest tests/ -v --tb=short

test-fast:
	. .venv/bin/activate && python -m pytest tests/ -m "not slow" -v --tb=short

test-failed:
	. .venv/bin/activate && python -m pytest tests/ --lf -v

lint:
	. .venv/bin/activate && flake8 scripts/ --max-line-length=100 --extend-ignore=E203,W503
	. .venv/bin/activate && bandit -r scripts/ -c .bandit.yml

format:
	. .venv/bin/activate && black scripts/ tests/ --line-length=100
	. .venv/bin/activate && isort scripts/ tests/ --profile black

security:
	. .venv/bin/activate && pip-audit
	. .venv/bin/activate && bandit -r scripts/ -c .bandit.yml
	. .venv/bin/activate && python3 tools/run_pyguard.py

coverage:
	. .venv/bin/activate && python -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	rm -rf htmlcov/ .coverage

all: format lint test

.DEFAULT_GOAL := help
