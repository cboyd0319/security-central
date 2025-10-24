#!/usr/bin/env python3
"""Analyze dependencies for supply chain risks."""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Any
import sys
import os

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import create_session_with_retries, retry_on_exception
import requests

@dataclass
class DependencyRisk:
    """Represents a dependency with supply chain risk analysis.

    Attributes:
        name: Package name
        version: Package version
        risk_score: Risk score from 0-100
        issues: List of identified risk indicators
    """
    name: str
    version: str
    risk_score: float  # 0-100
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "risk_score": self.risk_score,
            "issues": self.issues
        }

class SupplyChainAnalyzer:
    """Analyze supply chain risks in dependencies."""
    
    RISK_INDICATORS = {
        "typosquatting": 20,
        "no_github_repo": 15,
        "single_maintainer": 10,
        "recent_ownership_change": 25,
        "no_recent_commits": 15,
        "missing_security_policy": 10,
        "uses_exec_eval": 30,
        "network_access": 15,
        "filesystem_access": 15,
    }
    
    def __init__(self, repo_path: Path) -> None:
        """Initialize the supply chain analyzer.

        Args:
            repo_path: Path to repository to analyze
        """
        self.repo_path: Path = repo_path
        # Create session with retry logic for PyPI queries
        self.session = create_session_with_retries(
            total_retries=3,
            backoff_factor=0.5
        )
        
    def analyze_python_deps(self) -> list[DependencyRisk]:
        """Analyze Python dependencies for supply chain risks.

        Returns:
            List of high-risk dependencies (score > 50)
        """
        risks: list[DependencyRisk] = []
        
        # Get dependencies
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            cwd=self.repo_path
        )
        deps = json.loads(result.stdout)
        
        for dep in deps:
            name: str = dep["name"]
            version: str = dep["version"]

            # Check PyPI metadata
            issues: list[str] = []
            risk_score: float = 0.0
            
            metadata = self._get_pypi_metadata(name)
            if metadata:
                # Check for typosquatting
                if self._is_typosquat(name):
                    issues.append("Potential typosquatting")
                    risk_score += self.RISK_INDICATORS["typosquatting"]
                
                # Check maintainer count
                if len(metadata.get("maintainers", [])) == 1:
                    issues.append("Single maintainer")
                    risk_score += self.RISK_INDICATORS["single_maintainer"]
                    
                # Check for source repo
                if not metadata.get("project_urls", {}).get("Source"):
                    issues.append("No source repository")
                    risk_score += self.RISK_INDICATORS["no_github_repo"]
            
            if risk_score > 50:  # Only report high-risk deps
                risks.append(DependencyRisk(name, version, risk_score, issues))
        
        return risks
    
    @retry_on_exception(
        max_attempts=3,
        delay=0.5,
        exceptions=(requests.RequestException,)
    )
    def _get_pypi_metadata(self, package_name: str) -> dict[str, Any] | None:
        """Fetch package metadata from PyPI with automatic retries.

        Args:
            package_name: Name of the package to fetch metadata for

        Returns:
            Package metadata dictionary or None if not found
        """
        try:
            resp = self.session.get(
                f"https://pypi.org/pypi/{package_name}/json",
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()["info"]
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # Package not found - don't retry
                return None
            raise  # Retry other HTTP errors
        except (KeyError, ValueError) as e:
            # Handle missing keys or invalid JSON
            print(f"    ⚠️  Invalid metadata for {package_name}: {e}")
            return None
    
    def _is_typosquat(self, package_name: str) -> bool:
        """Check if package name looks like typosquatting.

        Args:
            package_name: Package name to check

        Returns:
            True if package name is suspiciously similar to popular package
        """
        POPULAR_PACKAGES: list[str] = [
            "requests", "numpy", "pandas", "django", "flask",
            "boto3", "pytest", "setuptools", "wheel"
        ]
        
        for popular in POPULAR_PACKAGES:
            # Levenshtein distance check
            if self._levenshtein(package_name.lower(), popular) <= 2:
                if package_name.lower() != popular:
                    return True
        return False
    
    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Edit distance between the two strings
        """
        if len(s1) < len(s2):
            return SupplyChainAnalyzer._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row: range = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row: list[int] = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

if __name__ == "__main__":
    import argparse
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    analyzer: SupplyChainAnalyzer = SupplyChainAnalyzer(args.repo)
    risks: list[DependencyRisk] = analyzer.analyze_python_deps()
    
    with open(args.output, "w") as f:
        json.dump([r.to_dict() for r in risks], f, indent=2)
    
    print(f"✓ Found {len(risks)} high-risk dependencies")
    for risk in sorted(risks, key=lambda x: x.risk_score, reverse=True)[:5]:
        print(f"  • {risk.name} (score: {risk.risk_score:.1f})")
