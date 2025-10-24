"""Tests for analyze_risk.py"""

import pytest
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.analyze_risk import RiskAnalyzer


class TestRiskAnalyzer:
    """Test RiskAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create RiskAnalyzer instance."""
        return RiskAnalyzer()

    def test_analyze_findings(self, analyzer, temp_findings_file):
        """Test analyzing findings from JSON file."""
        result = analyzer.analyze(str(temp_findings_file))

        assert "triaged" in result
        assert "auto_fixes" in result
        assert "summary" in result
        assert result["total_findings"] == 4
        assert result["summary"]["critical_count"] == 1
        assert result["summary"]["high_count"] == 1

    def test_is_auto_fixable_with_fixed_version(self, analyzer):
        """Test auto-fixable detection with fixed version."""
        finding = {
            "type": "python_dependency",
            "package": "requests",
            "version": "2.28.0",
            "fixed_in": ["2.28.2"]
        }

        assert analyzer.is_auto_fixable(finding) is True

    def test_is_auto_fixable_without_fixed_version(self, analyzer):
        """Test auto-fixable detection without fixed version."""
        finding = {
            "type": "python_dependency",
            "package": "requests",
            "version": "2.28.0",
            "fixed_in": []
        }

        assert analyzer.is_auto_fixable(finding) is False

    def test_is_auto_fixable_code_quality_issue(self, analyzer):
        """Test that code quality issues are not auto-fixable."""
        finding = {
            "type": "powershell_code_quality",
            "rule": "PSAvoidUsingPlainTextForPassword"
        }

        assert analyzer.is_auto_fixable(finding) is False

    def test_is_patch_update_valid(self, analyzer):
        """Test patch version detection."""
        assert analyzer.is_patch_update("2.28.0", "2.28.2") is True
        assert analyzer.is_patch_update("1.0.0", "1.0.1") is True

    def test_is_patch_update_minor_change(self, analyzer):
        """Test that minor version change is not a patch."""
        assert analyzer.is_patch_update("2.28.0", "2.29.0") is False
        assert analyzer.is_patch_update("1.0.0", "1.1.0") is False

    def test_is_patch_update_major_change(self, analyzer):
        """Test that major version change is not a patch."""
        assert analyzer.is_patch_update("2.28.0", "3.0.0") is False
        assert analyzer.is_patch_update("1.0.0", "2.0.0") is False

    def test_is_patch_update_invalid_format(self, analyzer):
        """Test patch detection with invalid version format."""
        assert analyzer.is_patch_update("invalid", "2.28.0") is False
        assert analyzer.is_patch_update("2.28.0", "invalid") is False
        assert analyzer.is_patch_update("2.28", "2.28.0") is False

    def test_is_minor_update_valid(self, analyzer):
        """Test minor version detection."""
        assert analyzer.is_minor_update("2.28.0", "2.29.0") is True
        assert analyzer.is_minor_update("1.0.0", "1.5.0") is True

    def test_is_minor_update_major_change(self, analyzer):
        """Test that major version change is not minor."""
        assert analyzer.is_minor_update("2.28.0", "3.0.0") is False
        assert analyzer.is_minor_update("1.0.0", "2.0.0") is False

    def test_calculate_fix_confidence_patch_version(self, analyzer):
        """Test confidence calculation for patch version update."""
        finding = {
            "type": "python_dependency",
            "package": "requests",
            "version": "2.28.0",
            "fixed_in": ["2.28.2"],
            "tool": "pip-audit",
            "severity": "CRITICAL"
        }

        confidence = analyzer.calculate_fix_confidence(finding)

        # Base 5 + patch 3 + pip-audit 2 + critical 1 = 11, capped at 10
        assert confidence == 10

    def test_calculate_fix_confidence_minor_version(self, analyzer):
        """Test confidence calculation for minor version update."""
        finding = {
            "type": "python_dependency",
            "package": "requests",
            "version": "2.28.0",
            "fixed_in": ["2.29.0"],
            "tool": "safety",
            "severity": "MEDIUM"
        }

        confidence = analyzer.calculate_fix_confidence(finding)

        # Base 5 + minor 1 + safety 2 = 8
        assert confidence == 8

    def test_calculate_fix_confidence_major_version(self, analyzer):
        """Test confidence calculation for major version update."""
        finding = {
            "type": "python_dependency",
            "package": "requests",
            "version": "2.28.0",
            "fixed_in": ["3.0.0"],
            "tool": "other-tool",
            "severity": "LOW"
        }

        confidence = analyzer.calculate_fix_confidence(finding)

        # Base 5 + major -2 = 3
        assert confidence == 3

    def test_is_safe_to_auto_merge_high_confidence_critical(self, analyzer):
        """Test auto-merge safety for high confidence critical fix."""
        finding = {
            "type": "python_dependency",
            "fix_confidence": 9,
            "severity": "CRITICAL",
            "version": "2.28.0",
            "fixed_in": ["2.28.2"]
        }

        assert analyzer.is_safe_to_auto_merge(finding) is True

    def test_is_safe_to_auto_merge_low_confidence(self, analyzer):
        """Test auto-merge safety for low confidence fix."""
        finding = {
            "type": "python_dependency",
            "fix_confidence": 5,
            "severity": "MEDIUM",
            "version": "2.28.0",
            "fixed_in": ["2.28.2"]
        }

        assert analyzer.is_safe_to_auto_merge(finding) is False

    def test_is_safe_to_auto_merge_patch_version(self, analyzer):
        """Test auto-merge safety for patch version."""
        finding = {
            "type": "python_dependency",
            "fix_confidence": 8,
            "severity": "MEDIUM",
            "version": "2.28.0",
            "fixed_in": ["2.28.2"]
        }

        assert analyzer.is_safe_to_auto_merge(finding) is True

    def test_generate_recommendations_critical_findings(self, analyzer):
        """Test recommendations generation with critical findings."""
        triaged = {
            "critical": [{"cve": "CVE-2024-1"}, {"cve": "CVE-2024-2"}],
            "high": [],
            "medium": [],
            "low": []
        }
        auto_fixes = []

        recommendations = analyzer.generate_recommendations(triaged, auto_fixes)

        assert len(recommendations) >= 1
        assert any("CRITICAL" in rec for rec in recommendations)
        assert any("2" in rec for rec in recommendations)

    def test_generate_recommendations_auto_merge_available(self, analyzer):
        """Test recommendations with auto-mergeable fixes."""
        triaged = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        auto_fixes = [
            {"auto_merge_safe": True},
            {"auto_merge_safe": True},
            {"auto_merge_safe": False}
        ]

        recommendations = analyzer.generate_recommendations(triaged, auto_fixes)

        assert any("2" in rec and "auto-merged" in rec for rec in recommendations)
        assert any("1" in rec and "manual review" in rec for rec in recommendations)
