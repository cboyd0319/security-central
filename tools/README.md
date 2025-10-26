# Development Tools

Utility scripts for code quality analysis and development.

## Available Tools

### Code Quality

#### `replace_magic_numbers.py`
Analyzes the codebase for magic numbers and suggests named constants.

```bash
# Analyze magic numbers
python3 tools/replace_magic_numbers.py

# Generate report
python3 tools/replace_magic_numbers.py --report
```

**Output:** Analysis of all numeric literals in the code with suggestions for constant names.

---

#### `apply_magic_number_fixes.py`
Automatically replaces magic numbers with named constants.

```bash
# Dry run (preview changes)
python3 tools/apply_magic_number_fixes.py --dry-run

# Create constants file
python3 tools/apply_magic_number_fixes.py --create-constants

# Apply all replacements
python3 tools/apply_magic_number_fixes.py --apply
```

**Features:**
- Creates `scripts/constants.py` with all constant definitions
- Updates files to import and use constants
- Validates Python syntax after changes
- Groups constants by category (HTTP codes, timeouts, retries, etc.)

---

### Security Analysis

#### `run_pyguard.py`
Runs PyGuard security scanner with custom configuration.

```bash
# Run security scan
python3 tools/run_pyguard.py

# Via Makefile
make security
```

**Features:**
- Comprehensive security and code quality scanning
- Auto-fix for safe issues
- Detailed reporting
- Integration with CI/CD (see `.github/workflows/quality-gates.yml`)

---

## Integration with Workflows

These tools are integrated into the development workflow:

### Pre-commit Hooks
Security scanning runs automatically before commits (see `.pre-commit-config.yaml`)

### CI/CD
Quality gates workflow runs these tools on every PR (see `.github/workflows/quality-gates.yml`)

### Makefile
Common commands available via `make`:
- `make security` - Runs all security tools including PyGuard
- `make lint` - Code quality checks
- `make format` - Auto-format code

---

## Adding New Tools

To add a new development tool:

1. Create the script in `tools/`
2. Add documentation to this README
3. Add to Makefile if appropriate
4. Update `.github/workflows/quality-gates.yml` if needed

---

## Tool Dependencies

Most tools use the same dependencies as the main project:
- Python 3.12+
- Dependencies from `requirements-dev.txt`

Special dependencies:
- **PyGuard**: Installed separately (see tool documentation)
- **Analysis tools**: Use built-in Python `ast` module

---

**See also:** [DEVELOPMENT.md](../docs/DEVELOPMENT.md) for complete development guide
