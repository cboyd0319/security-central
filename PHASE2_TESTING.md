# Phase 2 Testing Guide

Test the new Phase 2 features **locally tonight** (no GitHub secrets required)!

## What's Ready

✅ **Dependency Intelligence** - Detect version conflicts across repos
✅ **CI/CD Health Monitoring** - Track build health
✅ **Security Dashboard** - Live status page (HTML)

---

## Test Tonight (No Secrets Required)

### 1. Dependency Intelligence

```bash
cd /Users/chadboyd/Documents/GitHub/security-central

# Clone your repos (if not already done)
python3 scripts/clone_repos.py

# Run dependency analysis
python3 scripts/intelligence/dependency_graph.py

# View results
cat dependency-intelligence.json | jq '.summary'
cat docs/reports/dependency-intelligence.md
```

**What it shows**:
- All packages used across your 4 repos
- Version conflicts (e.g., Black 24.x in one repo, 23.x in another)
- Recommended upgrade paths
- Which repo to upgrade first

**Sample output**:
```
Total packages: 156
Shared packages: 42
Version conflicts: 7
High severity: 2
```

---

### 2. CI/CD Health Monitoring

**Requires GitHub CLI authenticated** (run `gh auth login` if needed)

```bash
# Analyze CI health across all repos
python3 scripts/monitoring/ci_health.py

# View results
cat ci-health.json | jq '.overall_health_score'
cat docs/reports/ci-health.md
```

**What it shows**:
- Build success rates
- Flaky test detection
- Build time trends (increasing/decreasing)
- Common failure patterns
- Optimization recommendations

**Sample output**:
```
Overall health: 87.3/100
Healthy repos: 3/4
Needs attention: 1 (JobSentinel - flaky tests detected)
```

**If you don't have `gh` CLI yet**:
```bash
# macOS
brew install gh

# Or skip this test until tomorrow
```

---

### 3. Security Dashboard

```bash
# Open the dashboard in your browser
open dashboard/index.html

# Or serve it locally
python3 -m http.server 8000 --directory dashboard

# Then visit: http://localhost:8000
```

**What you'll see**:
- Overall security score
- Vulnerability counts by severity
- Repository health status
- Recent scan activity chart

**Note**: Currently shows sample data. Tomorrow after running scans, it will show real data.

---

## Tomorrow Morning (After Adding Secrets)

### 1. Add GitHub Secrets

```bash
# Required for workflows to run
gh secret set REPO_ACCESS_TOKEN
# Paste your GitHub PAT

# Optional but recommended
gh secret set SLACK_SECURITY_WEBHOOK
# Paste your Slack webhook URL
```

### 2. Push Everything to GitHub

```bash
cd /Users/chadboyd/Documents/GitHub/security-central

git add .
git commit -m "feat: Phase 2 - dependency intelligence, CI monitoring, dashboard"
git push origin main
```

### 3. Trigger First Scan

```bash
# Manual trigger (faster than waiting for schedule)
gh workflow run daily-security-scan.yml

# Watch it run
gh run watch

# Check results
gh run list --workflow=daily-security-scan.yml
```

### 4. View Dashboard with Real Data

After scans complete, the dashboard will show real metrics:

```bash
# Deploy dashboard to GitHub Pages (optional)
gh workflow run deploy-dashboard.yml
```

Then visit: `https://cboyd0319.github.io/security-central/`

---

## What Each Feature Does

### Dependency Intelligence

**Problem**: You upgrade Black in PyGuard, then JobSentinel breaks because it's using an older version.

**Solution**: This shows you:
- All packages used across all 4 repos
- Which ones have version mismatches
- Predicted breaking changes
- Optimal upgrade order

**Example**:
```
⚠️  black - Version Conflict (Severity: 6/10)
  PyGuard: 24.10.0
  JobSentinel: 23.9.1

  Recommendation: Upgrade JobSentinel first (better test coverage)
  Target version: 24.10.0
```

---

### CI/CD Health Monitoring

**Problem**: Tests fail randomly, builds get slower, but you don't notice until it's a big problem.

**Solution**: Tracks:
- Success rate trends
- Build time changes
- Flaky tests (pass/fail randomly)
- Common failure causes

**Example**:
```
PoshGuard:
  ✅ Success rate: 98% (↑2% from last week)
  ⚠️  Avg build time: 8m 32s (↑12% - investigate)
  🔍 Flaky test detected: Test_SecretScanning (fails 3/10 times)

Recommendations:
  1. Add caching for PowerShell module installation
  2. Fix Test_SecretScanning race condition
```

---

### Security Dashboard

**Problem**: Management wants to see security posture at a glance.

**Solution**: Live dashboard showing:
- Overall security score (0-100)
- Vulnerability breakdown
- Time to patch metrics
- Per-repo health

**Bonus**: Deploy to GitHub Pages for executive-friendly reporting!

---

## Quick Tests (2 Minutes Each)

### Test 1: Find Version Conflicts

```bash
python3 scripts/intelligence/dependency_graph.py
grep -A 5 "Version Conflict" docs/reports/dependency-intelligence.md
```

**Expected**: List of packages used at different versions across repos.

---

### Test 2: Detect Flaky Tests (if gh CLI installed)

```bash
python3 scripts/monitoring/ci_health.py
grep -A 3 "Flaky Workflows" docs/reports/ci-health.md
```

**Expected**: List of workflows that fail intermittently.

---

### Test 3: View Dashboard

```bash
open dashboard/index.html
```

**Expected**: Nice looking dashboard with sample data.

---

## Troubleshooting

### "Module not found: tomli"

```bash
pip3 install tomli
```

### "gh: command not found"

```bash
# macOS
brew install gh

# Or skip CI monitoring test for now
```

### "No repos found"

```bash
# Make sure repos are cloned
python3 scripts/clone_repos.py
ls -la repos/
```

---

## Next Steps

After testing locally:

1. **Tomorrow**: Add secrets and push to GitHub
2. **Week 1**: Monitor dependency intelligence reports
3. **Week 2**: Fix flaky tests identified by CI monitoring
4. **Week 3**: Share security dashboard with team

---

## Files Created

```
scripts/intelligence/
  └── dependency_graph.py          # Dependency conflict detector

scripts/monitoring/
  └── ci_health.py                 # CI/CD health analyzer

dashboard/
  └── index.html                   # Security posture dashboard
```

---

**Sleep well! Tomorrow you'll have a complete DevOps control center running.** 😴

The scripts are ready to run locally right now - no secrets needed for testing!
