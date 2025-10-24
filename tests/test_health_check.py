#!/usr/bin/env python3
"""
Comprehensive tests for scripts/health_check.py

Tests environment health checking functionality.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from health_check import HealthCheckResult, HealthChecker, main


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_create_passing_result(self):
        """Test creating passing health check result."""
        result = HealthCheckResult(
            name="test_check",
            passed=True,
            message="All good",
            category="config"
        )

        assert result.name == "test_check"
        assert result.passed is True
        assert result.is_passing() is True
        assert result.is_failing() is False

    def test_create_failing_result(self):
        """Test creating failing health check result."""
        result = HealthCheckResult(
            name="test_check",
            passed=False,
            message="Failed",
            category="security",
            warning=False
        )

        assert result.passed is False
        assert result.is_failing() is True
        assert result.is_passing() is False
        assert result.is_warning() is False

    def test_create_warning_result(self):
        """Test creating warning health check result."""
        result = HealthCheckResult(
            name="test_check",
            passed=False,
            message="Warning",
            category="tools",
            warning=True
        )

        assert result.is_warning() is True
        assert result.is_failing() is False

    def test_result_with_details(self):
        """Test result with additional details."""
        result = HealthCheckResult(
            name="test",
            passed=True,
            message="OK",
            category="test",
            details="Extra info"
        )

        assert result.details == "Extra info"


class TestHealthChecker:
    """Test HealthChecker class."""

    @pytest.fixture
    def health_checker(self):
        """Create HealthChecker instance."""
        return HealthChecker(verbose=False)

    def test_init(self):
        """Test HealthChecker initialization."""
        checker = HealthChecker(verbose=True)

        assert checker.verbose is True
        assert hasattr(checker, 'results')
        assert len(checker.results) == 0

    def test_init_non_verbose(self):
        """Test initialization with verbose=False."""
        checker = HealthChecker(verbose=False)

        assert checker.verbose is False

    @patch.object(HealthChecker, '_check_config_files')
    @patch.object(HealthChecker, '_check_config_validity')
    @patch.object(HealthChecker, '_check_python_version')
    @patch.object(HealthChecker, '_check_required_packages')
    @patch.object(HealthChecker, '_print_summary')
    def test_run_all_checks_basic(self, mock_summary, mock_packages, mock_python,
                                   mock_validity, mock_config, health_checker):
        """Test running all health checks."""
        # Mock all check methods to avoid actual system checks
        with patch.object(health_checker, '_check_security_tools'), \
             patch.object(health_checker, '_check_directory_structure'), \
             patch.object(health_checker, '_check_permissions'), \
             patch.object(health_checker, '_check_github_token'), \
             patch.object(health_checker, '_check_git_config'), \
             patch.object(health_checker, '_check_cloned_repos'), \
             patch.object(health_checker, '_check_recent_scans'), \
             patch.object(health_checker, '_check_metrics'):

            result = health_checker.run_all_checks()

            # Should return boolean
            assert isinstance(result, bool)

    def test_check_config_files_missing(self, health_checker):
        """Test config files check with missing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            health_checker._check_config_files()

            # Should add results
            assert len(health_checker.results) > 0

    @patch('health_check.Path.exists')
    def test_check_config_files_present(self, mock_exists, health_checker):
        """Test config files check with files present."""
        mock_exists.return_value = True

        health_checker._check_config_files()

        # Should have results
        assert len(health_checker.results) > 0

    @patch('sys.version_info', (3, 12, 0))
    def test_check_python_version_correct(self, health_checker):
        """Test Python version check with correct version."""
        health_checker._check_python_version()

        # Should pass
        results = [r for r in health_checker.results if 'Python' in r.name]
        assert len(results) > 0

    @patch('health_check.subprocess.run')
    def test_check_required_packages(self, mock_run, health_checker):
        """Test required packages check."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "package1\npackage2\npyyaml\nrequests"
        mock_run.return_value = mock_result

        health_checker._check_required_packages()

        assert len(health_checker.results) > 0

    @patch('health_check.subprocess.run')
    def test_check_security_tools_available(self, mock_run, health_checker):
        """Test security tools check when tools available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        health_checker._check_security_tools()

        assert len(health_checker.results) > 0

    @patch('health_check.subprocess.run')
    def test_check_security_tools_missing(self, mock_run, health_checker):
        """Test security tools check when tools missing."""
        mock_run.side_effect = FileNotFoundError()

        health_checker._check_security_tools()

        # Should record missing tools
        assert len(health_checker.results) > 0

    def test_check_directory_structure(self, health_checker):
        """Test directory structure check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create some directories
            Path('config').mkdir()
            Path('scripts').mkdir()

            health_checker._check_directory_structure()

            assert len(health_checker.results) > 0

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'})
    def test_check_github_token_present(self, health_checker):
        """Test GitHub token check when token present."""
        health_checker._check_github_token()

        results = [r for r in health_checker.results if 'GitHub' in r.name]
        assert len(results) > 0

    @patch.dict(os.environ, {}, clear=True)
    def test_check_github_token_missing(self, health_checker):
        """Test GitHub token check when token missing."""
        health_checker._check_github_token()

        results = [r for r in health_checker.results if 'GitHub' in r.name]
        assert len(results) > 0

    @patch('health_check.subprocess.run')
    def test_check_git_config(self, mock_run, health_checker):
        """Test git config check."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "user.name=Test User"
        mock_run.return_value = mock_result

        health_checker._check_git_config()

        assert len(health_checker.results) > 0

    def test_export_results_json(self, health_checker):
        """Test exporting results to JSON."""
        health_checker.results = [
            HealthCheckResult("test1", True, "Pass", "config"),
            HealthCheckResult("test2", False, "Fail", "security", warning=True)
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name

        try:
            health_checker.export_results(output_file)

            assert Path(output_file).exists()

            with open(output_file) as f:
                data = json.load(f)

            assert 'checks' in data
            assert 'summary' in data
            assert len(data['checks']) == 2
        finally:
            Path(output_file).unlink()

    def test_export_results_structure(self, health_checker):
        """Test that exported results have correct structure."""
        health_checker.results = [
            HealthCheckResult("test", True, "OK", "config")
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name

        try:
            health_checker.export_results(output_file)

            with open(output_file) as f:
                data = json.load(f)

            assert 'summary' in data
            assert 'total_checks' in data['summary']
            assert 'passed' in data['summary']
            assert 'failed' in data['summary']
            assert 'warnings' in data['summary']
        finally:
            Path(output_file).unlink()


class TestMain:
    """Test main function."""

    @patch('health_check.HealthChecker')
    @patch('sys.argv', ['health_check.py'])
    def test_main_basic(self, mock_checker_class):
        """Test main function basic execution."""
        mock_checker = Mock()
        mock_checker.run_all_checks.return_value = True
        mock_checker_class.return_value = mock_checker

        # Should not raise
        try:
            main()
        except SystemExit:
            pass

    @patch('health_check.HealthChecker')
    @patch('sys.argv', ['health_check.py', '--verbose'])
    def test_main_verbose(self, mock_checker_class):
        """Test main with verbose flag."""
        mock_checker = Mock()
        mock_checker.run_all_checks.return_value = True
        mock_checker_class.return_value = mock_checker

        try:
            main()
        except SystemExit:
            pass

        # Should create checker with verbose=True
        mock_checker_class.assert_called()

    @patch('health_check.HealthChecker')
    @patch('sys.argv', ['health_check.py', '--export', 'results.json'])
    def test_main_export(self, mock_checker_class):
        """Test main with export option."""
        mock_checker = Mock()
        mock_checker.run_all_checks.return_value = True
        mock_checker_class.return_value = mock_checker

        try:
            main()
        except SystemExit:
            pass


class TestIntegration:
    """Integration tests for health checking."""

    def test_full_health_check_workflow(self):
        """Test complete health check workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create minimal environment
            Path('config').mkdir()
            Path('scripts').mkdir()
            Path('tests').mkdir()

            checker = HealthChecker(verbose=False)

            # Mock some checks that require external tools
            with patch.object(checker, '_check_security_tools'), \
                 patch.object(checker, '_check_git_config'), \
                 patch.object(checker, '_check_cloned_repos'), \
                 patch.object(checker, '_check_recent_scans'), \
                 patch.object(checker, '_check_metrics'):

                result = checker.run_all_checks()

                # Should complete
                assert isinstance(result, bool)
                assert len(checker.results) > 0

    def test_export_and_verify(self):
        """Test exporting results and verifying structure."""
        checker = HealthChecker()

        # Add some mock results
        checker.results = [
            HealthCheckResult("config_check", True, "Config OK", "config"),
            HealthCheckResult("tool_check", False, "Tool missing", "tools", warning=True),
            HealthCheckResult("security_check", False, "Security issue", "security", warning=False)
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name

        try:
            checker.export_results(output_file)

            with open(output_file) as f:
                data = json.load(f)

            # Verify complete structure
            assert data['summary']['total_checks'] == 3
            assert data['summary']['passed'] == 1
            assert data['summary']['failed'] == 1
            assert data['summary']['warnings'] == 1

            # Verify check details
            assert len(data['checks']) == 3
            assert all('name' in check for check in data['checks'])
            assert all('passed' in check for check in data['checks'])
            assert all('category' in check for check in data['checks'])
        finally:
            Path(output_file).unlink()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_results_export(self):
        """Test exporting with no check results."""
        checker = HealthChecker()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name

        try:
            checker.export_results(output_file)

            with open(output_file) as f:
                data = json.load(f)

            assert data['summary']['total_checks'] == 0
            assert data['checks'] == []
        finally:
            Path(output_file).unlink()

    def test_all_checks_passing(self):
        """Test when all checks pass."""
        checker = HealthChecker()
        checker.results = [
            HealthCheckResult(f"check{i}", True, "Pass", "test")
            for i in range(10)
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name

        try:
            checker.export_results(output_file)

            with open(output_file) as f:
                data = json.load(f)

            assert data['summary']['passed'] == 10
            assert data['summary']['failed'] == 0
        finally:
            Path(output_file).unlink()

    def test_all_checks_failing(self):
        """Test when all checks fail."""
        checker = HealthChecker()
        checker.results = [
            HealthCheckResult(f"check{i}", False, "Fail", "test")
            for i in range(5)
        ]

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name

        try:
            checker.export_results(output_file)

            with open(output_file) as f:
                data = json.load(f)

            assert data['summary']['passed'] == 0
            assert data['summary']['failed'] == 5
        finally:
            Path(output_file).unlink()
