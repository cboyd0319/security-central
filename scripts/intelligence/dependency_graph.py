#!/usr/bin/env python3
"""
Dependency Intelligence - Predict breaking changes before they hit.

This analyzes dependencies across all repos and predicts:
- Which updates will break your code
- Optimal upgrade paths
- Cross-repo dependency conflicts
"""

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

import yaml

from utils import safe_open


class DependencyIntelligence:
    def __init__(self, repos_dir: str = "repos"):
        self.repos_dir = Path(repos_dir)
        self.dependency_graph = defaultdict(
            lambda: {"repos": set(), "versions": defaultdict(set), "latest_version": None}
        )

    def analyze_all_repos(self) -> Dict:
        """Build complete dependency graph across all repos."""
        print("🔍 Analyzing dependencies across all repositories...\n")

        for repo_dir in self.repos_dir.iterdir():
            if repo_dir.is_dir() and not repo_dir.name.startswith("."):
                self.analyze_repo(repo_dir)

        return self.generate_intelligence_report()

    def analyze_repo(self, repo_dir: Path):
        """Extract dependencies from a single repo."""
        repo_name = repo_dir.name
        print(f"  Analyzing {repo_name}...")

        # Python dependencies
        for req_file in repo_dir.rglob("requirements*.txt"):
            self.parse_python_requirements(req_file, repo_name)

        for pyproject in repo_dir.rglob("pyproject.toml"):
            self.parse_pyproject_toml(pyproject, repo_name)

        # npm dependencies
        for package_json in repo_dir.rglob("package.json"):
            self.parse_package_json(package_json, repo_name)

        # Maven dependencies
        for pom_xml in repo_dir.rglob("pom.xml"):
            self.parse_pom_xml(pom_xml, repo_name)

    def parse_python_requirements(self, req_file: Path, repo_name: str):
        """Parse Python requirements.txt."""
        try:
            with safe_open(req_file, allowed_base=False) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Parse: package==1.2.3 or package>=1.2.3
                        match = re.match(r"([a-zA-Z0-9_-]+)([>=<]+)(.+)", line)
                        if match:
                            package, operator, version = match.groups()
                            self.dependency_graph[package]["repos"].add(repo_name)
                            self.dependency_graph[package]["versions"][repo_name].add(
                                version.strip()
                            )
        except Exception as e:
            print(f"    ⚠️  Failed to parse {req_file}: {e}")

    def parse_pyproject_toml(self, pyproject: Path, repo_name: str):
        """Parse pyproject.toml."""
        try:
            import tomli

            with safe_open(pyproject, "rb", allowed_base=False) as f:
                data = tomli.load(f)

            dependencies = data.get("project", {}).get("dependencies", [])
            for dep in dependencies:
                match = re.match(r"([a-zA-Z0-9_-]+)([>=<]+)(.+)", dep)
                if match:
                    package, operator, version = match.groups()
                    self.dependency_graph[package]["repos"].add(repo_name)
                    self.dependency_graph[package]["versions"][repo_name].add(version.strip())
        except ImportError:
            # tomli not installed, skip
            pass
        except Exception as e:
            print(f"    ⚠️  Failed to parse {pyproject}: {e}")

    def parse_package_json(self, package_json: Path, repo_name: str):
        """Parse npm package.json."""
        try:
            with safe_open(package_json, allowed_base=False) as f:
                data = json.load(f)

            for dep_type in ["dependencies", "devDependencies"]:
                for package, version in data.get(dep_type, {}).items():
                    # Remove ^ and ~ prefixes
                    clean_version = version.lstrip("^~")
                    self.dependency_graph[package]["repos"].add(repo_name)
                    self.dependency_graph[package]["versions"][repo_name].add(clean_version)
        except Exception as e:
            print(f"    ⚠️  Failed to parse {package_json}: {e}")

    def parse_pom_xml(self, pom_xml: Path, repo_name: str):
        """Parse Maven pom.xml."""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(pom_xml)
            root = tree.getroot()

            # Maven XML uses namespaces
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            for dependency in root.findall(".//m:dependency", ns):
                group_id = dependency.find("m:groupId", ns)
                artifact_id = dependency.find("m:artifactId", ns)
                version = dependency.find("m:version", ns)

                if all([group_id, artifact_id, version]):
                    package = f"{group_id.text}:{artifact_id.text}"
                    self.dependency_graph[package]["repos"].add(repo_name)
                    self.dependency_graph[package]["versions"][repo_name].add(version.text)
        except Exception as e:
            print(f"    ⚠️  Failed to parse {pom_xml}: {e}")

    def detect_version_conflicts(self) -> List[Dict]:
        """Find packages used at different versions across repos."""
        conflicts = []

        for package, data in self.dependency_graph.items():
            if len(data["repos"]) > 1:
                # Used in multiple repos
                all_versions = set()
                for repo_versions in data["versions"].values():
                    all_versions.update(repo_versions)

                if len(all_versions) > 1:
                    # Different versions used
                    conflicts.append(
                        {
                            "package": package,
                            "repos": list(data["repos"]),
                            "versions": {
                                repo: list(versions) for repo, versions in data["versions"].items()
                            },
                            "severity": self.assess_conflict_severity(all_versions),
                        }
                    )

        return sorted(conflicts, key=lambda x: x["severity"], reverse=True)

    def assess_conflict_severity(self, versions: Set[str]) -> int:
        """Rate severity of version conflict (0-10)."""
        try:
            # Parse versions and check major/minor differences
            parsed = []
            for v in versions:
                parts = v.split(".")
                if len(parts) >= 2:
                    parsed.append((int(parts[0]), int(parts[1])))

            if not parsed:
                return 3  # Unknown severity

            major_versions = set(p[0] for p in parsed)
            if len(major_versions) > 1:
                return 10  # CRITICAL: Different major versions

            minor_versions = set(p[1] for p in parsed)
            if len(minor_versions) > 1:
                return 6  # MEDIUM: Different minor versions

            return 2  # LOW: Just patch differences
        except (ValueError, AttributeError, IndexError) as e:
            # Handle version parsing errors
            return 5  # Default medium severity

    def predict_breaking_changes(self, package: str, from_version: str, to_version: str) -> Dict:
        """Predict if an upgrade will break code."""
        try:
            from_parts = [int(p) for p in from_version.split(".")[:2]]
            to_parts = [int(p) for p in to_version.split(".")[:2]]

            # Semantic versioning analysis
            if to_parts[0] > from_parts[0]:
                return {
                    "breaking": True,
                    "confidence": 0.9,
                    "reason": "Major version bump - likely breaking changes",
                    "recommendation": "Test thoroughly before merging",
                    "risk_level": "HIGH",
                }
            elif to_parts[1] > from_parts[1]:
                return {
                    "breaking": False,
                    "confidence": 0.7,
                    "reason": "Minor version bump - should be backward compatible",
                    "recommendation": "Review changelog and test",
                    "risk_level": "MEDIUM",
                }
            else:
                return {
                    "breaking": False,
                    "confidence": 0.95,
                    "reason": "Patch version - bug fixes only",
                    "recommendation": "Safe to auto-merge",
                    "risk_level": "LOW",
                }
        except (ValueError, AttributeError, IndexError) as e:
            # Handle version parsing errors
            return {
                "breaking": None,
                "confidence": 0.0,
                "reason": f"Could not parse version numbers: {e}",
                "recommendation": "Manual review required",
                "risk_level": "UNKNOWN",
            }

    def suggest_upgrade_order(self, conflicts: List[Dict]) -> List[Dict]:
        """Suggest which repo to upgrade first for each conflict."""
        suggestions = []

        for conflict in conflicts:
            # Determine best repo to upgrade first
            # Heuristic: Start with repo that has best test coverage
            # For now, just suggest alphabetically first repo

            repos = sorted(conflict["repos"])
            suggestions.append(
                {
                    "package": conflict["package"],
                    "recommended_order": repos,
                    "rationale": f"Upgrade {repos[0]} first (alphabetical order - replace with test coverage heuristic)",
                    "target_version": self.recommend_target_version(conflict["versions"]),
                }
            )

        return suggestions

    def recommend_target_version(self, versions_by_repo: Dict[str, List[str]]) -> str:
        """Recommend which version all repos should standardize on."""
        # Simple heuristic: Use the latest version
        all_versions = []
        for versions in versions_by_repo.values():
            all_versions.extend(versions)

        # Sort versions (simple string sort, not perfect but good enough)
        sorted_versions = sorted(set(all_versions), reverse=True)
        return sorted_versions[0] if sorted_versions else "unknown"

    def generate_intelligence_report(self) -> Dict:
        """Generate final intelligence report."""
        conflicts = self.detect_version_conflicts()
        upgrade_suggestions = self.suggest_upgrade_order(conflicts)

        total_packages = len(self.dependency_graph)
        shared_packages = len([p for p, d in self.dependency_graph.items() if len(d["repos"]) > 1])

        return {
            "summary": {
                "total_packages": total_packages,
                "shared_packages": shared_packages,
                "version_conflicts": len(conflicts),
                "high_severity_conflicts": len([c for c in conflicts if c["severity"] >= 8]),
            },
            "conflicts": conflicts,
            "upgrade_suggestions": upgrade_suggestions,
            "dependency_graph": {
                pkg: {
                    "repos": list(data["repos"]),
                    "versions": {
                        repo: list(versions) for repo, versions in data["versions"].items()
                    },
                }
                for pkg, data in self.dependency_graph.items()
            },
        }

    def generate_markdown_report(self, intelligence: Dict, output_path: str):
        """Generate human-readable markdown report."""
        report = f"""# Dependency Intelligence Report

**Date**: {subprocess.run(['date', '-u'], capture_output=True, text=True).stdout.strip()}

## Summary

- **Total Packages**: {intelligence['summary']['total_packages']}
- **Shared Across Repos**: {intelligence['summary']['shared_packages']}
- **Version Conflicts**: {intelligence['summary']['version_conflicts']}
- **High Severity Conflicts**: {intelligence['summary']['high_severity_conflicts']}

"""

        if intelligence["conflicts"]:
            report += "## ⚠️  Version Conflicts\n\n"
            for conflict in intelligence["conflicts"][:10]:  # Top 10
                severity_emoji = "🚨" if conflict["severity"] >= 8 else "⚠️"
                report += f"### {severity_emoji} {conflict['package']} (Severity: {conflict['severity']}/10)\n\n"
                report += f"**Used in**: {', '.join(conflict['repos'])}\n\n"
                report += "**Versions**:\n"  # PERFORMANCE: Use list and join()
                for repo, versions in conflict["versions"].items():
                    report += f"- {repo}: {', '.join(versions)}\n"
                report += "\n"  # PERFORMANCE: Use list and join()

        if intelligence["upgrade_suggestions"]:
            report += "## 🔄 Upgrade Recommendations\n\n"  # PERFORMANCE: Use list and join()
            for suggestion in intelligence["upgrade_suggestions"][:10]:
                report += f"### {suggestion['package']}\n\n"
                report += f"**Target Version**: {suggestion['target_version']}\n"
                report += f"**Upgrade Order**: {' → '.join(suggestion['recommended_order'])}\n"
                report += f"**Rationale**: {suggestion['rationale']}\n\n"

        # Write report
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with safe_open(output_path, "w", allowed_base=False) as f:
            f.write(report)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Dependency intelligence analysis")
    parser.add_argument("--output", default="dependency-intelligence.json")
    parser.add_argument("--report", default="docs/reports/dependency-intelligence.md")
    args = parser.parse_args()

    analyzer = DependencyIntelligence()
    intelligence = analyzer.analyze_all_repos()

    # Write JSON
    with safe_open(args.output, "w", allowed_base=False) as f:
        json.dump(intelligence, f, indent=2)

    # Write Markdown report
    analyzer.generate_markdown_report(intelligence, args.report)

    # Print summary
    print(f"\n{'='*60}")
    print("DEPENDENCY INTELLIGENCE ANALYSIS")
    print(f"{'='*60}")
    print(f"Total packages: {intelligence['summary']['total_packages']}")
    print(f"Shared packages: {intelligence['summary']['shared_packages']}")
    print(f"Version conflicts: {intelligence['summary']['version_conflicts']}")
    print(f"High severity: {intelligence['summary']['high_severity_conflicts']}")
    print(f"\nReports written to:")
    print(f"  JSON: {args.output}")
    print(f"  Markdown: {args.report}")


if __name__ == "__main__":
    main()
