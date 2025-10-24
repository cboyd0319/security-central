# Workflow Dependency Fixes

## Issue

The following GitHub Actions workflows were failing due to missing dependencies:

1. **Test & Coverage** workflow
2. **Daily Security Scan** workflow
3. **Emergency Response** workflow (potentially)
4. **Housekeeping** workflow (potentially)
5. **Weekly Audit** workflow (potentially)

## Root Cause

The workflows had hardcoded pip install commands that were missing critical dependencies:
- Missing `pydantic` (required by config_loader.py and other scripts)
- Missing `psutil` (required by performance_metrics.py)
- Not using the centralized requirements files

## Solution

Updated all workflows to use the new **requirements-prod.txt** file instead of hardcoded package lists.

### Files Modified

1. `.github/workflows/test.yml`
2. `.github/workflows/daily-security-scan.yml`
3. `.github/workflows/emergency-response.yml`
4. `.github/workflows/housekeeping.yml`
5. `.github/workflows/weekly-audit.yml`

### Changes Made

**Before:**
```yaml
- name: Install dependencies
  run: |
    pip install pyyaml requests safety pip-audit bandit
```

**After:**
```yaml
- name: Install dependencies
  run: |
    pip install --upgrade pip
    pip install -r requirements-prod.txt
    pip install semgrep  # Additional tools not in prod requirements
```

## Benefits

✅ **Centralized Dependency Management**: Single source of truth (requirements-prod.txt)
✅ **Automatic Updates**: Adding a dependency to requirements-prod.txt updates all workflows
✅ **No Missing Dependencies**: All required packages included (pyyaml, requests, pydantic, psutil, etc.)
✅ **Consistent Versions**: All workflows use same package versions
✅ **Easier Maintenance**: Update one file instead of 5+ workflows

## What's in requirements-prod.txt

```txt
# Core dependencies
pyyaml>=6.0.1              # Configuration parsing
requests>=2.32.3            # HTTP requests
pydantic>=2.0.0            # Data validation

# Security scanning tools
safety>=3.2.8              # Python vulnerability scanner
pip-audit>=2.7.3           # Python auditing
bandit>=1.7.10             # Security linter

# System utilities
psutil>=5.9.0              # Process monitoring (for performance metrics)
```

## Testing

After these fixes, workflows should:

1. ✅ Install all required dependencies
2. ✅ Import pydantic successfully
3. ✅ Import psutil successfully
4. ✅ Run tests without import errors
5. ✅ Execute security scans without failures

## Verification

You can verify the fixes locally:

```bash
# Install production dependencies
pip install -r requirements-prod.txt

# Run health check
python scripts/health_check.py

# Run tests
make test

# Check imports
python -c "import pydantic; import psutil; import yaml; import requests; print('✓ All imports successful')"
```

## Future

To prevent this issue in the future:

1. ✅ **Use requirements-prod.txt** in all workflows
2. ✅ **Add new dependencies** to requirements-prod.txt, not individual workflows
3. ✅ **Run health checks** before committing workflow changes
4. ✅ **Test locally** with `make install` before pushing

---

**Fixed**: 2024-10-24
**Impact**: All 5 workflows now use centralized dependency management
**Breaking Changes**: None - workflows still work, just with correct dependencies
