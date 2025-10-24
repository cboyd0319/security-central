"""Tests for scan_all_repos.py"""

import pytest
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.scan_all_repos import MultiRepoScanner


class TestMultiRepoScanner:
    """Test MultiRepoScanner class."""

    @pytest.fixture
    def scanner(self, temp_config_dir):
        """Create MultiRepoScanner instance with test config."""
        config_file = temp_config_dir / "repos.yml"
        return MultiRepoScanner(str(config_file))

    def test_map_severity(self, scanner):
        """Test severity mapping function."""
        assert scanner.map_severity("critical") == "CRITICAL"
        assert scanner.map_severity("high") == "HIGH"
        assert scanner.map_severity("medium") == "MEDIUM"
        assert scanner.map_severity("moderate") == "MEDIUM"
        assert scanner.map_severity("low") == "LOW"
        assert scanner.map_severity("info") == "LOW"
        assert scanner.map_severity("") == "MEDIUM"
        assert scanner.map_severity(None) == "MEDIUM"
        assert scanner.map_severity("unknown") == "MEDIUM"

    def test_generate_summary(self, scanner, sample_findings):
        """Test summary generation."""
        scanner.findings = sample_findings
        summary = scanner.generate_summary()

        assert summary["total_findings"] == 4
        assert summary["critical_count"] == 1
        assert summary["high_count"] == 1
        assert summary["medium_count"] == 1
        assert summary["low_count"] == 1
        assert "by_severity" in summary
        assert "by_repo" in summary
        assert "by_type" in summary

    def test_severity_to_sarif_level(self, scanner):
        """Test SARIF level mapping."""
        assert scanner.severity_to_sarif_level("CRITICAL") == "error"
        assert scanner.severity_to_sarif_level("HIGH") == "error"
        assert scanner.severity_to_sarif_level("MEDIUM") == "warning"
        assert scanner.severity_to_sarif_level("LOW") == "note"
        assert scanner.severity_to_sarif_level("UNKNOWN") == "warning"

    @patch('subprocess.run')
    def test_scan_python_pip_audit_success(self, mock_run, scanner, tmp_path):
        """Test Python scanning with pip-audit."""
        # Create a fake requirements.txt
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "requirements.txt").write_text("requests==2.28.0\n")

        # Mock pip-audit output
        mock_audit_result = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.28.0",
                    "vulns": [
                        {
                            "id": "CVE-2024-12345",
                            "severity": "HIGH",
                            "description": "Test vulnerability",
                            "fix_versions": ["2.28.2"]
                        }
                    ]
                }
            ]
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_audit_result),
            stderr=""
        )

        findings = scanner.scan_python(str(repo_dir), "test-repo")

        assert len(findings) >= 1
        assert findings[0]["package"] == "requests"
        assert findings[0]["severity"] == "HIGH"
        assert findings[0]["tool"] == "pip-audit"

    @patch('subprocess.run')
    def test_scan_python_handles_errors(self, mock_run, scanner, tmp_path):
        """Test Python scanning handles subprocess errors gracefully."""
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "requirements.txt").write_text("requests==2.28.0\n")

        # Mock subprocess failure
        mock_run.side_effect = subprocess.TimeoutExpired('pip-audit', 120)

        findings = scanner.scan_python(str(repo_dir), "test-repo")

        # Should return empty list, not crash
        assert isinstance(findings, list)

    def test_scan_python_no_requirements_file(self, scanner, tmp_path):
        """Test Python scanning with no requirements files."""
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        findings = scanner.scan_python(str(repo_dir), "test-repo")

        # Should return empty list
        assert findings == []

    @patch('pathlib.Path.glob')
    def test_scan_npm_no_package_json(self, mock_glob, scanner, tmp_path):
        """Test npm scanning when package.json doesn't exist."""
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        mock_glob.return_value = []

        findings = scanner.scan_npm(str(repo_dir), "test-repo")

        assert findings == []

    def test_export_sarif_format(self, scanner, sample_findings, tmp_path):
        """Test SARIF export format."""
        scanner.findings = sample_findings
        output_file = tmp_path / "test.sarif"

        scanner.export_sarif(str(output_file))

        assert output_file.exists()

        # Verify SARIF structure
        with open(output_file) as f:
            sarif = json.load(f)

        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        assert len(sarif["runs"]) == 1
        assert sarif["runs"][0]["tool"]["driver"]["name"] == "security-central"
        assert len(sarif["runs"][0]["results"]) == 4


class TestScanIntegration:
    """Integration tests for scanning."""

    @pytest.fixture
    def mock_repos_dir(self, tmp_path, temp_config_dir):
        """Create mock repos directory structure."""
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()

        # Create test-repo
        test_repo = repos_dir / "test-repo"
        test_repo.mkdir()
        (test_repo / "requirements.txt").write_text("requests==2.28.0\n")

        return repos_dir

    @patch('subprocess.run')
    def test_scan_all_self_scan_fallback(self, mock_run, temp_config_dir):
        """Test that scanner falls back to self-scan when no repos exist."""
        config_file = temp_config_dir / "repos.yml"
        scanner = MultiRepoScanner(str(config_file))

        # Mock empty pip-audit response
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"dependencies": []}',
            stderr=""
        )

        result = scanner.scan_all()

        assert result["total_repos"] == 1  # Self-scan
        assert "findings" in result
        assert "summary" in result
