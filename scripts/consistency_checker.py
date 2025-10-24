#!/usr/bin/env python3
"""Enforce consistent patterns across all managed repos."""

from pathlib import Path
from typing import Any
import yaml

class ConsistencyChecker:
    """Check for consistency issues across repos."""
    
    REQUIRED_FILES = [
        "README.md",
        "LICENSE",
        "SECURITY.md",
        "CONTRIBUTING.md",
        ".gitignore",
        "pyproject.toml",  # For Python repos
    ]
    
    REQUIRED_SECTIONS_README = [
        "## Features",
        "## Installation",
        "## Usage",
        "## Documentation",
        "## License",
    ]
    
    def __init__(self, repos: list[Path]):
        self.repos = repos
        self.issues = []
        
    def check_all(self) -> dict[str, list[str]]:
        """Run all consistency checks."""
        results = {}
        
        for repo in self.repos:
            repo_issues = []
            
            # Check required files
            repo_issues.extend(self._check_required_files(repo))
            
            # Check README structure
            repo_issues.extend(self._check_readme_structure(repo))
            
            # Check CI/CD presence
            repo_issues.extend(self._check_github_actions(repo))
            
            # Check security policies
            repo_issues.extend(self._check_security_policies(repo))
            
            results[repo.name] = repo_issues
        
        return results
    
    def _check_required_files(self, repo: Path) -> list[str]:
        """Check if required files exist."""
        issues = []
        for required_file in self.REQUIRED_FILES:
            if not (repo / required_file).exists():
                issues.append(f"Missing required file: {required_file}")
        return issues
    
    def _check_readme_structure(self, repo: Path) -> list[str]:
        """Check README has required sections."""
        issues = []
        readme = repo / "README.md"
        
        if not readme.exists():
            return ["README.md not found"]
        
        content = readme.read_text()
        for section in self.REQUIRED_SECTIONS_README:
            if section not in content:
                issues.append(f"README missing section: {section}")
        
        return issues
    
    def _check_github_actions(self, repo: Path) -> list[str]:
        """Check if GitHub Actions workflows exist."""
        issues = []
        workflows_dir = repo / ".github" / "workflows"
        
        if not workflows_dir.exists():
            return ["No GitHub Actions workflows found"]
        
        workflows = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        if len(workflows) == 0:
            issues.append("GitHub Actions directory exists but no workflows found")
        
        # Check for security scanning
        has_security_scan = any(
            "security" in w.name.lower() or "scan" in w.name.lower()
            for w in workflows
        )
        if not has_security_scan:
            issues.append("No security scanning workflow found")
        
        return issues
    
    def _check_security_policies(self, repo: Path) -> list[str]:
        """Check security policy completeness."""
        issues = []
        security_md = repo / "SECURITY.md"
        
        if not security_md.exists():
            return ["SECURITY.md not found"]
        
        content = security_md.read_text()
        
        required_sections = [
            "Reporting",
            "Supported Versions",
        ]
        
        for section in required_sections:
            if section.lower() not in content.lower():
                issues.append(f"SECURITY.md missing section: {section}")
        
        return issues

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    
    checker = ConsistencyChecker(args.repos)
    results = checker.check_all()
    
    # Write results
    with open(args.output, "w") as f:
        yaml.dump(results, f, default_flow_style=False)
    
    # Print summary
    total_issues = sum(len(issues) for issues in results.values())
    print(f"\n✓ Checked {len(args.repos)} repositories")
    print(f"✓ Found {total_issues} consistency issues\n")
    
    for repo, issues in results.items():
        if issues:
            print(f"{repo}:")
            for issue in issues:
                print(f"  • {issue}")
