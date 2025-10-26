#!/usr/bin/env python3
"""
Create GitHub issues for major audit concerns.
"""

import argparse
import json
import os
import subprocess

from utils import safe_open


def create_issues(health_file: str):
    """Create GitHub issues for repositories needing attention."""
    with safe_open(health_file, allowed_base=False) as f:
        health = json.load(f)

    issues_created = 0

    for repo in health["repositories"]:
        if repo["health_status"] in ["critical", "needs_attention"]:
            if create_issue_for_repo(repo):
                issues_created += 1

    print(f"Created {issues_created} GitHub issues for repositories needing attention")


def create_issue_for_repo(repo: dict) -> bool:
    """Create a GitHub issue for a repository."""
    # Check if running in GitHub Actions
    if not os.getenv("GITHUB_ACTIONS"):
        print(f"Skipping issue creation for {repo['name']} (not in GitHub Actions)")
        return False

    # In a real implementation, we would use the GitHub API to create issues
    # For now, just print what we would do
    print(f"Would create issue for {repo['name']}:")
    print(f"  Status: {repo['health_status']}")
    print(f"  Score: {repo['health_score']}/100")
    print(f"  Issues: {', '.join(repo['issues'])}")

    return False


def main():
    parser = argparse.ArgumentParser(description="Create audit issues")
    parser.add_argument("health_file", help="Health report JSON file")
    args = parser.parse_args()

    create_issues(args.health_file)


if __name__ == "__main__":
    main()
