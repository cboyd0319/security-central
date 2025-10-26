# Development Guide

Complete guide for developing and maintaining Security Central.

## Quick Start

```bash
# Setup
git clone https://github.com/cboyd0319/security-central
cd security-central
make install

# Development cycle
make format    # Format code
make lint      # Check code quality
make test      # Run tests
make coverage  # Generate coverage report
```

---

## Table of Contents

- [Development Environment](#development-environment)
- [Project Architecture](#project-architecture)
- [Development Tools](#development-tools)
- [Testing Strategy](#testing-strategy)
- [Code Quality](#code-quality)
- [Security Practices](#security-practices)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

---

## Development Environment

### Python Version

- **Required**: Python 3.12+
- **Recommended**: Python 3.14

### Virtual Environment

```bash
# Create and activate
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Deactivate when done
deactivate
```

### Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (includes pytest, black, etc.)
pip install -r requirements-dev.txt

# Production-only (minimal)
pip install -r requirements-prod.txt
```

### IDE Setup

#### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance
- Black Formatter
- isort

`.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true
}
```

---

## Project Architecture

### Directory Structure

```
security-central/
├── scripts/                    # Core application code
│   ├── utils.py                # Common utilities (safe_open, etc.)
│   ├── config_loader.py        # Configuration management
│   ├── scan_all_repos.py       # Main scanning logic
│   ├── analyze_risk.py         # Risk analysis engine
│   ├── create_issues.py        # GitHub issue creation
│   ├── generate_report.py      # Report generation
│   ├── health_check.py         # System health checks
│   ├── logging_config.py       # Logging configuration
│   └── performance_metrics.py  # Performance tracking
│
├── tests/                      # Comprehensive test suite
│   ├── test_*.py               # Unit and integration tests
│   └── conftest.py             # Pytest fixtures
│
├── config/                     # Configuration files
│   ├── repos.yml               # Repository definitions
│   └── security-central.yml    # Application configuration
│
├── docs/                       # Documentation
│   ├── QUICKSTART.md           # Quick start guide
│   ├── SETUP.md                # Detailed setup
│   ├── RUNBOOK.md              # Operational runbook
│   ├── MASTER_PLAN.md          # Long-term roadmap
│   └── reports/                # Generated reports
│
├── .github/workflows/          # CI/CD pipelines
│   ├── quality-gates.yml       # Code quality checks
│   ├── daily-security-scan.yml # Daily scans
│   └── test.yml                # Test automation
│
├── .pre-commit-config.yaml     # Pre-commit hooks
├── .bandit.yml                 # Security scanner config
├── Makefile                    # Development commands
├── IMPLEMENTATION_STATUS.md    # Current project status
└── README.md                   # Main documentation
```

### Key Modules

#### `utils.py`
Core utilities used across the project:
- `safe_open()`: Path traversal protection
- `safe_subprocess_run()`: Secure subprocess execution
- `deduplicate_findings()`: Finding deduplication
- `create_session_with_retries()`: HTTP session management

#### `config_loader.py`
Configuration management:
- Load and validate `repos.yml`
- Load and validate `security-central.yml`
- Configuration schema validation

#### `scan_all_repos.py`
Multi-ecosystem scanning:
- Python (pip-audit)
- JVM (Gradle vulnerability scan)
- npm (npm audit)
- PowerShell (static analysis)
- SARIF export

#### `analyze_risk.py`
Risk analysis and prioritization:
- CVE severity mapping
- Auto-fix confidence scoring
- Auto-merge safety assessment

---

## Development Tools

### Makefile Commands

```bash
make help       # Show all commands
make install    # Full setup
make test       # Run all tests
make test-fast  # Skip slow tests
make test-failed # Re-run only failed tests
make lint       # Run all linters
make format     # Format code (black + isort)
make security   # Security scans (pip-audit + bandit + PyGuard)
make coverage   # Generate coverage report
make clean      # Remove generated files
make all        # format + lint + test
```

### Pre-commit Hooks

Automatically run on `git commit`:
- Black (formatting)
- isort (import sorting)
- flake8 (linting)
- Trailing whitespace removal
- YAML validation
- Large file prevention

Skip hooks (emergency only):
```bash
git commit --no-verify
```

### Code Formatters

#### Black
```bash
black scripts/ tests/ --line-length=100
```

#### isort
```bash
isort scripts/ tests/ --profile black
```

### Linters

#### Flake8
```bash
flake8 scripts/ --max-line-length=100 --extend-ignore=E203,W503
```

#### Pylint
```bash
pylint scripts/ --max-line-length=100
```

### Security Scanners

#### Bandit (SAST)
```bash
bandit -r scripts/ -c .bandit.yml
```

#### pip-audit (Dependencies)
```bash
pip-audit --desc
```

#### PyGuard (Comprehensive)
```bash
python3 run_pyguard.py
```

---

## Testing Strategy

### Test Categories

1. **Unit Tests**: Test individual functions
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_utils.py -v

# Specific test
pytest tests/test_utils.py::test_safe_open -v

# With coverage
pytest tests/ --cov=scripts --cov-report=html

# Parallel execution (faster)
pytest tests/ -n auto

# Stop on first failure
pytest tests/ -x

# Show print statements
pytest tests/ -s
```

### Writing Tests

```python
import pytest
from scripts.my_module import my_function

class TestMyFunction:
    """Test my_function behavior."""

    def test_basic_case(self):
        """Test basic functionality."""
        result = my_function("input")
        assert result == "expected"

    def test_edge_case(self):
        """Test edge case."""
        with pytest.raises(ValueError):
            my_function(None)

    @pytest.fixture
    def sample_data(self):
        """Provide sample data for tests."""
        return {"key": "value"}

    def test_with_fixture(self, sample_data):
        """Test using fixture."""
        result = my_function(sample_data)
        assert result is not None
```

### Test Fixtures

Common fixtures in `tests/conftest.py`:
- `temp_dir`: Temporary directory
- `sample_sarif`: Sample SARIF data
- `mock_github_api`: Mocked GitHub API

### Coverage Requirements

- **Minimum**: 85% overall coverage
- **Critical paths**: 100% coverage
- **New code**: Must not decrease coverage

View coverage report:
```bash
make coverage
open htmlcov/index.html  # View in browser
```

---

## Code Quality

### Code Quality Metrics

Current status (as of 2025-10-26):
- **Test Coverage**: 45% (target: >85%)
- **Test Pass Rate**: 79% (254/322 tests)
- **Security Issues**: 0
- **Linting Issues**: Minimal

### Magic Numbers

Avoid magic numbers - use named constants:

❌ **Bad:**
```python
timeout = 60
if score > 80:
    ...
```

✅ **Good:**
```python
from scripts.constants import TIMEOUT_MEDIUM, HIGH_THRESHOLD

timeout = TIMEOUT_MEDIUM  # 60 seconds
if score > HIGH_THRESHOLD:  # 80
    ...
```

### Function Length

Keep functions focused and concise:
- **Target**: <50 lines
- **Maximum**: <100 lines
- Extract helper functions for clarity

### Complexity

Reduce cyclomatic complexity:
- **Target**: <10
- **Maximum**: <15
- Use early returns
- Extract complex logic to functions

---

## Security Practices

### Path Traversal Prevention

Always use `safe_open()`:

```python
from utils import safe_open

# Safe file operations
with safe_open(user_provided_path) as f:
    content = f.read()

# With explicit base directory
with safe_open(file_path, allowed_base="/allowed/dir") as f:
    content = f.read()
```

### Subprocess Execution

Use `safe_subprocess_run()`:

```python
from utils import safe_subprocess_run

result = safe_subprocess_run(
    ["command", "arg"],
    timeout=30,
    check=True
)
```

### Secrets Management

Never commit secrets:
- Use GitHub Secrets for CI/CD
- Use environment variables
- Add to `.gitignore`

Check for leaked secrets:
```bash
# Run TruffleHog (if available)
trufflehog filesystem .
```

---

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()
my_function()
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Memory Usage

```python
import tracemalloc

tracemalloc.start()
# ... code to profile ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

### Performance Metrics

Use built-in performance tracking:

```python
from scripts.performance_metrics import MetricsCollector, measure_performance

collector = MetricsCollector()

@measure_performance(collector, "my_operation")
def my_operation():
    ...

# Print summary
collector.print_summary()
```

---

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# Ensure you're in the right directory
cd /path/to/security-central

# Activate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements-dev.txt
```

#### Test Failures

```bash
# Run specific failing test with verbose output
pytest tests/test_failing.py::test_name -vv

# Show print statements
pytest tests/test_failing.py::test_name -s

# Run with debugger
pytest tests/test_failing.py::test_name --pdb
```

#### Pre-commit Hook Failures

```bash
# Run hooks manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate

# Skip hooks temporarily (emergency only)
git commit --no-verify
```

#### Coverage Not Updating

```bash
# Clean old coverage data
make clean

# Regenerate coverage
make coverage
```

### Debugging

```python
# Use pdb debugger
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### Logging

```python
from scripts.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

---

## Additional Resources

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide
- [docs/SETUP.md](docs/SETUP.md) - Detailed setup instructions
- [docs/RUNBOOK.md](docs/RUNBOOK.md) - Operational runbook
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) - Current status

---

**Questions?** Open a GitHub issue or discussion.
