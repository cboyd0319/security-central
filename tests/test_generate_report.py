#!/usr/bin/env python3
"""
Comprehensive tests for scripts/generate_report.py

Tests security report generation functionality.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_report import (
    generate_report,
    format_finding,
    format_auto_fix,
    main,
)


class TestGenerateReport:
    """Test generate_report function."""

    @pytest.fixture
    def sample_triage_data(self):
        """Create sample triage data."""
        return {
            'findings': [
                {
                    'repo': 'test-app',
                    'severity': 'CRITICAL',
                    'package': 'requests',
                    'cve': 'CVE-2024-1234',
                    'description': 'Critical vulnerability',
                    'fixed_in': ['2.28.0']
                },
                {
                    'repo': 'test-app',
                    'severity': 'HIGH',
                    'package': 'django',
                    'cve': 'CVE-2024-5678',
                    'description': 'High severity issue',
                    'fixed_in': ['4.1.0']
                }
            ],
            'auto_fixes': [
                {
                    'package': 'requests',
                    'current_version': '2.27.0',
                    'fixed_version': '2.28.0',
                    'pr_number': 123
                }
            ],
            'summary': {
                'total': 2,
                'critical': 1,
                'high': 1,
                'medium': 0,
                'low': 0
            }
        }

    def test_generate_report_creates_file(self, sample_triage_data):
        """Test that generate_report creates output file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as triage_f:
            json.dump(sample_triage_data, triage_f)
            triage_file = triage_f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            generate_report(triage_file, report_file)

            # Verify report file was created
            assert os.path.exists(report_file)

            # Verify report has content
            with open(report_file) as f:
                content = f.read()
                assert len(content) > 0
                assert 'Security Report' in content or 'CRITICAL' in content
        finally:
            os.unlink(triage_file)
            if os.path.exists(report_file):
                os.unlink(report_file)

    def test_generate_report_includes_findings(self, sample_triage_data):
        """Test that report includes all findings."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as triage_f:
            json.dump(sample_triage_data, triage_f)
            triage_file = triage_f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            generate_report(triage_file, report_file)

            with open(report_file) as f:
                content = f.read()

                # Check findings are included
                assert 'CVE-2024-1234' in content
                assert 'CVE-2024-5678' in content
                assert 'requests' in content
                assert 'django' in content
        finally:
            os.unlink(triage_file)
            if os.path.exists(report_file):
                os.unlink(report_file)

    def test_generate_report_includes_summary(self, sample_triage_data):
        """Test that report includes summary statistics."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as triage_f:
            json.dump(sample_triage_data, triage_f)
            triage_file = triage_f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            generate_report(triage_file, report_file)

            with open(report_file) as f:
                content = f.read()

                # Check summary is included
                assert '2' in content  # Total
                assert '1' in content  # Critical count
        finally:
            os.unlink(triage_file)
            if os.path.exists(report_file):
                os.unlink(report_file)

    def test_generate_report_empty_findings(self):
        """Test generating report with no findings."""
        empty_data = {
            'findings': [],
            'auto_fixes': [],
            'summary': {
                'total': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as triage_f:
            json.dump(empty_data, triage_f)
            triage_file = triage_f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            generate_report(triage_file, report_file)

            # Report should still be created
            assert os.path.exists(report_file)

            with open(report_file) as f:
                content = f.read()
                assert len(content) > 0
        finally:
            os.unlink(triage_file)
            if os.path.exists(report_file):
                os.unlink(report_file)

    def test_generate_report_missing_triage_file(self):
        """Test handling of missing triage file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            with pytest.raises(FileNotFoundError):
                generate_report('nonexistent-file.json', report_file)
        finally:
            if os.path.exists(report_file):
                os.unlink(report_file)

    def test_generate_report_invalid_json(self):
        """Test handling of invalid JSON in triage file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as triage_f:
            triage_f.write("invalid json content {")
            triage_file = triage_f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                generate_report(triage_file, report_file)
        finally:
            os.unlink(triage_file)
            if os.path.exists(report_file):
                os.unlink(report_file)


class TestFormatFinding:
    """Test format_finding function."""

    def test_format_finding_basic(self):
        """Test basic finding formatting."""
        finding = {
            'repo': 'test-app',
            'severity': 'CRITICAL',
            'package': 'requests',
            'cve': 'CVE-2024-1234',
            'description': 'Test vulnerability',
            'fixed_in': ['2.28.0']
        }

        result = format_finding(finding)

        assert isinstance(result, str)
        assert 'CRITICAL' in result
        assert 'requests' in result
        assert 'CVE-2024-1234' in result

    def test_format_finding_all_severities(self):
        """Test formatting findings with different severities."""
        severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

        for severity in severities:
            finding = {
                'repo': 'test-app',
                'severity': severity,
                'package': 'test-pkg',
                'cve': f'CVE-2024-{severity}',
                'description': f'{severity} issue',
                'fixed_in': ['1.0.0']
            }

            result = format_finding(finding)

            assert severity in result
            assert 'test-pkg' in result

    def test_format_finding_no_fixed_version(self):
        """Test formatting finding without fixed version."""
        finding = {
            'repo': 'test-app',
            'severity': 'HIGH',
            'package': 'vulnerable-pkg',
            'cve': 'CVE-2024-9999',
            'description': 'No fix available',
            'fixed_in': []
        }

        result = format_finding(finding)

        assert isinstance(result, str)
        assert 'vulnerable-pkg' in result

    def test_format_finding_multiple_fixed_versions(self):
        """Test formatting finding with multiple fixed versions."""
        finding = {
            'repo': 'test-app',
            'severity': 'MEDIUM',
            'package': 'multi-fix',
            'cve': 'CVE-2024-1111',
            'description': 'Multiple fixes',
            'fixed_in': ['1.0.0', '2.0.0', '3.0.0']
        }

        result = format_finding(finding)

        assert '1.0.0' in result or '2.0.0' in result or '3.0.0' in result

    def test_format_finding_missing_fields(self):
        """Test formatting finding with missing optional fields."""
        finding = {
            'repo': 'test-app',
            'severity': 'LOW',
            'package': 'simple-pkg',
            'cve': 'CVE-2024-2222'
        }

        # Should handle gracefully
        result = format_finding(finding)

        assert isinstance(result, str)
        assert 'simple-pkg' in result

    def test_format_finding_long_description(self):
        """Test formatting finding with long description."""
        finding = {
            'repo': 'test-app',
            'severity': 'HIGH',
            'package': 'test-pkg',
            'cve': 'CVE-2024-3333',
            'description': 'A' * 500,  # Very long description
            'fixed_in': ['1.0.0']
        }

        result = format_finding(finding)

        assert isinstance(result, str)
        assert len(result) > 0


class TestFormatAutoFix:
    """Test format_auto_fix function."""

    def test_format_auto_fix_basic(self):
        """Test basic auto-fix formatting."""
        fix = {
            'package': 'requests',
            'current_version': '2.27.0',
            'fixed_version': '2.28.0',
            'pr_number': 123
        }

        result = format_auto_fix(fix)

        assert isinstance(result, str)
        assert 'requests' in result
        assert '2.27.0' in result
        assert '2.28.0' in result
        assert '123' in result

    def test_format_auto_fix_no_pr(self):
        """Test formatting auto-fix without PR number."""
        fix = {
            'package': 'django',
            'current_version': '3.2.0',
            'fixed_version': '4.0.0'
        }

        result = format_auto_fix(fix)

        assert isinstance(result, str)
        assert 'django' in result

    def test_format_auto_fix_with_url(self):
        """Test formatting auto-fix with PR URL."""
        fix = {
            'package': 'flask',
            'current_version': '2.0.0',
            'fixed_version': '2.1.0',
            'pr_number': 456,
            'pr_url': 'https://github.com/org/repo/pull/456'
        }

        result = format_auto_fix(fix)

        assert isinstance(result, str)
        assert 'flask' in result

    def test_format_auto_fix_missing_versions(self):
        """Test formatting auto-fix with missing version info."""
        fix = {
            'package': 'test-pkg',
            'pr_number': 789
        }

        result = format_auto_fix(fix)

        assert isinstance(result, str)
        assert 'test-pkg' in result


class TestMain:
    """Test main CLI function."""

    @patch('generate_report.generate_report')
    @patch('sys.argv', ['generate_report.py', '--triage', 'triage.json', '--output', 'report.md'])
    def test_main_with_arguments(self, mock_generate):
        """Test main function with CLI arguments."""
        main()

        mock_generate.assert_called_once_with('triage.json', 'report.md')

    @patch('sys.argv', ['generate_report.py'])
    def test_main_missing_arguments(self):
        """Test main without required arguments."""
        with pytest.raises(SystemExit):
            main()

    @patch('generate_report.generate_report')
    @patch('sys.argv', ['generate_report.py', '--triage', 'input.json', '--output', 'output.md'])
    def test_main_calls_generate_report(self, mock_generate):
        """Test that main calls generate_report function."""
        main()

        assert mock_generate.called
        args = mock_generate.call_args[0]
        assert args[0] == 'input.json'
        assert args[1] == 'output.md'


class TestReportIntegration:
    """Integration tests for report generation."""

    def test_full_report_workflow(self):
        """Test complete report generation workflow."""
        triage_data = {
            'findings': [
                {
                    'repo': 'webapp',
                    'severity': 'CRITICAL',
                    'package': 'requests',
                    'cve': 'CVE-2024-1234',
                    'description': 'Critical security flaw',
                    'fixed_in': ['2.28.0']
                },
                {
                    'repo': 'webapp',
                    'severity': 'HIGH',
                    'package': 'django',
                    'cve': 'CVE-2024-5678',
                    'description': 'High severity vulnerability',
                    'fixed_in': ['4.1.0']
                },
                {
                    'repo': 'webapp',
                    'severity': 'MEDIUM',
                    'package': 'flask',
                    'cve': 'CVE-2024-9101',
                    'description': 'Medium risk issue',
                    'fixed_in': ['2.3.0']
                }
            ],
            'auto_fixes': [
                {
                    'package': 'requests',
                    'current_version': '2.27.0',
                    'fixed_version': '2.28.0',
                    'pr_number': 100
                },
                {
                    'package': 'django',
                    'current_version': '4.0.0',
                    'fixed_version': '4.1.0',
                    'pr_number': 101
                }
            ],
            'summary': {
                'total': 3,
                'critical': 1,
                'high': 1,
                'medium': 1,
                'low': 0
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as triage_f:
            json.dump(triage_data, triage_f)
            triage_file = triage_f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            # Generate report
            generate_report(triage_file, report_file)

            # Verify report content
            with open(report_file) as f:
                content = f.read()

                # Check all findings are present
                assert 'CVE-2024-1234' in content
                assert 'CVE-2024-5678' in content
                assert 'CVE-2024-9101' in content

                # Check packages
                assert 'requests' in content
                assert 'django' in content
                assert 'flask' in content

                # Check severities
                assert 'CRITICAL' in content
                assert 'HIGH' in content
                assert 'MEDIUM' in content

                # Check auto-fixes
                assert '100' in content or '101' in content
        finally:
            os.unlink(triage_file)
            if os.path.exists(report_file):
                os.unlink(report_file)

    def test_report_structure_valid_markdown(self):
        """Test that generated report is valid markdown."""
        triage_data = {
            'findings': [
                {
                    'repo': 'test',
                    'severity': 'HIGH',
                    'package': 'pkg',
                    'cve': 'CVE-2024-1',
                    'description': 'Test',
                    'fixed_in': ['1.0']
                }
            ],
            'auto_fixes': [],
            'summary': {'total': 1, 'critical': 0, 'high': 1, 'medium': 0, 'low': 0}
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as triage_f:
            json.dump(triage_data, triage_f)
            triage_file = triage_f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as report_f:
            report_file = report_f.name

        try:
            generate_report(triage_file, report_file)

            with open(report_file) as f:
                content = f.read()

                # Check for markdown formatting
                assert '#' in content or '##' in content or '- ' in content
        finally:
            os.unlink(triage_file)
            if os.path.exists(report_file):
                os.unlink(report_file)
