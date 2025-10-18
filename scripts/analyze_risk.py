#!/usr/bin/env python3
"""
Analyze and triage security findings by risk level.
"""

import json
import argparse
from typing import Dict, List
from datetime import datetime


class RiskAnalyzer:
    def __init__(self, config_path: str = 'config/security-policies.yml'):
        self.config_path = config_path

    def analyze(self, findings_file: str) -> Dict:
        """Analyze findings and prioritize by risk."""
        with open(findings_file) as f:
            data = json.load(f)

        findings = data.get('findings', [])

        # Triage findings
        triaged = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        auto_fixes = []

        for finding in findings:
            severity = finding.get('severity', 'MEDIUM')
            category = severity.lower()

            if category in triaged:
                triaged[category].append(finding)

            # Determine if auto-fixable
            if self.is_auto_fixable(finding):
                auto_fixes.append({
                    **finding,
                    'fix_confidence': self.calculate_fix_confidence(finding),
                    'auto_merge_safe': self.is_safe_to_auto_merge(finding)
                })

        return {
            'analysis_time': datetime.utcnow().isoformat(),
            'total_findings': len(findings),
            'triaged': triaged,
            'auto_fixes': auto_fixes,
            'summary': {
                'critical_count': len(triaged['critical']),
                'high_count': len(triaged['high']),
                'medium_count': len(triaged['medium']),
                'low_count': len(triaged['low']),
                'auto_fixable_count': len(auto_fixes),
                'auto_merge_safe_count': len([f for f in auto_fixes if f['auto_merge_safe']])
            },
            'recommendations': self.generate_recommendations(triaged, auto_fixes)
        }

    def is_auto_fixable(self, finding: Dict) -> bool:
        """Determine if a finding can be auto-fixed."""
        # Dependency vulnerabilities with known fixed versions
        if finding['type'] in ['python_dependency', 'npm_dependency', 'jvm_dependency']:
            if finding.get('fixed_in'):
                return True

        return False

    def calculate_fix_confidence(self, finding: Dict) -> int:
        """Calculate confidence score (0-10) for auto-fix."""
        confidence = 5  # Base score

        # Higher confidence for patch versions
        fixed_version = str(finding.get('fixed_in', [''])[0])
        current_version = str(finding.get('version', ''))

        if self.is_patch_update(current_version, fixed_version):
            confidence += 3
        elif self.is_minor_update(current_version, fixed_version):
            confidence += 1
        else:
            confidence -= 2  # Major version jump

        # Higher confidence for well-known tools
        if finding.get('tool') in ['pip-audit', 'safety', 'npm-audit']:
            confidence += 2

        # Higher confidence for CRITICAL/HIGH severity
        if finding.get('severity') in ['CRITICAL', 'HIGH']:
            confidence += 1

        return min(10, max(0, confidence))

    def is_safe_to_auto_merge(self, finding: Dict) -> bool:
        """Determine if fix is safe to auto-merge."""
        # Only auto-merge if high confidence
        if finding.get('fix_confidence', 0) < 7:
            return False

        # Only auto-merge patch and security updates
        if finding.get('severity') in ['CRITICAL', 'HIGH']:
            return True

        # Patch versions are generally safe
        fixed_version = str(finding.get('fixed_in', [''])[0])
        current_version = str(finding.get('version', ''))

        return self.is_patch_update(current_version, fixed_version)

    def is_patch_update(self, current: str, fixed: str) -> bool:
        """Check if update is just a patch version bump."""
        try:
            current_parts = current.split('.')
            fixed_parts = fixed.split('.')

            if len(current_parts) >= 3 and len(fixed_parts) >= 3:
                return (current_parts[0] == fixed_parts[0] and
                        current_parts[1] == fixed_parts[1])
        except:
            pass
        return False

    def is_minor_update(self, current: str, fixed: str) -> bool:
        """Check if update is a minor version bump."""
        try:
            current_parts = current.split('.')
            fixed_parts = fixed.split('.')

            if len(current_parts) >= 2 and len(fixed_parts) >= 2:
                return current_parts[0] == fixed_parts[0]
        except:
            pass
        return False

    def generate_recommendations(self, triaged: Dict, auto_fixes: List[Dict]) -> List[str]:
        """Generate action recommendations."""
        recommendations = []

        critical_count = len(triaged['critical'])
        high_count = len(triaged['high'])
        auto_merge_count = len([f for f in auto_fixes if f['auto_merge_safe']])

        if critical_count > 0:
            recommendations.append(
                f"🚨 URGENT: {critical_count} CRITICAL vulnerabilities found. "
                f"Immediate action required."
            )

        if high_count > 0:
            recommendations.append(
                f"⚠️  {high_count} HIGH severity issues. "
                f"Address within 24 hours."
            )

        if auto_merge_count > 0:
            recommendations.append(
                f"✅ {auto_merge_count} fixes can be safely auto-merged."
            )

        if len(auto_fixes) > auto_merge_count:
            manual_review = len(auto_fixes) - auto_merge_count
            recommendations.append(
                f"👀 {manual_review} fixes available but require manual review."
            )

        return recommendations


def main():
    parser = argparse.ArgumentParser(description='Analyze and triage security findings')
    parser.add_argument('findings_file', help='Input findings JSON file')
    parser.add_argument('--output', default='triage.json', help='Output triage file')
    args = parser.parse_args()

    analyzer = RiskAnalyzer()
    triage = analyzer.analyze(args.findings_file)

    # Write output
    with open(args.output, 'w') as f:
        json.dump(triage, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("RISK ANALYSIS COMPLETE")
    print("="*60)
    print(f"CRITICAL: {triage['summary']['critical_count']}")
    print(f"HIGH:     {triage['summary']['high_count']}")
    print(f"MEDIUM:   {triage['summary']['medium_count']}")
    print(f"LOW:      {triage['summary']['low_count']}")
    print(f"\nAuto-fixable: {triage['summary']['auto_fixable_count']}")
    print(f"Safe to auto-merge: {triage['summary']['auto_merge_safe_count']}")

    if triage['recommendations']:
        print("\nRECOMMENDATIONS:")
        for rec in triage['recommendations']:
            print(f"  {rec}")

    print(f"\nTriage results written to {args.output}")


if __name__ == '__main__':
    main()
