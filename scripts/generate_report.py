#!/usr/bin/env python3
"""
Generate human-readable security reports.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from utils import safe_open


def generate_report(triage_file: str, output_file: str) -> None:
    """Generate markdown security report from triage results.

    Args:
        triage_file: Path to triage JSON file
        output_file: Path to output markdown report file
    """
    with safe_open(triage_file, allowed_base=False) as f:
        triage: Dict[str, Any] = json.load(f)

    report_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Extract data with backward compatibility
    findings: List[Dict[str, Any]] = triage.get("findings", [])
    auto_fixes: List[Dict[str, Any]] = triage.get("auto_fixes", [])
    summary: Dict[str, Any] = triage.get("summary", {})

    # Count findings by severity
    total_findings = summary.get("total", len(findings))
    critical_count = summary.get("critical", sum(1 for f in findings if f.get("severity") == "CRITICAL"))
    high_count = summary.get("high", sum(1 for f in findings if f.get("severity") == "HIGH"))
    medium_count = summary.get("medium", sum(1 for f in findings if f.get("severity") == "MEDIUM"))
    low_count = summary.get("low", sum(1 for f in findings if f.get("severity") == "LOW"))

    report = f"""# Security Scan Report

**Date**: {report_date}
**Total Findings**: {total_findings}

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | {critical_count} |
| HIGH     | {high_count} |
| MEDIUM   | {medium_count} |
| LOW      | {low_count} |

**Auto-fixable**: {len(auto_fixes)}

## Recommendations

"""

    for rec in triage.get("recommendations", []):
        report += f"- {rec}\n"

    # Group findings by severity
    critical_findings = [f for f in findings if f.get("severity") == "CRITICAL"]
    high_findings = [f for f in findings if f.get("severity") == "HIGH"]
    medium_findings = [f for f in findings if f.get("severity") == "MEDIUM"]

    # Critical findings
    if critical_findings:
        report += "\n## 🚨 CRITICAL Issues\n\n"
        for finding in critical_findings:
            report += format_finding(finding)

    # High findings
    if high_findings:
        report += "\n## ⚠️  HIGH Severity Issues\n\n"
        for finding in high_findings[:10]:  # Limit to 10
            report += format_finding(finding)

    # Medium findings
    if medium_findings:
        report += "\n## ⚡ MEDIUM Severity Issues\n\n"
        for finding in medium_findings[:10]:  # Limit to 10
            report += format_finding(finding)

    # Auto-fixes
    if auto_fixes:
        report += "\n## ✅ Auto-Fixable Issues\n\n"
        for fix in auto_fixes[:10]:
            report += format_auto_fix(fix)

    # Write report
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with safe_open(output_file, "w", allowed_base=False) as f:
        f.write(report)

    print(f"Report generated: {output_file}")


def format_finding(finding: Dict[str, Any]) -> str:
    """Format a finding for the report.

    Args:
        finding: Finding dictionary with vulnerability details

    Returns:
        Markdown-formatted finding section
    """
    pkg: str = finding.get("package", finding.get("rule", "Unknown"))
    cve: str = finding.get("cve", "N/A")
    repo: str = finding.get("repo", "Unknown")
    severity: str = finding.get("severity", "UNKNOWN")
    advisory: str = finding.get("advisory", finding.get("description", finding.get("message", "No details available")))[:200]

    return f"""### [{severity}] {pkg} ({cve})

- **Repository**: {repo}
- **Severity**: {severity}
- **Version**: {finding.get('version', 'N/A')}
- **Advisory**: {advisory}...
- **Fixed in**: {finding.get('fixed_in', 'N/A')}

---

"""


def format_auto_fix(fix: Dict[str, Any]) -> str:
    """Format an auto-fix for the report.

    Args:
        fix: Auto-fix dictionary with package and confidence info

    Returns:
        Markdown-formatted auto-fix section
    """
    pkg: str = fix.get("package", "Unknown")
    repo: str = fix.get("repo", "Unknown")
    current_version: str = fix.get("current_version", fix.get("version", "N/A"))
    fixed_version: str = fix.get("fixed_version", "N/A")
    if isinstance(fix.get("fixed_in"), list):
        fixed_version = fix["fixed_in"][0] if fix["fixed_in"] else "N/A"

    confidence: int = fix.get("fix_confidence", 0)
    auto_merge: bool = fix.get("auto_merge_safe", False)
    pr_number: int = fix.get("pr_number")

    result = f"""### {pkg} in {repo}

- **Current**: {current_version}
- **Fixed**: {fixed_version}
"""

    if pr_number:
        pr_url = fix.get("pr_url", f"PR #{pr_number}")
        result += f"- **PR**: {pr_url}\n"

    if confidence:
        result += f"- **Confidence**: {confidence}/10\n"

    if "auto_merge_safe" in fix:
        result += f"- **Auto-merge**: {'✅ Yes' if auto_merge else '⚠️  Manual review'}\n"

    result += "\n---\n\n"
    return result


def main() -> None:
    """Main entry point for report generation CLI."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Generate security report"
    )
    parser.add_argument("--triage", required=True, help="Triage JSON file")
    parser.add_argument("--output", required=True, help="Output markdown file")
    args: argparse.Namespace = parser.parse_args()

    generate_report(args.triage, args.output)


if __name__ == "__main__":
    main()
