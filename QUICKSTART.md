# Security Central - Quickstart Guide

Get up and running with Security Central in 5 minutes.

---

## Prerequisites

Before you begin, ensure you have:

- GitHub account with admin access to the repositories you want to monitor
- GitHub Personal Access Token with `repo` and `workflow` permissions
- (Optional) Slack workspace with incoming webhook configured
- (Optional) PagerDuty account with integration key for critical alerts

---

## Setup Steps

### 1. Clone the Repository

```bash
git clone https://github.com/cboyd0319/security-central
cd security-central
```

### 2. Configure Your Repositories

Edit `config/repos.yml` to add your repositories:

```yaml
repositories:
  - name: YourRepo
    url: https://github.com/your-username/your-repo
    tech_stack:
      - python  # or powershell, npm, java, kotlin, scala
    security_tools:
      - Bandit
      - Safety
      - pip-audit
    auto_merge_rules:
      patch: true          # Auto-merge patch updates (1.0.X)
      minor: false         # Require review for minor (1.X.0)
      security: true       # Always auto-merge security fixes
      breaking: false      # Never auto-merge breaking changes
    notification_threshold: HIGH  # Only notify for HIGH+ severity
```

### 3. Configure GitHub Secrets

Set up the required secrets in your GitHub repository:

```bash
# Required: GitHub Personal Access Token
gh secret set REPO_ACCESS_TOKEN
# Paste your token when prompted

# Optional: Slack webhook for notifications
gh secret set SLACK_SECURITY_WEBHOOK
# Paste your Slack webhook URL when prompted

# Optional: PagerDuty integration key for critical alerts
gh secret set PAGERDUTY_INTEGRATION_KEY
# Paste your PagerDuty key when prompted
```

**How to create these secrets:**

- **REPO_ACCESS_TOKEN**: Go to GitHub Settings > Developer Settings > Personal Access Tokens > Generate new token (classic). Select `repo` and `workflow` scopes.
- **SLACK_SECURITY_WEBHOOK**: In Slack, go to Apps > Incoming Webhooks > Add to Slack > Choose channel > Copy webhook URL
- **PAGERDUTY_INTEGRATION_KEY**: In PagerDuty, go to Services > Your Service > Integrations > Add Integration > Events API V2 > Copy Integration Key

### 4. Run Initial Setup (Optional)

If you want to install dependencies locally for testing:

```bash
bash setup.sh
```

This will:
- Install Python 3.12+ if needed
- Create a virtual environment
- Install all required dependencies
- Verify configuration files

### 5. Test the Scanner

Trigger a manual workflow run to test:

```bash
gh workflow run daily-security-scan.yml
```

Then check the workflow status:

```bash
gh run list --workflow=daily-security-scan.yml --limit 1
```

### 6. Done!

That's it! Security Central will now:

- Scan all your repositories daily at 9 AM UTC
- Auto-create PRs for security fixes
- Send Slack notifications for HIGH+ severity issues
- Upload findings to GitHub Security tab
- Run weekly audits every Sunday
- Perform housekeeping tasks every Monday

---

## Next Steps

### Enable Auto-Merge (Recommended)

For automatic patch merging to work, enable auto-merge on your repositories:

```bash
gh repo edit your-username/your-repo --enable-auto-merge
```

### Configure Vacation Mode

When going on vacation, increase scan frequency:

```bash
gh variable set VACATION_MODE --body "true"
```

This switches from daily scans to hourly scans and enables more aggressive auto-patching.

### Review Configuration Files

- `config/repos.yml` - Repository definitions and auto-merge rules
- `config/security-policies.yml` - Severity mappings and CVE sources
- `config/common-dependencies.yml` - Synchronized dependency versions
- `config/security-central.yaml` - Scanning schedule and engine config

### Monitor Your Security Status

- **GitHub Actions**: View real-time workflow status at `https://github.com/your-username/security-central/actions`
- **GitHub Security**: See aggregated findings at `https://github.com/your-username/security-central/security`
- **Daily Reports**: Check `docs/reports/daily/` for detailed scan results

---

## Common Workflows

### Manual Security Scan

Trigger an immediate scan across all repositories:

```bash
gh workflow run daily-security-scan.yml
```

### Emergency Response

Respond to a zero-day CVE:

```bash
gh workflow run emergency-response.yml \
  -f cve=CVE-2024-12345 \
  -f affected_package=requests \
  -f severity=CRITICAL
```

### Weekly Audit

Run a deep dependency analysis:

```bash
gh workflow run weekly-audit.yml
```

### Housekeeping

Sync Actions, clean branches, update dependencies:

```bash
gh workflow run housekeeping.yml
```

---

## Troubleshooting

### Workflow Not Running?

Check if the workflow file syntax is correct:

```bash
gh workflow view daily-security-scan.yml
```

### PRs Not Auto-Merging?

Ensure auto-merge is enabled:

```bash
gh repo edit your-username/your-repo --enable-auto-merge
```

And verify branch protection rules allow auto-merge.

### No Slack Notifications?

Test your webhook:

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text":"Test from Security Central"}'
```

---

## Getting Help

- **Documentation**: See `docs/SETUP.md` for detailed setup instructions
- **GitHub Issues**: Report bugs at `https://github.com/cboyd0319/security-central/issues`
- **Examples**: Check `docs/MASTER_PLAN.md` for use cases and roadmap

---

**You're all set!** Security Central is now protecting your repositories.
