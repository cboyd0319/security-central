#!/usr/bin/env python3
"""
Analyze and triage security findings by risk level.
"""

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils import safe_open

# Fix confidence scoring constants
BASE_CONFIDENCE_SCORE = 5
PATCH_UPDATE_BONUS = 3
MINOR_UPDATE_BONUS = 1
MAJOR_UPDATE_PENALTY = 2
KNOWN_TOOL_BONUS = 2
HIGH_SEVERITY_BONUS = 1
MAX_CONFIDENCE_SCORE = 10
MIN_CONFIDENCE_SCORE = 0
AUTO_MERGE_CONFIDENCE_THRESHOLD = 7


class RiskAnalyzer:
    """Analyze and triage security findings by risk level and auto-fix potential.

    Attributes:
        config_path: Path to security policies configuration file
    """

    def __init__(self, config_path: str = "config/security-policies.yml") -> None:
        """Initialize the risk analyzer.

        Args:
            config_path: Path to security policies configuration file
        """
        self.config_path: str = config_path

    def analyze(self, findings_file: str) -> Dict[str, Any]:
        """Analyze findings and prioritize by risk.

        Args:
            findings_file: Path to JSON file containing security findings

        Returns:
            Dictionary containing triaged findings, auto-fixes, and recommendations
        """
        with safe_open(findings_file, "r", allowed_base=False) as f:
            data: Dict[str, Any] = json.load(f)

        findings: List[Dict[str, Any]] = data.get("findings", [])

        # Triage findings
        triaged: Dict[str, List[Dict[str, Any]]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        auto_fixes: List[Dict[str, Any]] = []

        for finding in findings:
            severity = finding.get("severity", "MEDIUM")
            category = severity.lower()

            if category in triaged:
                triaged[category].append(finding)

            # Determine if auto-fixable
            if self.is_auto_fixable(finding):
                auto_fixes.append(
                    {
                        **finding,
                        "fix_confidence": self.calculate_fix_confidence(finding),
                        "auto_merge_safe": self.is_safe_to_auto_merge(finding),
                    }
                )

        return {
            "analysis_time": datetime.now(timezone.utc).isoformat(),
            "total_findings": len(findings),
            "triaged": triaged,
            "auto_fixes": auto_fixes,
            "summary": {
                "critical_count": len(triaged["critical"]),
                "high_count": len(triaged["high"]),
                "medium_count": len(triaged["medium"]),
                "low_count": len(triaged["low"]),
                "auto_fixable_count": len(auto_fixes),
                "auto_merge_safe_count": len([f for f in auto_fixes if f["auto_merge_safe"]]),
            },
            "recommendations": self.generate_recommendations(triaged, auto_fixes),
        }

    def is_auto_fixable(self, finding: Dict[str, Any]) -> bool:
        """Determine if a finding can be auto-fixed.

        Args:
            finding: Security finding dictionary

        Returns:
            True if the finding can be automatically fixed
        """
        # Dependency vulnerabilities with known fixed versions
        if finding["type"] in ["python_dependency", "npm_dependency", "jvm_dependency"]:
            if finding.get("fixed_in"):
                return True

        return False

    def calculate_fix_confidence(self, finding: Dict[str, Any]) -> int:
        """Calculate confidence score (0-10) for auto-fix.

        Args:
            finding: Security finding dictionary

        Returns:
            Confidence score from 0 (low) to 10 (high)
        """
        confidence: int = BASE_CONFIDENCE_SCORE

        # Higher confidence for patch versions
        fixed_version = str(finding.get("fixed_in", [""])[0])
        current_version = str(finding.get("version", ""))

        if self.is_patch_update(current_version, fixed_version):
            confidence += PATCH_UPDATE_BONUS
        elif self.is_minor_update(current_version, fixed_version):
            confidence += MINOR_UPDATE_BONUS
        else:
            confidence -= MAJOR_UPDATE_PENALTY  # Major version jump

        # Higher confidence for well-known tools
        if finding.get("tool") in ["pip-audit", "safety", "npm-audit"]:
            confidence += KNOWN_TOOL_BONUS

        # Higher confidence for CRITICAL/HIGH severity
        if finding.get("severity") in ["CRITICAL", "HIGH"]:
            confidence += HIGH_SEVERITY_BONUS

        return min(MAX_CONFIDENCE_SCORE, max(MIN_CONFIDENCE_SCORE, confidence))

    def is_safe_to_auto_merge(self, finding: Dict[str, Any]) -> bool:
        """Determine if fix is safe to auto-merge.

        Args:
            finding: Security finding dictionary with fix_confidence

        Returns:
            True if the fix is safe to auto-merge without review
        """
        # Only auto-merge if high confidence
        if finding.get("fix_confidence", 0) < AUTO_MERGE_CONFIDENCE_THRESHOLD:
            return False

        # Only auto-merge patch and security updates
        if finding.get("severity") in ["CRITICAL", "HIGH"]:
            return True

        # Patch versions are generally safe
        fixed_version = str(finding.get("fixed_in", [""])[0])
        current_version = str(finding.get("version", ""))

        return self.is_patch_update(current_version, fixed_version)

    def is_patch_update(self, current: str, fixed: str) -> bool:
        """Check if update is just a patch version bump (e.g., 2.0.1 -> 2.0.2).

        Args:
            current: Current version string
            fixed: Fixed version string

        Returns:
            True if major and minor versions match (only patch differs)
        """
        try:
            current_parts = current.split(".")
            fixed_parts = fixed.split(".")

            if len(current_parts) >= 3 and len(fixed_parts) >= 3:
                return current_parts[0] == fixed_parts[0] and current_parts[1] == fixed_parts[1]
        except (AttributeError, IndexError, ValueError) as e:
            # Handle invalid version formats gracefully
            return False
        return False

    def is_minor_update(self, current: str, fixed: str) -> bool:
        """Check if update is a minor version bump (e.g., 2.0.0 -> 2.1.0).

        Args:
            current: Current version string
            fixed: Fixed version string

        Returns:
            True if major version matches (only minor/patch differ)
        """
        try:
            current_parts = current.split(".")
            fixed_parts = fixed.split(".")

            if len(current_parts) >= 2 and len(fixed_parts) >= 2:
                return current_parts[0] == fixed_parts[0]
        except (AttributeError, IndexError, ValueError) as e:
            # Handle invalid version formats gracefully
            return False
        return False

    def generate_recommendations(
        self,
        triaged: Dict[str, List[Dict[str, Any]]],
        auto_fixes: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate action recommendations based on findings.

        Args:
            triaged: Dictionary of findings categorized by severity
            auto_fixes: List of auto-fixable findings

        Returns:
            List of recommendation strings
        """
        recommendations: List[str] = []

        critical_count: int = len(triaged["critical"])
        high_count: int = len(triaged["high"])
        auto_merge_count: int = len([f for f in auto_fixes if f["auto_merge_safe"]])

        if critical_count > 0:
            recommendations.append(
                f"🚨 URGENT: {critical_count} CRITICAL vulnerabilities found. "
                f"Immediate action required."
            )

        if high_count > 0:
            recommendations.append(
                f"⚠️  {high_count} HIGH severity issues. " f"Address within 24 hours."
            )

        if auto_merge_count > 0:
            recommendations.append(f"✅ {auto_merge_count} fixes can be safely auto-merged.")

        if len(auto_fixes) > auto_merge_count:
            manual_review: int = len(auto_fixes) - auto_merge_count
            recommendations.append(f"👀 {manual_review} fixes available but require manual review.")

        return recommendations


def main() -> None:
    """Main entry point for risk analysis CLI."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Analyze and triage security findings"
    )
    parser.add_argument("findings_file", help="Input findings JSON file")
    parser.add_argument("--output", default="triage.json", help="Output triage file")
    args: argparse.Namespace = parser.parse_args()

    analyzer: RiskAnalyzer = RiskAnalyzer()
    triage: Dict[str, Any] = analyzer.analyze(args.findings_file)

    # Write output
    with safe_open(args.output, "w", allowed_base=False) as f:
        json.dump(triage, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("RISK ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"CRITICAL: {triage['summary']['critical_count']}")
    print(f"HIGH:     {triage['summary']['high_count']}")
    print(f"MEDIUM:   {triage['summary']['medium_count']}")
    print(f"LOW:      {triage['summary']['low_count']}")
    print(f"\nAuto-fixable: {triage['summary']['auto_fixable_count']}")
    print(f"Safe to auto-merge: {triage['summary']['auto_merge_safe_count']}")

    if triage["recommendations"]:
        print("\nRECOMMENDATIONS:")
        for rec in triage["recommendations"]:
            print(f"  {rec}")

    print(f"\nTriage results written to {args.output}")


if __name__ == "__main__":
    main()
