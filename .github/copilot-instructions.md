# GitHub Copilot Instructions for Security Central

## Project Overview

Security Central is an automated security monitoring system for multi-repo projects. It performs daily vulnerability scans, auto-patches security fixes, and handles emergency response across multiple repositories with different tech stacks (Python, PowerShell, Java/Kotlin/Scala, React/npm).

## Key Principles

1. **Automation First**: This project prioritizes automation over manual intervention
2. **Security Focus**: All code must handle security data carefully and follow best practices
3. **Multi-Ecosystem**: Support Python, PowerShell, Java/JVM, and npm ecosystems
4. **Minimal False Positives**: Prioritize accuracy over catching everything
5. **Vacation-Ready**: Systems must operate autonomously for extended periods

## Code Style and Standards

### Python
- Use Python 3.9+ features
- Follow PEP 8 style guide
- Format with Black (line length: 88)
- Sort imports with isort
- Type hints are required for all functions
- Use Pydantic for configuration and data validation
- Handle all errors explicitly - no silent failures

### YAML
- Use 2-space indentation
- Keep configurations declarative and simple
- Add comments for complex logic
- Validate against schemas where possible

### GitHub Actions
- Pin all action versions to specific commits or tags
- Include detailed descriptions for workflow inputs
- Set appropriate timeouts for all steps
- Use matrix strategies for multi-ecosystem scanning

## Architecture Patterns

### Configuration Loading
```python
from scripts.config_loader import load_config

# Always use the config loader for YAML files
config = load_config('config/repos.yml')
```

### Security Scanning
- Each scanner should produce SARIF output
- Findings must include: severity, CVE/CWE, affected package, fix version
- Always filter by severity threshold before alerting
- Cache scan results to avoid redundant work

### Auto-Merge Logic
```python
# Auto-merge is only safe when:
# 1. CI passes
# 2. It's a patch version or security fix
# 3. No breaking changes detected
# 4. Version jump within safety limits
```

### Error Handling
```python
# Always handle errors with context
try:
    result = scan_repository(repo)
except ScannerError as e:
    logger.error(f"Failed to scan {repo.name}: {e}")
    send_notification(severity="HIGH", message=f"Scanner failed: {e}")
    # Continue with other repos - one failure shouldn't stop everything
```

## Repository Structure

- `.github/workflows/` - All automation workflows
- `config/` - YAML configuration files for repos, policies, and dependencies
- `scripts/` - Core Python scripts for scanning, analysis, and automation
- `scripts/housekeeping/` - Maintenance automation scripts
- `scripts/intelligence/` - Threat intelligence and CVE tracking
- `scripts/monitoring/` - Dashboard and metrics
- `docs/` - Documentation and daily/weekly reports

## Key Files

### Configuration Files
- `config/repos.yml` - Monitored repositories and their auto-merge rules
- `config/security-policies.yml` - Severity thresholds and response times
- `config/common-dependencies.yml` - Shared dependency versions across repos

### Core Scripts
- `scripts/scan_all_repos.py` - Main scanning orchestrator
- `scripts/analyze_risk.py` - Risk analysis and triage
- `scripts/create_patch_prs.py` - Auto-generate fix PRs
- `scripts/clone_repos.py` - Repository cloning utilities

## Monitored Repositories

1. **PoshGuard** - PowerShell security tool
2. **BazBOM** - Multi-language build system (Java/Kotlin/Scala/Python/Bazel)
3. **JobSentinel** - Python/React job monitoring application
4. **PyGuard** - Python security scanning tool

## Security Scanners Used

### Python
- `pip-audit` - PyPI advisory database
- `safety` - Safety DB for known vulnerabilities
- `bandit` - Static code analysis for security issues
- `osv-scanner` - OSV (Open Source Vulnerabilities) database

### PowerShell
- `PSScriptAnalyzer` - PowerShell linting and security analysis
- `Pester` - Testing framework

### Java/JVM
- `OWASP Dependency-Check` - Dependency vulnerability scanner
- `osv-scanner` - OSV database scanning

### npm
- `npm audit` - npm registry vulnerability database

## Common Tasks

### Adding a New Repository
1. Add to `config/repos.yml` with tech stack and auto-merge rules
2. Ensure repository has auto-merge enabled
3. Configure notification threshold
4. Test with `scripts/scan_all_repos.py --repo NEW_REPO`

### Adding a New Security Scanner
1. Create scanner wrapper in appropriate scripts
2. Ensure SARIF output format
3. Add to workflow matrix
4. Update `config/repos.yml` security_tools list
5. Test against all tech stacks

### Creating a New Workflow
1. Use clear, descriptive names
2. Include manual trigger (`workflow_dispatch`)
3. Set appropriate schedules (don't overload API)
4. Add error notifications
5. Upload artifacts for debugging

## Testing Approach

- Test locally before committing: `python scripts/SCRIPT.py --dry-run`
- Use `gh workflow run` to test workflows manually
- Check workflow logs: `gh run view --log`
- Validate YAML: `yamllint config/`
- Run Python linters: `black . && isort . && ruff check .`

## Notification Patterns

### Severity-Based Notifications
- **CRITICAL**: Immediate PagerDuty alert + Slack
- **HIGH**: Slack notification within 1 hour
- **MEDIUM**: Daily digest
- **LOW**: Weekly summary

### Notification Content
Always include:
- Repository name
- Affected package and version
- CVE/CWE identifier
- Severity score
- Recommended fix version
- Link to PR (if auto-created)

## Emergency Response

When a critical CVE is discovered:
1. Assess impact across all monitored repos
2. Create emergency patches for affected repos
3. Send CRITICAL alerts via PagerDuty
4. Create tracking issue with incident details
5. Auto-merge if safe, otherwise flag for manual review

## Vacation Mode

When enabled (`VACATION_MODE=true`):
- Increase scan frequency to hourly
- Lower auto-merge thresholds (more aggressive)
- Send fewer notifications (only CRITICAL)
- Auto-archive repos as last resort for critical unfixable CVEs

## Common Gotchas

1. **Rate Limits**: GitHub API has rate limits - add delays between operations
2. **Token Permissions**: Ensure `REPO_ACCESS_TOKEN` has `repo` and `workflow` scopes
3. **SARIF Uploads**: GitHub only accepts SARIF files < 10MB
4. **Auto-Merge**: Requires branch protection + "Allow auto-merge" enabled on repo
5. **Slack Webhooks**: Test webhooks fail silently if URL is wrong
6. **Version Comparisons**: Use semantic versioning libraries, not string comparison

## Dependencies

- Keep all scanners up-to-date (weekly audit checks this)
- Pin versions in `requirements.txt`
- Sync common dependencies via `config/common-dependencies.yml`
- Update GitHub Actions yearly or when CVEs are found

## When Writing New Code

- Add logging for debugging: `import logging; logger = logging.getLogger(__name__)`
- Use environment variables for secrets, never hardcode
- Write defensive code - assume external services fail
- Document complex algorithms with comments
- Create unit tests for complex logic
- Use type hints for better IDE support
- Handle rate limits and retries for API calls

## Example Code Patterns

### Loading Repository Configuration
```python
import yaml
from pathlib import Path

def load_repos():
    config_path = Path(__file__).parent.parent / 'config' / 'repos.yml'
    with open(config_path) as f:
        return yaml.safe_load(f)['repositories']
```

### Calling GitHub API
```python
import os
import requests
import time

def github_api_call(endpoint, method='GET', data=None):
    headers = {
        'Authorization': f"token {os.getenv('REPO_ACCESS_TOKEN')}",
        'Accept': 'application/vnd.github.v3+json'
    }
    
    for attempt in range(3):
        response = requests.request(method, f"https://api.github.com{endpoint}", 
                                     headers=headers, json=data)
        if response.status_code == 403:  # Rate limit
            time.sleep(60)
            continue
        response.raise_for_status()
        return response.json()
    
    raise Exception(f"Failed after 3 attempts: {endpoint}")
```

### Creating SARIF Output
```python
def create_sarif_result(finding):
    return {
        'ruleId': finding.get('cve', 'UNKNOWN'),
        'level': severity_to_level(finding['severity']),
        'message': {
            'text': f"{finding['package']} {finding['version']} has known vulnerability"
        },
        'locations': [{
            'physicalLocation': {
                'artifactLocation': {
                    'uri': finding.get('file', 'requirements.txt')
                }
            }
        }]
    }
```

## Questions to Ask Before Coding

1. Does this handle all monitored tech stacks (Python, PowerShell, Java, npm)?
2. What happens if a repository is unreachable?
3. How will this behave during vacation mode?
4. Does this respect rate limits?
5. Is error handling sufficient?
6. Will this work with branch protection rules?
7. Is the notification severity appropriate?
8. Should this be auto-merged or require review?

## Resources

- [GitHub REST API](https://docs.github.com/en/rest)
- [SARIF Specification](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)
- [OSV Schema](https://ossf.github.io/osv-schema/)
- [CVSS Scoring](https://www.first.org/cvss/calculator/3.1)

## Contact

For questions about this project, see the repository's issue tracker or discussions.
