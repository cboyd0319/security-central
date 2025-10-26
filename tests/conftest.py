"""Pytest configuration and shared fixtures."""

import json
from pathlib import Path
from typing import Dict, List

import pytest


@pytest.fixture
def sample_findings() -> List[Dict]:
    """Sample vulnerability findings for testing."""
    return [
        {
            "repo": "test-repo",
            "type": "python_dependency",
            "severity": "CRITICAL",
            "package": "requests",
            "version": "2.28.0",
            "cve": "CVE-2024-12345",
            "advisory": "Critical security vulnerability in requests",
            "fixed_in": ["2.28.2"],
            "tool": "pip-audit",
            "file": "requirements.txt",
        },
        {
            "repo": "test-repo",
            "type": "python_dependency",
            "severity": "HIGH",
            "package": "django",
            "version": "3.2.0",
            "cve": "CVE-2024-67890",
            "advisory": "SQL injection vulnerability",
            "fixed_in": ["3.2.18"],
            "tool": "safety",
            "file": "requirements.txt",
        },
        {
            "repo": "test-repo",
            "type": "python_dependency",
            "severity": "MEDIUM",
            "package": "flask",
            "version": "2.0.0",
            "cve": "CVE-2024-11111",
            "advisory": "XSS vulnerability",
            "fixed_in": ["2.0.3"],
            "tool": "pip-audit",
            "file": "requirements.txt",
        },
        {
            "repo": "test-repo",
            "type": "python_dependency",
            "severity": "LOW",
            "package": "pytest",
            "version": "7.0.0",
            "cve": "CVE-2024-22222",
            "advisory": "Minor information disclosure",
            "fixed_in": ["7.4.0"],
            "tool": "safety",
            "file": "requirements-dev.txt",
        },
    ]


@pytest.fixture
def sample_repos_config() -> Dict:
    """Sample repos.yml configuration for testing."""
    return {
        "repositories": [
            {
                "name": "test-repo",
                "url": "https://github.com/test/test-repo",
                "tech_stack": ["python"],
                "security_tools": ["pip-audit", "safety", "bandit"],
                "auto_merge_rules": {
                    "patch": True,
                    "minor": False,
                    "security": True,
                    "breaking": False,
                },
                "notification_threshold": "HIGH",
            },
            {
                "name": "test-repo-2",
                "url": "https://github.com/test/test-repo-2",
                "tech_stack": ["python", "npm"],
                "security_tools": ["pip-audit", "npm-audit"],
                "auto_merge_rules": {
                    "patch": True,
                    "minor": False,
                    "security": True,
                    "breaking": False,
                },
                "notification_threshold": "MEDIUM",
            },
        ],
        "notifications": {
            "slack": {"enabled": True, "webhook_url_secret": "SLACK_SECURITY_WEBHOOK"}
        },
        "safety_checks": {
            "require_ci_pass": True,
            "require_no_breaking_changes": True,
            "max_version_jump": {"major": 0, "minor": 2, "patch": 10},
        },
    }


@pytest.fixture
def sample_security_config() -> Dict:
    """Sample security-central.yaml configuration."""
    return {
        "version": "1.0",
        "project": {"name": "security-central", "owner": "test-user"},
        "scanning": {
            "schedule": "0 9 * * *",
            "parallel_scans": 4,
            "timeout_minutes": 30,
            "fail_on_critical": True,
        },
        "security_policies": {
            "max_critical_age_days": 1,
            "max_high_age_days": 7,
            "max_medium_age_days": 30,
            "block_on_secrets": True,
            "require_sarif": True,
        },
    }


@pytest.fixture
def temp_findings_file(tmp_path, sample_findings) -> Path:
    """Create a temporary findings JSON file."""
    findings_file = tmp_path / "findings.json"
    findings_data = {
        "scan_time": "2024-01-01T00:00:00+00:00",
        "total_repos": 1,
        "findings": sample_findings,
        "summary": {
            "total_findings": len(sample_findings),
            "by_severity": {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 1, "LOW": 1},
            "critical_count": 1,
            "high_count": 1,
            "medium_count": 1,
            "low_count": 1,
        },
    }
    findings_file.write_text(json.dumps(findings_data, indent=2))
    return findings_file


@pytest.fixture
def temp_config_dir(tmp_path, sample_repos_config, sample_security_config):
    """Create temporary config directory with test configs."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Write repos.yml
    import yaml

    repos_file = config_dir / "repos.yml"
    repos_file.write_text(yaml.dump(sample_repos_config))

    # Write security-central.yaml
    security_file = config_dir / "security-central.yaml"
    security_file.write_text(yaml.dump(sample_security_config))

    return config_dir
