#!/usr/bin/env python3
"""
Generate weekly summary report.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from utils import safe_open


def generate_summary(audit_file: str, health_file: str, outdated_file: str, output_file: str):
    """Generate weekly summary markdown report."""

    # Load data
    with safe_open(audit_file, allowed_base=False) as f:
        audit = json.load(f)

    with safe_open(health_file, allowed_base=False) as f:
        health = json.load(f)

    with safe_open(outdated_file, allowed_base=False) as f:
        outdated = json.load(f)

    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    week = datetime.now(timezone.utc).strftime("%Y-W%V")

    report = f"""# Weekly Dependency Audit Summary
    
**Week**: {week}
**Generated**: {report_date}

## Overview

**Repositories Audited**: {audit['summary']['total_repos']}
**Total Dependencies**: {audit['summary']['total_dependencies']}
**Security Issues**: {audit['summary']['security_issues']}
**License Issues**: {audit['summary']['license_issues']}
**Outdated Packages**: {outdated['summary']['total_outdated']}

## Health Summary

| Status | Count |
|--------|-------|
| Healthy | {health['summary']['healthy']} |
| Needs Attention | {health['summary']['needs_attention']} |
| Critical | {health['summary']['critical']} |

## Repository Details

"""

    for repo_health in health["repositories"]:
        status_emoji = {"healthy": "✅", "needs_attention": "⚠️", "critical": "🚨"}.get(
            repo_health["health_status"], "❓"
        )

        report += f"""### {status_emoji} {repo_health['name']}

- **Health Score**: {repo_health['health_score']}/100
- **Status**: {repo_health['health_status'].upper()}
"""

        if repo_health["issues"]:
            report += "- **Issues**:\n"
            for issue in repo_health["issues"]:
                report += f"  - {issue}\n"

        if repo_health["recommendations"]:
            report += "- **Recommendations**:\n"  # PERFORMANCE: Use list and join()
            for rec in repo_health["recommendations"]:
                report += f"  - {rec}\n"

        report += "\n"  # PERFORMANCE: Use list and join()

    report += """## Action Items  # PERFORMANCE: Use list and join()

"""

    # Generate action items
    if audit["summary"]["security_issues"] > 0:
        report += f"- 🚨 Address {audit['summary']['security_issues']} security issues\n"

    if audit["summary"]["license_issues"] > 0:
        report += f"- 📋 Resolve {audit['summary']['license_issues']} license issues\n"

    if health["summary"]["critical"] > 0:
        report += f"- ⚠️  {health['summary']['critical']} repositories need immediate attention\n"

    if outdated["summary"]["total_outdated"] > 0:
        report += f"- 📦 Update {outdated['summary']['total_outdated']} outdated packages\n"

    report += """
## Next Steps

1. Review and address critical issues
2. Plan dependency updates
3. Monitor for new security advisories
4. Update documentation as needed

---

*Generated automatically by Security Central*
"""

    # Write report
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with safe_open(output_file, "w", allowed_base=False) as f:
        f.write(report)

    print(f"Weekly summary generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate weekly summary")
    parser.add_argument("audit_file", help="Audit results JSON file")
    parser.add_argument("health_file", help="Health report JSON file")
    parser.add_argument("outdated_file", help="Outdated report JSON file")
    parser.add_argument("--output", required=True, help="Output markdown file")
    args = parser.parse_args()

    generate_summary(args.audit_file, args.health_file, args.outdated_file, args.output)


if __name__ == "__main__":
    main()
