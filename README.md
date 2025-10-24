<div align="center">
  <img src="docs/brand/security-central-logo.svg" width="120" alt="Security Central logo">
  <h1>Security Central</h1>
  <p><strong>Automated security monitoring for multi-repo projects</strong></p>
  <p>Daily scans • Auto-patching • Emergency response • Zero manual work</p>
</div>

<div align="center">
[![Daily Security Scan](https://github.com/cboyd0319/security-central/actions/workflows/daily-security-scan.yml/badge.svg)](https://github.com/cboyd0319/security-central/actions/workflows/daily-security-scan.yml)
[![Weekly Audit](https://github.com/cboyd0319/security-central/actions/workflows/weekly-audit.yml/badge.svg)](https://github.com/cboyd0319/security-central/actions/workflows/weekly-audit.yml)

[Quickstart](#-quickstart) •
[Features](#-features) •
[Workflows](#-workflows) •
[Configuration](#-configuration)
</div>

---

## What is Security Central?

**The problem:** Managing security across 4+ disconnected projects with different tech stacks (PowerShell, Python, Java/Kotlin/Scala, React) is impossible while holding a day job. Manual vulnerability monitoring doesn't scale.

**The solution:** Security Central automatically scans all your repos daily, auto-patches safe security fixes, alerts you for CRITICAL issues, and handles housekeeping—so you can focus on building instead of maintaining.

### Who is this for?

- **Solo developers** maintaining multiple projects across different tech stacks
- **Small teams** without dedicated security engineers
- **Open source maintainers** juggling security across repos
- **Developers on vacation** who need automated security without manual work

### What's New

- **Multi-ecosystem support** (Python, Java/Kotlin/Scala, PowerShell, npm)
- **Smart auto-merge** only patches safe, tested updates
- **Emergency response workflow** for zero-day CVEs
- **Vacation mode** increases scan frequency when you're away
- **PagerDuty integration** for CRITICAL alerts 24/7
- **Automated housekeeping** syncs Actions, cleans branches, updates badges

---

## Quickstart

### Prerequisites

- GitHub account with admin access to monitored repos
- GitHub token with `repo` and `workflow` permissions
- (Optional) Slack webhook for notifications
- (Optional) PagerDuty integration key for critical alerts

### Setup (5 Minutes)

**1. Clone this repo:**

```bash
git clone https://github.com/cboyd0319/security-central
cd security-central
```

**2. Configure repositories:**

Edit `config/repos.yml` to add/remove monitored repos and set auto-merge rules.

**3. Add GitHub secrets:**

```bash
gh secret set REPO_ACCESS_TOKEN  # Personal access token with repo access
gh secret set SLACK_SECURITY_WEBHOOK  # Slack incoming webhook URL
gh secret set PAGERDUTY_INTEGRATION_KEY  # (Optional) PagerDuty key
```

**4. Test the scanner:**

```bash
# Trigger manual run
gh workflow run daily-security-scan.yml
```

**5. Done!** Scans run daily at 9 AM UTC automatically.

---

## Features

<table>
<tr>
<td width="50%">

**Security Scanning**
- **Daily vulnerability scans** across all repos
- **Multi-ecosystem support**:
  - Python: pip-audit, safety, osv-scanner
  - Java/JVM: osv-scanner, OWASP Dependency-Check
  - npm: npm audit
  - PowerShell: PSScriptAnalyzer
- **SARIF export** to GitHub Security tab
- **CVE tracking** and prioritization
- **Severity-based triage** (CRITICAL/HIGH/MEDIUM/LOW)

**Auto-Patching**
- **Smart auto-merge** for safe updates:
  - Patch versions (1.0.X)
  - Security fixes
  - High-confidence updates
- **Manual review** for:
  - Minor/major version bumps
  - Breaking changes
  - Low-confidence fixes
- **CI integration** - Only merges if tests pass

**Alerting**
- **Slack notifications**:
  - CRITICAL: Immediate alert
  - HIGH: Daily digest
  - MEDIUM/LOW: Weekly summary
- **PagerDuty integration**:
  - CRITICAL issues page you 24/7
  - Configurable severity threshold
- **GitHub Issues** - Auto-creates tracking issues

</td>
<td width="50%">

**Housekeeping** (Bonus!)
- **Sync GitHub Actions** to latest versions
- **Update badges** in READMEs
- **Clean up old branches** (>90 days)
- **Sync common dependencies** (same Black version everywhere)
- **Enforce standards** (LICENSE files, .gitignore)
- **Weekly automation** - Runs Monday 3 AM UTC

**Emergency Response**
- **Zero-day CVE handling** while you're on vacation
- **Impact assessment** across all repos
- **Auto-create emergency patches**
- **CRITICAL alerts** via PagerDuty
- **Incident tracking** via GitHub Issues
- **Manual trigger** for specific CVEs

**Vacation Mode**
- **Increased scan frequency** (hourly instead of daily)
- **Automated decision-making** for safe patches
- **Emergency contact fallback** for manual intervention
- **Auto-archive** affected repos as last resort
- **Enable with:** `gh variable set VACATION_MODE --body "true"`

**Monitoring Dashboard**
- **GitHub Actions** - Real-time workflow status
- **GitHub Security** - Aggregated findings
- **Daily reports** - Committed to docs/reports/
- **Trend tracking** - Security posture over time

</td>
</tr>
</table>

---

## Workflows

### Daily Security Scan

**Schedule:** Daily at 9 AM UTC
**Duration:** ~10 minutes

**What it does:**
1. Clone all monitored repos
2. Run security scanners (pip-audit, safety, npm audit, etc.)
3. Triage findings by severity
4. Auto-create PRs for safe fixes
5. Send Slack notifications
6. Upload SARIF to GitHub Security

**Manual trigger:**
```bash
gh workflow run daily-security-scan.yml
```

### Weekly Audit

**Schedule:** Sunday 2 AM UTC
**Duration:** ~20 minutes

**What it does:**
1. Deep dependency analysis
2. Check for outdated packages
3. License compliance scan
4. Dependency health metrics
5. Generate weekly summary report

### Emergency Response

**Trigger:** Manual or webhook
**Use case:** Critical CVE drops while you're on vacation

**What it does:**
1. Assess impact across all repos
2. Auto-create emergency patches
3. Send CRITICAL alerts (PagerDuty)
4. Create incident tracking issue

**Manual trigger:**
```bash
gh workflow run emergency-response.yml \
  -f cve=CVE-2024-12345 \
  -f affected_package=requests \
  -f severity=CRITICAL
```

### Housekeeping

**Schedule:** Monday 3 AM UTC
**Duration:** ~15 minutes

**What it does:**
1. Sync GitHub Actions versions
2. Update common dependencies
3. Clean up old branches
4. Update documentation badges
5. Enforce code standards

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

---

## Troubleshooting

### Common Issues

<details>
<summary><strong>Error: Scan workflow failing</strong></summary>

**Cause:** Workflow errors or repository access issues

**Fix:**

```bash
# View workflow logs
gh run list --workflow=daily-security-scan.yml --limit 1
gh run view <RUN_ID> --log

# Re-run failed jobs
gh run rerun <RUN_ID>

# Check repository access
gh repo view cboyd0319/REPO_NAME
```

</details>

<details>
<summary><strong>PRs not auto-merging</strong></summary>

**Cause:** Auto-merge disabled, CI failing, or branch protection rules

**Fix:**

```bash
# 1. Enable auto-merge on repo
gh repo edit cboyd0319/REPO --enable-auto-merge

# 2. Check branch protection settings allow auto-merge

# 3. Verify CI passing on PR
gh pr view <PR_NUMBER> --json statusCheckRollup

# 4. Check if PR marked as safe
# Download triage.json artifact from workflow run
```

</details>

<details>
<summary><strong>Missing Slack notifications</strong></summary>

**Cause:** Invalid webhook, wrong severity threshold, or missing secrets

**Fix:**

```bash
# Test Slack webhook
curl -X POST "$SLACK_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"text":"Test alert from security-central"}'

# Check severity threshold in config
cat config/repos.yml | grep notification_threshold

# Verify GitHub secrets are set
gh secret list
```

</details>

<details>
<summary><strong>Emergency response not triggering</strong></summary>

**Cause:** Workflow syntax error or missing parameters

**Fix:**

```bash
# Trigger manually with all required parameters
gh workflow run emergency-response.yml \
  -f cve=CVE-2024-12345 \
  -f affected_package=package-name \
  -f severity=CRITICAL

# Check workflow syntax
cat .github/workflows/emergency-response.yml
```

</details>

**More help:**
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [GitHub Discussions](https://github.com/cboyd0319/security-central/discussions)

---

## Contributing

This is a personal automation repo, but improvements are welcome!

**Before submitting:**
- Test changes locally
- Update documentation if needed
- Submit PR with clear description

**Quick start:**
```bash
git clone https://github.com/cboyd0319/security-central
cd security-central
# Make your changes
# Test workflows
```

---

## License

**MIT License** - See [LICENSE](LICENSE) for full text.

```
✅ Commercial use allowed
✅ Modification allowed
✅ Distribution allowed
✅ Private use allowed
📋 License and copyright notice required
```

**TL;DR:** Use it however you want. Just include the license.

Learn more: https://choosealicense.com/licenses/mit/

---

## Support & Monitoring

**Monitoring Dashboard:**
- [GitHub Actions](https://github.com/cboyd0319/security-central/actions) - Real-time workflow status
- [GitHub Security](https://github.com/cboyd0319/security-central/security) - Security findings
- [Daily Reports](docs/reports/daily/) - Latest scan results

**Need help?**
- [GitHub Issues](https://github.com/cboyd0319/security-central/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/cboyd0319/security-central/discussions) - Questions and ideas
- [Documentation](docs/) - Setup guides and examples

### Maintenance Summary

- **Auto-updates:** Dependabot manages this repo's dependencies
- **Self-scanning:** security-central scans itself daily
- **Monitoring:** Automated alerts if workflows fail

**Time investment:**
- Initial setup: **30 minutes**
- Weekly maintenance: **15 minutes** (reviewing auto-PRs)
- **On vacation: 0 minutes** ☀️

---

<div align="center">

## ⭐ Spread the Word

If Security Central helps automate your security workflow, **give us a star** ⭐

[![Star History](https://img.shields.io/github/stars/cboyd0319/security-central?style=social)](https://github.com/cboyd0319/security-central/stargazers)

**Automated** • **Vacation-Ready** • **Multi-Ecosystem**

Made with 🤖 for developers who value their time

[⬆ Back to top](#security-central)

</div>
