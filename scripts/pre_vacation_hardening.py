#!/usr/bin/env python3
"""
Pre-vacation hardening script - Run this before going on vacation!
"""

import subprocess
import yaml
import sys
from pathlib import Path
from datetime import datetime


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def run_command(cmd: list, description: str) -> bool:
    """Run a command and report status."""
    print(f"  ⏳ {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"  ✅ {description} - DONE")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ {description} - FAILED")
        print(f"     Error: {e.stderr}")
        return False


def main():
    print_header("🏖️  Pre-Vacation Security Hardening")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load config
    with open('config/repos.yml') as f:
        config = yaml.safe_load(f)

    repos = config['repositories']
    total_checks = 0
    passed_checks = 0

    # 1. Clone/Update all repos
    print_header("Step 1: Update All Repositories")
    if run_command(['python', 'scripts/clone_repos.py'], "Clone/update all repos"):
        passed_checks += 1
    total_checks += 1

    # 2. Run immediate security scan
    print_header("Step 2: Security Scan (Pre-Departure)")
    if run_command(
        ['python', 'scripts/scan_all_repos.py', '--output', 'pre-vacation-scan.json'],
        "Scan for vulnerabilities"
    ):
        passed_checks += 1
    total_checks += 1

    # Check if any CRITICAL issues
    try:
        import json
        with open('pre-vacation-scan.json') as f:
            scan_results = json.load(f)

        critical_count = scan_results.get('summary', {}).get('critical_count', 0)
        high_count = scan_results.get('summary', {}).get('high_count', 0)

        if critical_count > 0:
            print(f"\n  ⚠️  WARNING: {critical_count} CRITICAL issues found!")
            print("     Consider fixing before vacation.")
        elif high_count > 0:
            print(f"\n  ⚠️  {high_count} HIGH severity issues found.")
            print("     Review before leaving.")
        else:
            print(f"\n  ✅ No critical issues found")
            passed_checks += 1
        total_checks += 1
    except Exception as e:
        print(f"  ❌ Could not analyze scan results: {e}")
        total_checks += 1

    # 3. Enable auto-merge on all repos
    print_header("Step 3: Enable Auto-Merge")
    for repo in repos:
        repo_name = repo['name']
        if run_command(
            ['gh', 'repo', 'edit', f"cboyd0319/{repo_name}", '--enable-auto-merge'],
            f"Enable auto-merge for {repo_name}"
        ):
            passed_checks += 1
        total_checks += 1

    # 4. Test Slack notifications
    print_header("Step 4: Test Alert Systems")

    slack_webhook = subprocess.run(
        ['gh', 'secret', 'list'],
        capture_output=True, text=True
    ).stdout

    if 'SLACK_SECURITY_WEBHOOK' in slack_webhook:
        print("  ✅ Slack webhook configured")
        passed_checks += 1
    else:
        print("  ⚠️  Slack webhook NOT configured")
        print("     Set with: gh secret set SLACK_SECURITY_WEBHOOK")
    total_checks += 1

    # 5. Verify GitHub token
    print_header("Step 5: Verify GitHub Access")
    if run_command(['gh', 'auth', 'status'], "Check GitHub authentication"):
        passed_checks += 1
    total_checks += 1

    # 6. Check workflow status
    print_header("Step 6: Verify Workflows")
    if run_command(
        ['gh', 'workflow', 'list'],
        "List workflows"
    ):
        print("\n  Verify these workflows are enabled:")
        print("    - daily-security-scan.yml")
        print("    - emergency-response.yml")
        print("    - weekly-audit.yml")
        passed_checks += 1
    total_checks += 1

    # 7. Create backup emergency token
    print_header("Step 7: Emergency Backup")
    print("  ℹ️  Share these with a trusted backup contact:")
    print(f"     - GitHub: https://github.com/cboyd0319/security-central")
    print(f"     - Emergency token: gh secret get REPO_ACCESS_TOKEN")
    print(f"     - Manual emergency response:")
    print(f"       gh workflow run emergency-response.yml \\")
    print(f"         -f cve=CVE-XXXX-XXXXX \\")
    print(f"         -f affected_package=PACKAGE \\")
    print(f"         -f severity=CRITICAL")

    # Final summary
    print_header("Pre-Vacation Hardening Complete")

    pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    print(f"  Checks passed: {passed_checks}/{total_checks} ({pass_rate:.1f}%)\n")

    if pass_rate >= 90:
        print("  ✅ All systems operational. Enjoy your vacation! 🏖️ \n")
        return 0
    elif pass_rate >= 70:
        print("  ⚠️  Some issues found. Review warnings above.\n")
        return 0
    else:
        print("  ❌ Critical issues found. Do NOT leave until resolved!\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
