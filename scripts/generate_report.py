#!/usr/bin/env python3
"""
Generate human-readable security reports.
"""

import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


def generate_report(triage_file: str, output_file: str) -> None:
    """Generate markdown security report from triage results.

    Args:
        triage_file: Path to triage JSON file
        output_file: Path to output markdown report file
    """
    with open(triage_file) as f:
        triage: Dict[str, Any] = json.load(f)

    report_date: str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    report = f"""# Security Scan Report

**Date**: {report_date}
**Total Findings**: {triage['total_findings']}

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | {triage['summary']['critical_count']} |
| HIGH     | {triage['summary']['high_count']} |
| MEDIUM   | {triage['summary']['medium_count']} |
| LOW      | {triage['summary']['low_count']} |

**Auto-fixable**: {triage['summary']['auto_fixable_count']}
**Safe to auto-merge**: {triage['summary']['auto_merge_safe_count']}

## Recommendations

"""

    for rec in triage.get('recommendations', []):
        report += f"- {rec}\n"

    # Critical findings
    if triage['summary']['critical_count'] > 0:
        report += "\n## 🚨 CRITICAL Issues\n\n"
        for finding in triage['triaged']['critical']:
            report += format_finding(finding)

    # High findings
    if triage['summary']['high_count'] > 0:
        report += "\n## ⚠️  HIGH Severity Issues\n\n"
        for finding in triage['triaged']['high'][:10]:  # Limit to 10
            report += format_finding(finding)

    # Auto-fixes
    if triage['summary']['auto_fixable_count'] > 0:
        report += "\n## ✅ Auto-Fixable Issues\n\n"
        for fix in triage['auto_fixes'][:10]:
            report += format_auto_fix(fix)

    # Write report
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(report)

    print(f"Report generated: {output_file}")


def format_finding(finding: Dict[str, Any]) -> str:
    """Format a finding for the report.

    Args:
        finding: Finding dictionary with vulnerability details

    Returns:
        Markdown-formatted finding section
    """
    pkg: str = finding.get('package', finding.get('rule', 'Unknown'))
    cve: str = finding.get('cve', 'N/A')
    repo: str = finding.get('repo', 'Unknown')
    advisory: str = finding.get('advisory', finding.get('message', 'No details available'))[:200]

    return f"""### {pkg} ({cve})

- **Repository**: {repo}
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
    pkg: str = fix.get('package', 'Unknown')
    repo: str = fix.get('repo', 'Unknown')
    confidence: int = fix.get('fix_confidence', 0)
    auto_merge: bool = fix.get('auto_merge_safe', False)

    return f"""### {pkg} in {repo}

- **Current**: {fix.get('version')}
- **Fixed**: {fix.get('fixed_in', ['N/A'])[0]}
- **Confidence**: {confidence}/10
- **Auto-merge**: {'✅ Yes' if auto_merge else '⚠️  Manual review'}

---

"""


def main() -> None:
    """Main entry point for report generation CLI."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Generate security report'
    )
    parser.add_argument('triage_file', help='Triage JSON file')
    parser.add_argument('--output', required=True, help='Output markdown file')
    args: argparse.Namespace = parser.parse_args()

    generate_report(args.triage_file, args.output)


if __name__ == '__main__':
    main()
