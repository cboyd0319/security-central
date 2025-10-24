#!/usr/bin/env python3
"""
Comprehensive tests for scripts/utils.py

Tests all utility functions with edge cases, error handling, and integration scenarios.
"""

import pytest
import subprocess
import time
import requests
from unittest.mock import Mock, patch, MagicMock, call
from typing import List, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from utils import (
    deduplicate_findings,
    _create_finding_fingerprint,
    rate_limit,
    safe_subprocess_run,
    merge_findings_metadata,
    create_session_with_retries,
    retry_on_exception,
    validate_version_format,
)


class TestDeduplicateFindings:
    """Test deduplicate_findings function."""

    def test_no_duplicates(self):
        """Test with no duplicate findings."""
        findings = [
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'pip-audit',
                'severity': 'HIGH'
            },
            {
                'package': 'django',
                'cve': 'CVE-2024-2',
                'repo': 'app1',
                'tool': 'pip-audit',
                'severity': 'CRITICAL'
            },
        ]
        unique, dupes = deduplicate_findings(findings)
        assert len(unique) == 2
        assert dupes == 0

    def test_exact_duplicates(self):
        """Test with exact duplicate findings."""
        findings = [
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'pip-audit',
                'severity': 'HIGH',
                'fixed_in': ['2.28.0']
            },
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'safety',
                'severity': 'HIGH',
                'fixed_in': ['2.28.0']
            },
        ]
        unique, dupes = deduplicate_findings(findings)
        assert len(unique) == 1
        assert dupes == 1
        assert 'detected_by' in unique[0]
        assert len(unique[0]['detected_by']) == 2

    def test_scanner_priority(self):
        """Test that higher priority scanner data is preferred."""
        findings = [
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'safety',  # Lower priority (7)
                'advisory': 'Old advisory',
                'fixed_in': ['2.27.0']
            },
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'pip-audit',  # Higher priority (10)
                'advisory': 'Better advisory',
                'fixed_in': ['2.28.0']
            },
        ]
        unique, dupes = deduplicate_findings(findings)
        assert len(unique) == 1
        assert dupes == 1
        assert unique[0]['tool'] == 'pip-audit'
        assert unique[0]['advisory'] == 'Better advisory'

    def test_merge_fixed_versions(self):
        """Test that fixed_in versions are merged from multiple scanners."""
        findings = [
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'safety',
                'fixed_in': ['2.27.0', '2.28.0']
            },
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'pip-audit',
                'fixed_in': ['2.28.0', '2.29.0']
            },
        ]
        unique, dupes = deduplicate_findings(findings)
        assert len(unique) == 1
        assert sorted(unique[0]['fixed_in']) == ['2.27.0', '2.28.0', '2.29.0']

    def test_empty_findings(self):
        """Test with empty findings list."""
        unique, dupes = deduplicate_findings([])
        assert unique == []
        assert dupes == 0

    def test_different_repos_same_vuln(self):
        """Test that same vuln in different repos is not deduplicated."""
        findings = [
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'pip-audit'
            },
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app2',
                'tool': 'pip-audit'
            },
        ]
        unique, dupes = deduplicate_findings(findings)
        assert len(unique) == 2
        assert dupes == 0

    def test_none_fixed_in_values(self):
        """Test handling of None values in fixed_in."""
        findings = [
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'safety',
                'fixed_in': None
            },
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'pip-audit',
                'fixed_in': ['2.28.0']
            },
        ]
        unique, dupes = deduplicate_findings(findings)
        assert len(unique) == 1
        assert unique[0]['fixed_in'] == ['2.28.0']

    def test_unknown_scanner(self):
        """Test handling of scanners not in priority list."""
        findings = [
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'unknown-scanner'
            },
            {
                'package': 'requests',
                'cve': 'CVE-2024-1',
                'repo': 'app1',
                'tool': 'pip-audit'
            },
        ]
        unique, dupes = deduplicate_findings(findings)
        assert len(unique) == 1
        # pip-audit should be preferred (priority 10 vs 0)
        assert unique[0]['tool'] == 'pip-audit'


class TestCreateFindingFingerprint:
    """Test _create_finding_fingerprint function."""

    def test_basic_fingerprint(self):
        """Test basic fingerprint creation."""
        finding = {
            'package': 'requests',
            'cve': 'CVE-2024-1',
            'repo': 'app1'
        }
        fingerprint = _create_finding_fingerprint(finding)
        assert isinstance(fingerprint, str)
        assert len(fingerprint) > 0

    def test_same_finding_same_fingerprint(self):
        """Test that identical findings produce same fingerprint."""
        finding1 = {'package': 'requests', 'cve': 'CVE-2024-1', 'repo': 'app1'}
        finding2 = {'package': 'requests', 'cve': 'CVE-2024-1', 'repo': 'app1'}
        assert _create_finding_fingerprint(finding1) == _create_finding_fingerprint(finding2)

    def test_different_finding_different_fingerprint(self):
        """Test that different findings produce different fingerprints."""
        finding1 = {'package': 'requests', 'cve': 'CVE-2024-1', 'repo': 'app1'}
        finding2 = {'package': 'django', 'cve': 'CVE-2024-1', 'repo': 'app1'}
        assert _create_finding_fingerprint(finding1) != _create_finding_fingerprint(finding2)

    def test_missing_fields(self):
        """Test fingerprint creation with missing fields."""
        finding = {'package': 'requests'}
        fingerprint = _create_finding_fingerprint(finding)
        assert isinstance(fingerprint, str)


class TestRateLimit:
    """Test rate_limit decorator."""

    def test_rate_limit_basic(self):
        """Test basic rate limiting."""
        @rate_limit(calls_per_minute=120)  # 2 calls per second
        def test_func():
            return "success"

        # Should complete quickly
        start = time.time()
        result1 = test_func()
        result2 = test_func()
        duration = time.time() - start

        assert result1 == "success"
        assert result2 == "success"
        # Second call should be delayed by ~0.5 seconds
        assert duration >= 0.4  # Allow some tolerance

    def test_rate_limit_with_args(self):
        """Test rate limiting with function arguments."""
        @rate_limit(calls_per_minute=120)
        def test_func(x, y):
            return x + y

        result = test_func(2, 3)
        assert result == 5

    def test_rate_limit_preserves_function_metadata(self):
        """Test that rate_limit preserves function name and docstring."""
        @rate_limit(calls_per_minute=60)
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestSafeSubprocessRun:
    """Test safe_subprocess_run function."""

    def test_successful_command(self):
        """Test successful command execution."""
        result = safe_subprocess_run(['echo', 'hello'], timeout=5)
        assert result is not None
        assert result.returncode == 0
        assert 'hello' in result.stdout

    def test_command_timeout(self):
        """Test command timeout handling."""
        result = safe_subprocess_run(['sleep', '10'], timeout=0.5)
        assert result is None

    def test_command_not_found(self):
        """Test handling of non-existent command."""
        result = safe_subprocess_run(['nonexistent-command-xyz'], timeout=5)
        assert result is None

    def test_check_true_on_failure(self):
        """Test check=True raises exception on failure."""
        with pytest.raises(subprocess.CalledProcessError):
            safe_subprocess_run(['false'], check=True, timeout=5)

    def test_capture_output_default(self):
        """Test that output is captured by default."""
        result = safe_subprocess_run(['echo', 'test'], timeout=5)
        assert result is not None
        assert 'test' in result.stdout

    def test_with_cwd(self):
        """Test command execution with working directory."""
        result = safe_subprocess_run(['pwd'], timeout=5, cwd='/tmp')
        assert result is not None
        assert '/tmp' in result.stdout

    def test_with_env(self):
        """Test command execution with custom environment."""
        result = safe_subprocess_run(
            ['sh', '-c', 'echo $MY_VAR'],
            timeout=5,
            env={'MY_VAR': 'test_value'}
        )
        assert result is not None
        assert 'test_value' in result.stdout


class TestMergeFindingsMetadata:
    """Test merge_findings_metadata function."""

    def test_empty_findings(self):
        """Test with empty findings list."""
        metadata = merge_findings_metadata([])
        assert metadata['total_findings'] == 0
        assert metadata['by_severity'] == {}
        assert metadata['by_tool'] == {}

    def test_basic_metadata(self):
        """Test basic metadata creation."""
        findings = [
            {'severity': 'HIGH', 'tool': 'pip-audit'},
            {'severity': 'CRITICAL', 'tool': 'pip-audit'},
            {'severity': 'HIGH', 'tool': 'safety'},
        ]
        metadata = merge_findings_metadata(findings)
        assert metadata['total_findings'] == 3
        assert metadata['by_severity']['HIGH'] == 2
        assert metadata['by_severity']['CRITICAL'] == 1
        assert metadata['by_tool']['pip-audit'] == 2
        assert metadata['by_tool']['safety'] == 1

    def test_missing_fields(self):
        """Test handling of findings with missing fields."""
        findings = [
            {'severity': 'HIGH'},
            {'tool': 'pip-audit'},
            {},
        ]
        metadata = merge_findings_metadata(findings)
        assert metadata['total_findings'] == 3
        assert 'HIGH' in metadata['by_severity']
        assert 'pip-audit' in metadata['by_tool']

    def test_unique_packages_and_cves(self):
        """Test unique package and CVE counting."""
        findings = [
            {'package': 'requests', 'cve': 'CVE-2024-1'},
            {'package': 'requests', 'cve': 'CVE-2024-2'},
            {'package': 'django', 'cve': 'CVE-2024-1'},
        ]
        metadata = merge_findings_metadata(findings)
        assert metadata['unique_packages'] == 2  # requests, django
        assert metadata['unique_cves'] == 2  # CVE-2024-1, CVE-2024-2


class TestCreateSessionWithRetries:
    """Test create_session_with_retries function."""

    def test_returns_session(self):
        """Test that function returns a requests Session."""
        session = create_session_with_retries()
        assert isinstance(session, requests.Session)

    def test_custom_retries(self):
        """Test with custom retry configuration."""
        session = create_session_with_retries(
            total_retries=5,
            backoff_factor=0.5
        )
        assert isinstance(session, requests.Session)
        # Check adapter is mounted
        assert 'https://' in session.adapters
        assert 'http://' in session.adapters

    def test_session_has_adapters(self):
        """Test that session has retry adapters."""
        session = create_session_with_retries()
        # Verify adapters are configured
        https_adapter = session.get_adapter('https://example.com')
        assert isinstance(https_adapter, HTTPAdapter)


class TestRetryOnException:
    """Test retry_on_exception decorator."""

    def test_successful_call_no_retry(self):
        """Test that successful call doesn't retry."""
        call_count = [0]

        @retry_on_exception(max_retries=3, delay=0.1)
        def successful_func():
            call_count[0] += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_on_failure(self):
        """Test that function retries on exception."""
        call_count = [0]

        @retry_on_exception(max_retries=3, delay=0.1)
        def failing_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Temporary error")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count[0] == 3

    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        call_count = [0]

        @retry_on_exception(max_retries=2, delay=0.1)
        def always_failing_func():
            call_count[0] += 1
            raise ValueError("Permanent error")

        with pytest.raises(ValueError, match="Permanent error"):
            always_failing_func()
        assert call_count[0] == 3  # Initial + 2 retries

    def test_retry_with_args(self):
        """Test retry decorator with function arguments."""
        call_count = [0]

        @retry_on_exception(max_retries=2, delay=0.1)
        def func_with_args(x, y):
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Retry")
            return x + y

        result = func_with_args(2, 3)
        assert result == 5
        assert call_count[0] == 2

    def test_specific_exception_types(self):
        """Test retrying only on specific exception types."""
        call_count = [0]

        @retry_on_exception(max_retries=3, delay=0.1, exceptions=(ValueError,))
        def func_specific_exception():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Retry this")
            elif call_count[0] == 2:
                raise TypeError("Don't retry this")
            return "success"

        with pytest.raises(TypeError, match="Don't retry this"):
            func_specific_exception()
        assert call_count[0] == 2  # Failed on second attempt (TypeError)


class TestValidateVersionFormat:
    """Test validate_version_format function."""

    def test_valid_semver(self):
        """Test valid semantic versions."""
        assert validate_version_format("1.2.3") is True
        assert validate_version_format("0.0.1") is True
        assert validate_version_format("10.20.30") is True

    def test_valid_semver_with_prerelease(self):
        """Test valid semver with prerelease."""
        assert validate_version_format("1.2.3-alpha") is True
        assert validate_version_format("1.2.3-beta.1") is True
        assert validate_version_format("1.2.3-rc.1") is True

    def test_valid_python_version(self):
        """Test valid Python-style versions."""
        assert validate_version_format("1.2.3.4") is True
        assert validate_version_format("2.7") is True

    def test_invalid_versions(self):
        """Test invalid version formats."""
        assert validate_version_format("") is False
        assert validate_version_format("abc") is False
        assert validate_version_format("1.2.") is False
        assert validate_version_format(".1.2") is False

    def test_version_with_v_prefix(self):
        """Test versions with 'v' prefix."""
        assert validate_version_format("v1.2.3") is True
        assert validate_version_format("V2.0.0") is True

    def test_edge_cases(self):
        """Test edge cases."""
        assert validate_version_format("1") is True  # Single digit
        assert validate_version_format("1.2") is True  # Two components
        assert validate_version_format("1.2.3.4.5") is True  # Many components
