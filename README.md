# security-central

**Centralized security monitoring and automated maintenance for PoshGuard, BazBOM, JobSentinel, and PyGuard.**

[![Daily Security Scan](https://github.com/cboyd0319/security-central/actions/workflows/daily-security-scan.yml/badge.svg)](https://github.com/cboyd0319/security-central/actions/workflows/daily-security-scan.yml)
[![Weekly Audit](https://github.com/cboyd0319/security-central/actions/workflows/weekly-audit.yml/badge.svg)](https://github.com/cboyd0319/security-central/actions/workflows/weekly-audit.yml)

## What This Does

**Problem**: You have 4 disconnected projects with different tech stacks (PowerShell, Python, Java/Kotlin/Scala, React). Manually monitoring security vulnerabilities across all of them is impossible while holding a day job.

**Solution**: This repository automatically:

- 🔍 **Scans** all repos daily for security vulnerabilities
- 🤖 **Auto-patches** safe security fixes (patch versions, known good updates)
- 🚨 **Alerts** you (Slack/PagerDuty) for CRITICAL issues
- 📊 **Reports** weekly dependency health
- 🧹 **Maintains** code quality standards across repos
- 🔄 **Syncs** common dependencies (e.g., Black, isort versions)
- 🎯 **Emergency response** for zero-day CVEs

**On vacation?** Everything runs automatically. CRITICAL issues page you, everything else handled.

---

## Quick Start

### Prerequisites

- GitHub account with admin access to all monitored repos
- GitHub token with `repo` and `workflow` permissions
- (Optional) Slack webhook for notifications
- (Optional) PagerDuty integration key for critical alerts

### Setup (5 minutes)

1. **Clone this repo**:
   ```bash
   git clone https://github.com/cboyd0319/security-central
   cd security-central
   ```

2. **Configure repositories**:
   - Edit `config/repos.yml` to add/remove monitored repos
   - Set auto-merge rules per repo

3. **Add GitHub secrets**:
   ```bash
   gh secret set REPO_ACCESS_TOKEN  # Personal access token with repo access
   gh secret set SLACK_SECURITY_WEBHOOK  # Slack incoming webhook URL
   gh secret set PAGERDUTY_INTEGRATION_KEY  # (Optional) PagerDuty key
   ```

4. **Test the scanner**:
   ```bash
   # Trigger manual run
   gh workflow run daily-security-scan.yml
   ```

5. **Done!** Scans run daily at 9 AM UTC automatically.

---

## Features

### Security Scanning

- **Daily vulnerability scans** across all repos
- **Multi-ecosystem support**:
  - Python: `pip-audit`, `safety`, `osv-scanner`
  - Java/JVM: `osv-scanner`, OWASP Dependency-Check
  - npm: `npm audit`
  - PowerShell: `PSScriptAnalyzer`
- **SARIF export** to GitHub Security tab
- **CVE tracking** and prioritization

### Auto-Patching

- **Smart auto-merge** for safe updates:
  - Patch versions (1.0.X)
  - Security fixes
  - High-confidence updates
- **Manual review** for:
  - Minor/major version bumps
  - Breaking changes
  - Low-confidence fixes
- **CI integration**: Only merges if tests pass

### Alerting

- **Slack notifications**:
  - CRITICAL: Immediate alert
  - HIGH: Daily digest
  - MEDIUM/LOW: Weekly summary
- **PagerDuty integration**:
  - CRITICAL issues page you 24/7
  - Configurable severity threshold
- **GitHub Issues**: Auto-creates tracking issues

### Housekeeping (Bonus!)

Weekly automated maintenance:

- 🔄 **Sync GitHub Actions** to latest versions
- 📝 **Update badges** in READMEs
- 🧹 **Clean up old branches** (>90 days)
- 🔧 **Sync common dependencies** (e.g., same Black version everywhere)
- 📋 **Enforce standards** (LICENSE files, .gitignore, etc.)

---

## Configuration

### Monitored Repositories

Edit `config/repos.yml`:

```yaml
repositories:
  - name: PoshGuard
    url: https://github.com/cboyd0319/PoshGuard
    tech_stack: [powershell]
    auto_merge_rules:
      patch: true
      security: true
    notification_threshold: HIGH
```

### Security Policies

Edit `config/security-policies.yml`:

```yaml
severity_mapping:
  CRITICAL:
    cvss_score: 9.0-10.0
    action: immediate_patch
    auto_merge: true
    max_response_time: 2h
```

### Common Dependencies

Edit `config/common-dependencies.yml`:

```yaml
python:
  black: "24.10.0"
  isort: "5.13.2"
  pytest: "8.0.0"
```

---

## Workflows

### Daily Security Scan

**Schedule**: Daily at 9 AM UTC
**Duration**: ~10 minutes
**What it does**:

1. Clone all monitored repos
2. Run security scanners (pip-audit, safety, npm audit, etc.)
3. Triage findings by severity
4. Auto-create PRs for safe fixes
5. Send Slack notifications
6. Upload SARIF to GitHub Security

**Manual trigger**:
```bash
gh workflow run daily-security-scan.yml
```

### Weekly Audit

**Schedule**: Sunday 2 AM UTC
**Duration**: ~20 minutes
**What it does**:

1. Deep dependency analysis
2. Check for outdated packages
3. License compliance scan
4. Dependency health metrics
5. Generate weekly summary report

### Emergency Response

**Trigger**: Manual or webhook
**Use case**: Critical CVE drops while you're on vacation
**What it does**:

1. Assess impact across all repos
2. Auto-create emergency patches
3. Send CRITICAL alerts (PagerDuty)
4. Create incident tracking issue

**Manual trigger**:
```bash
gh workflow run emergency-response.yml \
  -f cve=CVE-2024-12345 \
  -f affected_package=requests \
  -f severity=CRITICAL
```

### Housekeeping

**Schedule**: Monday 3 AM UTC
**Duration**: ~15 minutes
**What it does**:

1. Sync GitHub Actions versions
2. Update common dependencies
3. Clean up old branches
4. Update documentation badges
5. Enforce code standards

---

## Pre-Vacation Checklist

Run this before going on vacation:

```bash
# 1. Update all dependencies NOW
python scripts/pre_vacation_hardening.py

# 2. Test emergency alerts
python scripts/send_pagerduty_alert.py --severity critical --message "Test alert"

# 3. Verify auto-merge is enabled
gh repo edit cboyd0319/PoshGuard --enable-auto-merge
gh repo edit cboyd0319/BazBOM --enable-auto-merge
gh repo edit cboyd0319/JobSentinel --enable-auto-merge
gh repo edit cboyd0319/PyGuard --enable-auto-merge

# 4. Check last scan results
gh run list --workflow=daily-security-scan.yml --limit 1

# 5. Set vacation mode (optional - increases scan frequency)
gh variable set VACATION_MODE --body "true"
```

**During vacation**: Automated. CRITICAL issues page you. Everything else handled.

---

## Reports

All reports saved to `docs/reports/`:

```
docs/reports/
├── daily/
│   └── 2025-10-17-security-report.md
├── weekly/
│   └── 2025-W42-summary.md
└── housekeeping/
    └── 2025-10-17-housekeeping.md
```

View latest report:
```bash
cat docs/reports/daily/$(ls docs/reports/daily | tail -1)
```

---

## Emergency Contact Protocol

**If a CRITICAL CVE drops while you're away:**

1. **Automated** (happens within 2 hours):
   - security-central detects CVE
   - Creates PRs across affected repos
   - Runs CI tests
   - Auto-merges if safe
   - Sends Slack alert

2. **Manual intervention** only if:
   - CI fails
   - Breaking changes detected
   - Multiple major version jumps

3. **Backup contact**: [Set in config/repos.yml]
   - Access via: `${{ secrets.EMERGENCY_BACKUP_TOKEN }}`

4. **Worst case**: Archive affected repo temporarily:
   ```bash
   gh repo archive cboyd0319/REPO_NAME
   ```

---

## Architecture

```
security-central/
├── .github/workflows/       # Automation workflows
│   ├── daily-security-scan.yml
│   ├── weekly-audit.yml
│   ├── emergency-response.yml
│   └── housekeeping.yml
├── config/                  # Configuration
│   ├── repos.yml           # Monitored repositories
│   ├── security-policies.yml
│   └── common-dependencies.yml
├── scripts/                 # Core scripts
│   ├── clone_repos.py
│   ├── scan_all_repos.py
│   ├── analyze_risk.py
│   ├── create_patch_prs.py
│   └── housekeeping/       # Maintenance scripts
└── docs/                    # Reports and documentation
```

---

## Monitoring Dashboard

View security status:

- **GitHub Actions**: [Security Workflows](https://github.com/cboyd0319/security-central/actions)
- **GitHub Security**: [Security Tab](https://github.com/cboyd0319/security-central/security)
- **Latest Report**: `docs/reports/daily/` (committed daily)

---

## Troubleshooting

### Scan failing

```bash
# View logs
gh run list --workflow=daily-security-scan.yml --limit 1
gh run view <RUN_ID> --log

# Re-run failed jobs
gh run rerun <RUN_ID>
```

### PRs not auto-merging

Check:
1. Auto-merge enabled: `gh repo edit cboyd0319/REPO --enable-auto-merge`
2. Branch protection allows auto-merge
3. CI passing: View PR checks
4. PR marked as safe: Check `triage.json` artifact

### Missing notifications

Check:
1. Slack webhook valid: `curl -X POST $SLACK_WEBHOOK -d '{"text":"test"}'`
2. Severity threshold: Edit `config/repos.yml`
3. GitHub secrets set: `gh secret list`

---

## Contributing

This is a personal automation repo, but improvements welcome:

1. Fork and create feature branch
2. Test changes locally
3. Submit PR with clear description

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Maintenance

- **Auto-updates**: Dependabot manages this repo's dependencies
- **Self-scanning**: security-central scans itself daily
- **Monitoring**: Automated alerts if workflows fail

---

**Time investment**:
- Initial setup: 30 minutes
- Weekly maintenance: 15 minutes (reviewing auto-PRs)
- **On vacation**: 0 minutes ☀️

**Questions?** Open an issue or check [docs/](docs/)

---

Made with 🤖 for developers who value their time
