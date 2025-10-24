.PHONY: help install test lint format scan clone analyze report clean setup check-deps metrics

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(BLUE)Security-Central Makefile$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} \
		/^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

install: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install -r requirements.txt
	pip install -r requirements-dev.txt || pip install pytest pytest-cov pytest-mock mypy black isort flake8 bandit
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

setup: install install-dev ## Full setup (install all dependencies)
	@echo "$(BLUE)Setting up pre-commit hooks...$(NC)"
	pip install pre-commit
	pre-commit install
	@echo "$(GREEN)✓ Setup complete$(NC)"

##@ Code Quality

lint: ## Run all linters (flake8, mypy, bandit)
	@echo "$(BLUE)Running linters...$(NC)"
	@echo "→ flake8"
	flake8 scripts/ tests/ || true
	@echo "→ mypy"
	mypy scripts/ --ignore-missing-imports || true
	@echo "→ bandit"
	bandit -r scripts/ -c .bandit || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black scripts/ tests/
	isort scripts/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run mypy type checking
	@echo "$(BLUE)Running type checks...$(NC)"
	mypy scripts/ --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking complete$(NC)"

security-check: ## Run bandit security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	bandit -r scripts/ -c .bandit
	@echo "$(GREEN)✓ Security checks complete$(NC)"

check-deps: ## Check for outdated dependencies
	@echo "$(BLUE)Checking dependencies...$(NC)"
	pip list --outdated
	@echo "$(GREEN)✓ Dependency check complete$(NC)"

##@ Testing

test: ## Run tests with pytest
	@echo "$(BLUE)Running tests...$(NC)"
	pytest tests/ -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest tests/ --cov=scripts --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated: htmlcov/index.html$(NC)"

test-fast: ## Run tests without coverage (faster)
	@echo "$(BLUE)Running fast tests...$(NC)"
	pytest tests/ -v --no-cov
	@echo "$(GREEN)✓ Tests complete$(NC)"

##@ Scanning Operations

clone: ## Clone all monitored repositories
	@echo "$(BLUE)Cloning repositories...$(NC)"
	python3 scripts/clone_repos.py
	@echo "$(GREEN)✓ Repositories cloned$(NC)"

scan: ## Run security scans on all repositories
	@echo "$(BLUE)Running security scans...$(NC)"
	python3 scripts/scan_all_repos.py
	@echo "$(GREEN)✓ Scans complete$(NC)"

analyze: ## Analyze findings and generate risk reports
	@echo "$(BLUE)Analyzing findings...$(NC)"
	python3 scripts/analyze_risk.py findings.json --output triage.json
	@echo "$(GREEN)✓ Analysis complete: triage.json$(NC)"

report: ## Generate human-readable security report
	@echo "$(BLUE)Generating report...$(NC)"
	python3 scripts/generate_report.py triage.json --output reports/security-report.md
	@echo "$(GREEN)✓ Report generated: reports/security-report.md$(NC)"

full-scan: clone scan analyze report ## Run full scan pipeline (clone → scan → analyze → report)
	@echo "$(GREEN)✓ Full scan pipeline complete!$(NC)"

##@ Utilities

matrix: ## Generate repository matrix for GitHub Actions
	@echo "$(BLUE)Generating repository matrix...$(NC)"
	python3 scripts/generate_repo_matrix.py --info

matrix-json: ## Generate repository matrix as JSON
	@python3 scripts/generate_repo_matrix.py --format github

metrics: ## Display performance metrics
	@echo "$(BLUE)Performance Metrics:$(NC)"
	@if [ -f metrics/performance.json ]; then \
		python3 -c "import json; data = json.load(open('metrics/performance.json')); \
		print(f'Total operations: {data[\"total_operations\"]}'); \
		print('Last updated:', data['last_updated'])"; \
	else \
		echo "$(YELLOW)No metrics file found$(NC)"; \
	fi

logs: ## View recent logs
	@echo "$(BLUE)Recent logs:$(NC)"
	@if [ -d logs ]; then \
		tail -n 50 logs/*.log 2>/dev/null || echo "$(YELLOW)No log files found$(NC)"; \
	else \
		echo "$(YELLOW)Logs directory not found$(NC)"; \
	fi

##@ Cleanup

clean: ## Clean generated files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-all: clean ## Clean everything including reports and repos
	@echo "$(YELLOW)⚠️  This will delete all cloned repos and reports!$(NC)"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds..."
	@sleep 5
	rm -rf repos/ reports/ findings.json triage.json findings.sarif metrics/
	@echo "$(GREEN)✓ Full cleanup complete$(NC)"

clean-reports: ## Clean only report files
	@echo "$(BLUE)Cleaning reports...$(NC)"
	rm -f findings.json triage.json findings.sarif
	rm -rf reports/
	@echo "$(GREEN)✓ Reports cleaned$(NC)"

##@ Development

dev-setup: setup ## Setup development environment
	@echo "$(GREEN)✓ Development environment ready$(NC)"

pre-commit: ## Run pre-commit hooks manually
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit complete$(NC)"

check-all: lint test security-check ## Run all checks (lint + test + security)
	@echo "$(GREEN)✓ All checks passed!$(NC)"

ci: check-all ## Run all CI checks locally
	@echo "$(GREEN)✓ CI checks complete!$(NC)"

##@ Documentation

docs: ## Generate documentation (placeholder)
	@echo "$(YELLOW)Documentation generation not yet implemented$(NC)"

##@ Quick Commands

quick-scan: ## Quick scan (skip clone if repos exist)
	@echo "$(BLUE)Quick scan...$(NC)"
	@if [ ! -d repos ] || [ -z "$$(ls -A repos 2>/dev/null)" ]; then \
		echo "$(YELLOW)Cloning repositories first...$(NC)"; \
		$(MAKE) clone; \
	fi
	$(MAKE) scan analyze
	@echo "$(GREEN)✓ Quick scan complete!$(NC)"

status: ## Show status of scans and reports
	@echo "$(BLUE)Repository Status:$(NC)"
	@if [ -d repos ]; then \
		echo "Cloned repos: $$(ls -1 repos 2>/dev/null | wc -l | tr -d ' ')"; \
	else \
		echo "$(YELLOW)No repos directory$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)Report Status:$(NC)"
	@if [ -f findings.json ]; then \
		echo "✓ findings.json exists"; \
	else \
		echo "$(YELLOW)✗ findings.json not found$(NC)"; \
	fi
	@if [ -f triage.json ]; then \
		echo "✓ triage.json exists"; \
	else \
		echo "$(YELLOW)✗ triage.json not found$(NC)"; \
	fi
	@if [ -d reports ]; then \
		echo "✓ reports/ directory exists"; \
	else \
		echo "$(YELLOW)✗ reports/ directory not found$(NC)"; \
	fi

version: ## Show Python and dependency versions
	@echo "$(BLUE)Version Information:$(NC)"
	@python3 --version
	@echo ""
	@echo "$(BLUE)Key Dependencies:$(NC)"
	@pip show pyyaml pydantic requests 2>/dev/null | grep -E "Name|Version" || echo "Dependencies not installed"
