# Security-Central Quickstart

Get up and running in 10 minutes.

## What You Just Got

A **complete automated security system** that:
- ✅ Scans all 4 repos daily for vulnerabilities
- ✅ Auto-patches security fixes
- ✅ Alerts you on Slack/PagerDuty for CRITICAL issues
- ✅ Syncs dependencies and GitHub Actions across repos
- ✅ Works while you're on vacation

## Setup (10 Minutes)

### 1. Run Setup Script

```bash
cd security-central
./setup.sh
```

This installs dependencies and verifies prerequisites.

### 2. Add GitHub Token

```bash
# Create token: https://github.com/settings/tokens/new
# Scopes: repo, workflow

gh secret set REPO_ACCESS_TOKEN
# Paste your token when prompted
```

### 3. (Optional) Add Slack Webhook

```bash
# Get webhook: https://api.slack.com/messaging/webhooks
gh secret set SLACK_SECURITY_WEBHOOK
```

### 4. Push to GitHub

```bash
git add .
git commit -m "chore: initial security-central setup"
git push origin main
```

### 5. Trigger First Scan

```bash
gh workflow run daily-security-scan.yml
```

View results:
```bash
gh run list --workflow=daily-security-scan.yml
gh run view <RUN_ID>
```

## Done!

**Daily scans**: 9 AM UTC automatically
**Weekly audits**: Sunday 2 AM UTC
**Housekeeping**: Monday 3 AM UTC

## Before Vacation

```bash
python3 scripts/pre_vacation_hardening.py
```

This will:
1. Update all dependencies NOW
2. Enable auto-merge
3. Test alerts
4. Verify workflows

Then enjoy your vacation! 🏖️

---

## File Structure

```
security-central/
├── .github/workflows/        # Automation
│   ├── daily-security-scan.yml
│   ├── weekly-audit.yml
│   ├── emergency-response.yml
│   └── housekeeping.yml
├── config/                   # Settings
│   ├── repos.yml            # Edit this!
│   ├── security-policies.yml
│   └── common-dependencies.yml
├── scripts/                  # Core logic
│   ├── scan_all_repos.py
│   ├── create_patch_prs.py
│   └── housekeeping/
└── docs/                     # Reports
```

## Key Files to Edit

1. **config/repos.yml** - Add/remove repositories
2. **config/security-policies.yml** - Adjust severity thresholds
3. **config/common-dependencies.yml** - Sync specific versions

## Monitoring

- **GitHub Actions**: [Workflows](https://github.com/cboyd0319/security-central/actions)
- **Reports**: `docs/reports/daily/`
- **Slack**: #security-alerts channel

## Troubleshooting

**Scans failing?**
```bash
gh run list --workflow=daily-security-scan.yml
gh run view <RUN_ID> --log
```

**PRs not auto-merging?**
```bash
gh repo edit cboyd0319/PoshGuard --enable-auto-merge
```

**No notifications?**
```bash
gh secret list  # Verify secrets are set
```

---

## Full Documentation

- **Complete setup**: [docs/SETUP.md](docs/SETUP.md)
- **Architecture**: [README.md](README.md)
- **Config reference**: [config/](config/)

---

**Questions?** Open an issue or check the docs!
