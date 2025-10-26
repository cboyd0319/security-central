#!/usr/bin/env python3
"""
Analyze dependency health metrics.
"""

import argparse
import json
from datetime import datetime, timezone
from typing import Dict, List

from utils import safe_open

# Health score constants
INITIAL_HEALTH_SCORE = 100
SECURITY_PENALTY_PER_FINDING = 10
LICENSE_PENALTY_PER_ISSUE = 5
MAINTENANCE_PENALTY_PER_CONCERN = 3
HEALTHY_THRESHOLD = 80
NEEDS_ATTENTION_THRESHOLD = 50


class DependencyHealthAnalyzer:
    """Analyzer for assessing dependency health metrics and generating health reports."""

    def analyze(self, audit_file: str, output_file: str):
        """Analyze dependency health."""
        with safe_open(audit_file, "r", allowed_base=False) as f:
            audit_data = json.load(f)

        results = {
            "analysis_time": datetime.now(timezone.utc).isoformat(),
            "repositories": [],
            "summary": {"healthy": 0, "needs_attention": 0, "critical": 0},
        }

        for repo in audit_data.get("repositories", []):
            repo_health = self.assess_repository_health(repo)
            results["repositories"].append(repo_health)

            # Update summary
            status = repo_health["health_status"]
            if status == "healthy":
                results["summary"]["healthy"] += 1
            elif status == "needs_attention":
                results["summary"]["needs_attention"] += 1
            else:
                results["summary"]["critical"] += 1

        # Write output
        with safe_open(output_file, "w", allowed_base=False) as f:
            json.dump(results, f, indent=2)

        print(f"\nHealth analysis complete: {output_file}")
        print(f"Healthy: {results['summary']['healthy']}")
        print(f"Needs attention: {results['summary']['needs_attention']}")
        print(f"Critical: {results['summary']['critical']}")

        return results

    def assess_repository_health(self, repo: Dict) -> Dict:
        """Assess health of a single repository."""
        health_score = INITIAL_HEALTH_SCORE
        issues = []

        # Check for security issues
        security_count = len(repo.get("security_findings", []))
        if security_count > 0:
            health_score -= security_count * SECURITY_PENALTY_PER_FINDING
            issues.append(f"{security_count} security findings")

        # Check for license issues
        license_count = len(repo.get("license_issues", []))
        if license_count > 0:
            health_score -= license_count * LICENSE_PENALTY_PER_ISSUE
            issues.append(f"{license_count} license issues")

        # Check for maintenance issues
        maintenance_count = len(repo.get("maintenance_concerns", []))
        if maintenance_count > 0:
            health_score -= maintenance_count * MAINTENANCE_PENALTY_PER_CONCERN
            issues.append(f"{maintenance_count} maintenance concerns")

        # Determine status
        if health_score >= HEALTHY_THRESHOLD:
            status = "healthy"
        elif health_score >= NEEDS_ATTENTION_THRESHOLD:
            status = "needs_attention"
        else:
            status = "critical"

        return {
            "name": repo["name"],
            "health_score": max(0, health_score),
            "health_status": status,
            "issues": issues,
            "recommendations": self.generate_recommendations(repo, health_score),
        }

    def generate_recommendations(self, repo: Dict, health_score: int) -> List[str]:
        """Generate recommendations for improving repository health."""
        recommendations = []

        if len(repo.get("security_findings", [])) > 0:
            recommendations.append("Address security findings immediately")

        if len(repo.get("license_issues", [])) > 0:
            recommendations.append("Add or update LICENSE file")

        if health_score < NEEDS_ATTENTION_THRESHOLD:
            recommendations.append("Repository requires immediate attention")

        return recommendations


def main():
    """Main entry point for dependency health analysis CLI."""
    parser = argparse.ArgumentParser(description="Analyze dependency health")
    parser.add_argument("audit_file", help="Audit results JSON file")
    parser.add_argument("--output", default="health-report.json", help="Output file")
    args = parser.parse_args()

    analyzer = DependencyHealthAnalyzer()
    analyzer.analyze(args.audit_file, args.output)


if __name__ == "__main__":
    main()
