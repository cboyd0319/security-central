# Security-Central Setup Guide

Complete setup guide for automated security monitoring across your repositories.

## Prerequisites

- GitHub account with admin access to all monitored repos
- Git installed locally
- Python 3.12+
- GitHub CLI (`gh`) installed

## Initial Setup (30 minutes)

### 1. Fork or Clone Repository

```bash
# Clone the security-central repo
git clone https://github.com/cboyd0319/security-central
cd security-central
```

### 2. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Install OSV Scanner
curl -LO https://github.com/google/osv-scanner/releases/latest/download/osv-scanner_$(uname -s | tr '[:upper:]' '[:lower:]')_amd64
chmod +x osv-scanner_*
sudo mv osv-scanner_* /usr/local/bin/osv-scanner

# Install OWASP Dependency-Check (for Java projects)
curl -LO https://github.com/jeremylong/DependencyCheck/releases/download/v9.0.9/dependency-check-9.0.9-release.zip
unzip dependency-check-9.0.9-release.zip
sudo mv dependency-check /opt/

# Verify installations
osv-scanner --version
/opt/dependency-check/bin/dependency-check.sh --version
```

### 3. Configure Monitored Repositories

Edit `config/repos.yml`:

```yaml
repositories:
  - name: PoshGuard
    url: https://github.com/cboyd0319/PoshGuard
    tech_stack:
      - powershell
      - pwsh_modules
    auto_merge_rules:
      patch: true          # Auto-merge patch versions
      minor: false         # Require review for minor versions
      security: true       # Always auto-merge security fixes
    notification_threshold: HIGH  # Only notify for HIGH+ severity
```

Repeat for each repo you want to monitor.

### 4. Set Up GitHub Secrets

Create a Personal Access Token:

1. Go to GitHub Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Generate new token with scopes:
   - `repo` (full control of private repositories)
   - `workflow` (update GitHub Actions workflows)
3. Copy the token

Set secrets in security-central repo:

```bash
# Authenticate with GitHub CLI
gh auth login

# Set repository access token
gh secret set REPO_ACCESS_TOKEN
# Paste your PAT when prompted

# Set Slack webhook (optional)
gh secret set SLACK_SECURITY_WEBHOOK
# Paste your Slack incoming webhook URL

# Set PagerDuty key (optional, for critical alerts)
gh secret set PAGERDUTY_INTEGRATION_KEY
# Paste your PagerDuty integration key
```

### 5. Test the Scanner Locally

```bash
# Clone all monitored repos
python scripts/clone_repos.py

# Run a security scan
python scripts/scan_all_repos.py --output test-findings.json

# Analyze results
python scripts/analyze_risk.py test-findings.json --output test-triage.json

# View results
cat test-triage.json | jq '.summary'
```

### 6. Enable GitHub Actions

Push the configuration to GitHub:

```bash
git add .
git commit -m "chore: initial security-central setup"
git push origin main
```

Enable workflows:

```bash
# Verify workflows are enabled
gh workflow list

# Manually trigger first scan
gh workflow run daily-security-scan.yml
```

### 7. Configure Auto-Merge

Enable auto-merge on all monitored repos:

```bash
gh repo edit cboyd0319/PoshGuard --enable-auto-merge
gh repo edit cboyd0319/BazBOM --enable-auto-merge
gh repo edit cboyd0319/JobSentinel --enable-auto-merge
gh repo edit cboyd0319/PyGuard --enable-auto-merge
```

### 8. Test Notifications

Send a test Slack notification:

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text":"🔒 security-central setup complete!"}'
```

Test PagerDuty (if configured):

```bash
python scripts/send_pagerduty_alert.py \
  --severity info \
  --message "security-central test alert"
```

---

## Slack Setup (Optional)

### Create Incoming Webhook

1. Go to your Slack workspace settings
2. Navigate to Apps → Incoming Webhooks
3. Add to Slack → Choose channel (e.g., `#security-alerts`)
4. Copy webhook URL (starts with `https://hooks.slack.com/`)
5. Add to GitHub secrets: `gh secret set SLACK_SECURITY_WEBHOOK`

### Recommended Channels

- `#security-critical` - CRITICAL issues only
- `#security-alerts` - HIGH severity issues
- `#security-daily` - Daily digest

Update `config/repos.yml` to configure channel routing.

---

## PagerDuty Setup (Optional)

### Create Integration

1. Go to PagerDuty → Services
2. Create new service → Name: "security-central"
3. Integration Settings → Events API v2
4. Copy integration key
5. Add to GitHub secrets: `gh secret set PAGERDUTY_INTEGRATION_KEY`

### Configure Escalation

Edit `config/security-policies.yml`:

```yaml
notifications:
  pagerduty:
    enabled: true
    severity_threshold: CRITICAL  # Only page for CRITICAL
```

---

## Verification Checklist

After setup, verify:

- [ ] All repos cloned: `ls repos/` shows all 4 repos
- [ ] Secrets configured: `gh secret list` shows REPO_ACCESS_TOKEN
- [ ] Workflows enabled: `gh workflow list` shows 4 workflows
- [ ] Auto-merge enabled: `gh repo view cboyd0319/PoshGuard --json autoMergeAllowed`
- [ ] First scan succeeded: `gh run list --workflow=daily-security-scan.yml --limit 1`
- [ ] Notifications working: Check Slack/PagerDuty

---

## Maintenance

### Update Security Scanner

```bash
cd security-central
git pull origin main
pip install -r requirements.txt --upgrade
```

### Add New Repository

1. Edit `config/repos.yml`
2. Add repository configuration
3. Commit and push:
   ```bash
   git add config/repos.yml
   git commit -m "chore: add NewRepo to monitoring"
   git push
   ```

### Review Weekly Reports

```bash
# View latest weekly report
cat docs/reports/weekly/$(ls docs/reports/weekly | tail -1)

# View all reports
ls -lh docs/reports/daily/
ls -lh docs/reports/weekly/
```

---

## Troubleshooting

### Scan Failing

```bash
# View workflow logs
gh run list --workflow=daily-security-scan.yml
gh run view <RUN_ID> --log

# Re-run failed workflow
gh run rerun <RUN_ID>
```

### PRs Not Auto-Merging

Common issues:

1. **Auto-merge not enabled**: `gh repo edit <REPO> --enable-auto-merge`
2. **Branch protection**: Check repository Settings → Branches
3. **CI not passing**: View PR checks
4. **Not marked as safe**: Check `triage.json` in workflow artifacts

### Missing Notifications

```bash
# Verify Slack webhook
echo $SLACK_WEBHOOK_URL | curl -X POST "$(cat -)" \
  -d '{"text":"test"}'

# Check notification settings
cat config/repos.yml | grep notification_threshold

# Verify GitHub secrets
gh secret list
```

---

## Advanced Configuration

### Custom Scan Schedule

Edit `.github/workflows/daily-security-scan.yml`:

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours instead of daily
```

### Vacation Mode

Before vacation, increase scan frequency:

```bash
# Set vacation mode variable
gh variable set VACATION_MODE --body "true"
```

Update workflow to check every 15 minutes when in vacation mode.

### Emergency Contacts

Edit `config/repos.yml`:

```yaml
emergency_contacts:
  - name: "Backup Admin"
    email: "backup@example.com"
    phone: "+1-555-0100"
    github: "backupadmin"
```

---

## Next Steps

After setup:

1. **Run pre-vacation script** before first trip:
   ```bash
   python scripts/pre_vacation_hardening.py
   ```

2. **Monitor for one week**: Verify scans run daily

3. **Fine-tune auto-merge rules**: Adjust `config/repos.yml` based on PR volume

4. **Set up status dashboard**: (Optional) Deploy GitHub Pages dashboard

---

## Support

- Issues: https://github.com/cboyd0319/security-central/issues
- Docs: `docs/`
- Config reference: `config/README.md`

---

**Setup complete! Your repos are now monitored 24/7.**
