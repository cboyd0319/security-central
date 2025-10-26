# Contributing to Security Central

Thank you for your interest in contributing to Security Central! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the community guidelines

---

## Getting Started

### Prerequisites

- Python 3.12+
- Git
- GitHub account
- Virtual environment (venv)

### Initial Setup

1. **Fork and clone the repository:**

```bash
git clone https://github.com/YOUR_USERNAME/security-central
cd security-central
```

2. **Set up development environment:**

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

3. **Verify setup:**

```bash
# Run tests
make test

# Run linters
make lint

# Check security
make security
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Write clean, readable code
- Follow existing patterns and conventions
- Add tests for new functionality
- Update documentation as needed

### 3. Run Quality Checks

```bash
# Format code
make format

# Run linters
make lint

# Run tests
make test

# Check coverage
make coverage
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature"
# or
git commit -m "fix: resolve bug in scanner"
```

**Commit Message Format:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

---

## Code Standards

### Python Style Guide

We follow **PEP 8** with these tools:

- **Black** (line length: 100) - Code formatting
- **isort** - Import sorting
- **flake8** - Linting
- **pylint** - Advanced linting

All code is automatically checked by pre-commit hooks.

### Type Hints

Use type hints for all function signatures:

```python
def process_findings(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Process security findings and return counts."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def scan_repository(repo_url: str, tech_stack: List[str]) -> Dict[str, Any]:
    """Scan a repository for vulnerabilities.

    Args:
        repo_url: GitHub repository URL
        tech_stack: List of technologies (e.g., ["python", "npm"])

    Returns:
        Dictionary containing scan results and findings

    Raises:
        ValueError: If repo_url is invalid
        RuntimeError: If scan fails
    """
    ...
```

### Security Guidelines

- Never hardcode credentials or secrets
- Use `utils.safe_open()` for file operations (path traversal protection)
- Validate all external inputs
- Use parameterized queries for any database operations
- Run `bandit` and `pip-audit` before committing

---

## Testing Requirements

### Test Coverage

- All new code must have **>85% test coverage**
- Critical paths require **100% coverage**
- Tests must pass on all supported Python versions

### Writing Tests

Tests use **pytest**. Place tests in `tests/` directory:

```python
# tests/test_my_feature.py
import pytest
from scripts.my_feature import my_function

def test_my_function_basic():
    """Test basic functionality."""
    result = my_function("input")
    assert result == "expected"

def test_my_function_edge_case():
    """Test edge case handling."""
    with pytest.raises(ValueError):
        my_function(None)
```

### Running Tests

```bash
# All tests
make test

# Specific file
pytest tests/test_my_feature.py -v

# With coverage
make coverage

# Fast tests only (skip slow integration tests)
make test-fast
```

---

## Pull Request Process

### Before Submitting

1. ✅ All tests pass locally
2. ✅ Code coverage >85%
3. ✅ Linters pass (flake8, pylint, black, isort)
4. ✅ Security scans clean (bandit, pip-audit)
5. ✅ Documentation updated
6. ✅ CHANGELOG.md updated (if applicable)

### PR Checklist

- [ ] Descriptive title following conventional commits
- [ ] Clear description of changes
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Linked to related issue (if applicable)

### Review Process

1. Automated checks run (GitHub Actions)
2. Code review by maintainers
3. Address feedback
4. Approval and merge

### After Merge

- Delete your feature branch
- Pull latest main branch
- Create new branch for next feature

---

## Project Structure

```
security-central/
├── scripts/           # Main application code
│   ├── utils.py       # Common utilities
│   ├── config_loader.py
│   └── ...
├── tests/             # Test suite
├── config/            # Configuration files
│   └── repos.yml      # Repository configuration
├── docs/              # Documentation
├── .github/           # GitHub Actions workflows
└── Makefile           # Development commands
```

---

## Common Development Tasks

### Add a New Script

1. Create script in `scripts/` directory
2. Add tests in `tests/`
3. Update `docs/` if needed
4. Run quality checks
5. Submit PR

### Update Dependencies

1. Update `requirements.txt` or `requirements-dev.txt`
2. Run `pip install -r requirements-dev.txt`
3. Run full test suite
4. Check for security vulnerabilities: `pip-audit`
5. Submit PR with dependency updates

### Fix a Bug

1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify test passes
4. Add regression test
5. Submit PR

---

## Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Browse existing [GitHub Issues](https://github.com/cboyd0319/security-central/issues)
- **Questions**: Open a GitHub Discussion

---

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- GitHub contributors page

Thank you for contributing to Security Central!
