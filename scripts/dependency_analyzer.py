#!/usr/bin/env python3
"""Analyze dependencies for supply chain risks."""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Any
import requests

@dataclass
class DependencyRisk:
    name: str
    version: str
    risk_score: float  # 0-100
    issues: list[str]
    
    def to_dict(self) -> dict:
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
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        
    def analyze_python_deps(self) -> list[DependencyRisk]:
        """Analyze Python dependencies."""
        risks = []
        
        # Get dependencies
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            cwd=self.repo_path
        )
        deps = json.loads(result.stdout)
        
        for dep in deps:
            name = dep["name"]
            version = dep["version"]
            
            # Check PyPI metadata
            issues = []
            risk_score = 0.0
            
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
    
    def _get_pypi_metadata(self, package_name: str) -> dict[str, Any] | None:
        """Fetch package metadata from PyPI."""
        try:
            resp = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=5)
            if resp.status_code == 200:
                return resp.json()["info"]
        except Exception:
            pass
        return None
    
    def _is_typosquat(self, package_name: str) -> bool:
        """Check if package name looks like typosquatting."""
        POPULAR_PACKAGES = [
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
        """Calculate Levenshtein distance."""
        if len(s1) < len(s2):
            return SupplyChainAnalyzer._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    
    analyzer = SupplyChainAnalyzer(args.repo)
    risks = analyzer.analyze_python_deps()
    
    with open(args.output, "w") as f:
        json.dump([r.to_dict() for r in risks], f, indent=2)
    
    print(f"✓ Found {len(risks)} high-risk dependencies")
    for risk in sorted(risks, key=lambda x: x.risk_score, reverse=True)[:5]:
        print(f"  • {risk.name} (score: {risk.risk_score:.1f})")
