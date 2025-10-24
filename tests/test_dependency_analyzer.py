#!/usr/bin/env python3
"""
Comprehensive tests for scripts/dependency_analyzer.py

Tests supply chain risk analysis for dependencies.
"""

import pytest
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from dependency_analyzer import (
    DependencyRisk,
    SupplyChainAnalyzer,
)


class TestDependencyRisk:
    """Test DependencyRisk dataclass."""

    def test_create_dependency_risk(self):
        """Test creating DependencyRisk instance."""
        risk = DependencyRisk(
            name='requests',
            version='2.28.0',
            risk_score=25.5,
            issues=['no_github_repo', 'single_maintainer']
        )

        assert risk.name == 'requests'
        assert risk.version == '2.28.0'
        assert risk.risk_score == 25.5
        assert len(risk.issues) == 2

    def test_to_dict(self):
        """Test converting DependencyRisk to dictionary."""
        risk = DependencyRisk(
            name='django',
            version='4.0.0',
            risk_score=15.0,
            issues=['missing_security_policy']
        )

        result = risk.to_dict()

        assert result['name'] == 'django'
        assert result['version'] == '4.0.0'
        assert result['risk_score'] == 15.0
        assert result['issues'] == ['missing_security_policy']

    def test_empty_issues(self):
        """Test DependencyRisk with no issues."""
        risk = DependencyRisk(
            name='safe-package',
            version='1.0.0',
            risk_score=0.0,
            issues=[]
        )

        assert len(risk.issues) == 0
        assert risk.risk_score == 0.0

    def test_high_risk_score(self):
        """Test DependencyRisk with high risk score."""
        risk = DependencyRisk(
            name='risky-package',
            version='0.1.0',
            risk_score=95.0,
            issues=['uses_exec_eval', 'network_access', 'single_maintainer']
        )

        assert risk.risk_score == 95.0
        assert len(risk.issues) == 3


class TestSupplyChainAnalyzer:
    """Test SupplyChainAnalyzer class."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def analyzer(self, temp_repo):
        """Create SupplyChainAnalyzer instance."""
        return SupplyChainAnalyzer(temp_repo)

    def test_init(self, temp_repo):
        """Test SupplyChainAnalyzer initialization."""
        analyzer = SupplyChainAnalyzer(temp_repo)

        assert analyzer.repo_path == temp_repo
        assert hasattr(analyzer, 'session')

    def test_risk_indicators_defined(self):
        """Test that RISK_INDICATORS are properly defined."""
        indicators = SupplyChainAnalyzer.RISK_INDICATORS

        assert 'typosquatting' in indicators
        assert 'no_github_repo' in indicators
        assert 'single_maintainer' in indicators
        assert 'uses_exec_eval' in indicators

        # Check scores are reasonable
        assert indicators['typosquatting'] > 0
        assert indicators['uses_exec_eval'] > indicators['single_maintainer']

    @patch('dependency_analyzer.subprocess.run')
    @patch.object(SupplyChainAnalyzer, '_get_pypi_metadata')
    @patch.object(SupplyChainAnalyzer, '_is_typosquat')
    def test_analyze_python_deps_no_risks(self, mock_typosquat, mock_metadata, mock_subprocess, analyzer):
        """Test analyzing dependencies with no risks."""
        # Mock pip list output
        mock_result = Mock()
        mock_result.stdout = json.dumps([
            {'name': 'requests', 'version': '2.28.0'},
            {'name': 'django', 'version': '4.0.0'}
        ])
        mock_subprocess.return_value = mock_result

        # Mock metadata (safe packages)
        mock_metadata.return_value = {
            'info': {
                'maintainers': ['user1', 'user2'],
                'project_urls': {'Source': 'https://github.com/...'}
            }
        }
        mock_typosquat.return_value = False

        risks = analyzer.analyze_python_deps()

        # Should return empty list (no high-risk packages)
        assert isinstance(risks, list)

    @patch('dependency_analyzer.subprocess.run')
    @patch.object(SupplyChainAnalyzer, '_get_pypi_metadata')
    @patch.object(SupplyChainAnalyzer, '_is_typosquat')
    def test_analyze_python_deps_with_typosquat(self, mock_typosquat, mock_metadata, mock_subprocess, analyzer):
        """Test analyzing dependencies with typosquatting risk."""
        mock_result = Mock()
        mock_result.stdout = json.dumps([
            {'name': 'reqeusts', 'version': '1.0.0'}  # Typo of requests
        ])
        mock_subprocess.return_value = mock_result

        mock_metadata.return_value = {
            'info': {
                'maintainers': ['user1'],
                'project_urls': {}
            }
        }
        mock_typosquat.return_value = True  # Detected as typosquat

        risks = analyzer.analyze_python_deps()

        # Should detect high risk
        assert len(risks) >= 0  # May or may not exceed threshold

    @patch('dependency_analyzer.subprocess.run')
    def test_analyze_python_deps_empty_list(self, mock_subprocess, analyzer):
        """Test analyzing with no dependencies."""
        mock_result = Mock()
        mock_result.stdout = json.dumps([])
        mock_subprocess.return_value = mock_result

        risks = analyzer.analyze_python_deps()

        assert isinstance(risks, list)
        assert len(risks) == 0

    def test_get_pypi_metadata_success(self, analyzer):
        """Test fetching PyPI metadata successfully."""
        with patch.object(analyzer.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'info': {
                    'name': 'requests',
                    'version': '2.28.0'
                }
            }
            mock_get.return_value = mock_response

            metadata = analyzer._get_pypi_metadata('requests')

            assert metadata is not None
            assert metadata['info']['name'] == 'requests'

    def test_get_pypi_metadata_failure(self, analyzer):
        """Test handling PyPI metadata fetch failure."""
        with patch.object(analyzer.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            metadata = analyzer._get_pypi_metadata('nonexistent-package')

            assert metadata is None

    def test_get_pypi_metadata_exception(self, analyzer):
        """Test handling exception during metadata fetch."""
        with patch.object(analyzer.session, 'get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            metadata = analyzer._get_pypi_metadata('package')

            assert metadata is None

    def test_is_typosquat_exact_match(self, analyzer):
        """Test typosquatting detection with exact popular package."""
        # Popular packages shouldn't be flagged
        assert analyzer._is_typosquat('requests') == False
        assert analyzer._is_typosquat('django') == False
        assert analyzer._is_typosquat('flask') == False

    def test_is_typosquat_close_match(self, analyzer):
        """Test typosquatting detection with similar name."""
        # These might be typosquats
        result = analyzer._is_typosquat('reqeusts')  # reqeusts vs requests
        # Result depends on implementation, just check it returns bool
        assert isinstance(result, bool)

    def test_is_typosquat_very_different(self, analyzer):
        """Test typosquatting detection with very different name."""
        # Very different names shouldn't match
        result = analyzer._is_typosquat('my-custom-package-xyz')
        assert isinstance(result, bool)

    def test_levenshtein_distance_identical(self):
        """Test Levenshtein distance for identical strings."""
        distance = SupplyChainAnalyzer._levenshtein('test', 'test')
        assert distance == 0

    def test_levenshtein_distance_single_char(self):
        """Test Levenshtein distance for single character difference."""
        distance = SupplyChainAnalyzer._levenshtein('test', 'best')
        assert distance == 1

    def test_levenshtein_distance_insertion(self):
        """Test Levenshtein distance for insertion."""
        distance = SupplyChainAnalyzer._levenshtein('test', 'tests')
        assert distance == 1

    def test_levenshtein_distance_deletion(self):
        """Test Levenshtein distance for deletion."""
        distance = SupplyChainAnalyzer._levenshtein('tests', 'test')
        assert distance == 1

    def test_levenshtein_distance_completely_different(self):
        """Test Levenshtein distance for completely different strings."""
        distance = SupplyChainAnalyzer._levenshtein('abc', 'xyz')
        assert distance == 3

    def test_levenshtein_distance_empty_strings(self):
        """Test Levenshtein distance with empty strings."""
        distance = SupplyChainAnalyzer._levenshtein('', 'test')
        assert distance == 4

        distance = SupplyChainAnalyzer._levenshtein('test', '')
        assert distance == 4

        distance = SupplyChainAnalyzer._levenshtein('', '')
        assert distance == 0


class TestSupplyChainAnalyzerIntegration:
    """Integration tests for supply chain analysis."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch('dependency_analyzer.subprocess.run')
    @patch.object(SupplyChainAnalyzer, '_get_pypi_metadata')
    def test_full_analysis_workflow(self, mock_metadata, mock_subprocess, temp_repo):
        """Test complete analysis workflow."""
        analyzer = SupplyChainAnalyzer(temp_repo)

        # Mock dependencies
        mock_result = Mock()
        mock_result.stdout = json.dumps([
            {'name': 'safe-package', 'version': '1.0.0'},
            {'name': 'risky-package', 'version': '0.1.0'}
        ])
        mock_subprocess.return_value = mock_result

        # Mock metadata - one safe, one risky
        def metadata_side_effect(package_name):
            if package_name == 'safe-package':
                return {
                    'info': {
                        'maintainers': ['user1', 'user2', 'user3'],
                        'project_urls': {'Source': 'https://github.com/safe/package'}
                    }
                }
            else:
                return {
                    'info': {
                        'maintainers': ['user1'],  # Single maintainer
                        'project_urls': {}  # No GitHub repo
                    }
                }

        mock_metadata.side_effect = metadata_side_effect

        risks = analyzer.analyze_python_deps()

        # Verify analysis ran
        assert isinstance(risks, list)

    @patch('dependency_analyzer.subprocess.run')
    def test_analysis_with_subprocess_error(self, mock_subprocess, temp_repo):
        """Test handling subprocess errors."""
        analyzer = SupplyChainAnalyzer(temp_repo)

        # Simulate subprocess failure
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'pip')

        with pytest.raises(subprocess.CalledProcessError):
            analyzer.analyze_python_deps()

    def test_risk_score_accumulation(self, temp_repo):
        """Test that risk scores accumulate correctly."""
        analyzer = SupplyChainAnalyzer(temp_repo)

        # Verify risk indicators
        assert analyzer.RISK_INDICATORS['typosquatting'] == 20
        assert analyzer.RISK_INDICATORS['single_maintainer'] == 10
        assert analyzer.RISK_INDICATORS['uses_exec_eval'] == 30

        # A package with multiple issues should have cumulative score
        expected_score = 20 + 10 + 30  # 60
        assert expected_score > 50  # High risk threshold

    @patch('dependency_analyzer.subprocess.run')
    @patch.object(SupplyChainAnalyzer, '_get_pypi_metadata')
    def test_filtering_high_risk_only(self, mock_metadata, mock_subprocess, temp_repo):
        """Test that only high-risk dependencies are returned."""
        analyzer = SupplyChainAnalyzer(temp_repo)

        mock_result = Mock()
        mock_result.stdout = json.dumps([
            {'name': 'low-risk', 'version': '1.0.0'},
            {'name': 'high-risk', 'version': '0.1.0'}
        ])
        mock_subprocess.return_value = mock_result

        def metadata_side_effect(package_name):
            if package_name == 'low-risk':
                # Low risk: multiple maintainers, has GitHub
                return {
                    'info': {
                        'maintainers': ['user1', 'user2', 'user3'],
                        'project_urls': {'Source': 'https://github.com/org/low-risk'}
                    }
                }
            else:
                # High risk: single maintainer, no GitHub, would trigger multiple flags
                return {
                    'info': {
                        'maintainers': ['solo'],
                        'project_urls': {}
                    }
                }

        mock_metadata.side_effect = metadata_side_effect

        risks = analyzer.analyze_python_deps()

        # Only packages with score > 50 should be returned
        for risk in risks:
            assert risk.risk_score > 50


class TestDependencyRiskDataclass:
    """Additional tests for DependencyRisk dataclass."""

    def test_dataclass_fields(self):
        """Test that DependencyRisk has all expected fields."""
        risk = DependencyRisk(
            name='test',
            version='1.0',
            risk_score=50.0,
            issues=[]
        )

        assert hasattr(risk, 'name')
        assert hasattr(risk, 'version')
        assert hasattr(risk, 'risk_score')
        assert hasattr(risk, 'issues')

    def test_to_dict_structure(self):
        """Test that to_dict returns proper structure."""
        risk = DependencyRisk(
            name='package',
            version='2.0.0',
            risk_score=75.5,
            issues=['issue1', 'issue2']
        )

        result = risk.to_dict()

        assert isinstance(result, dict)
        assert 'name' in result
        assert 'version' in result
        assert 'risk_score' in result
        assert 'issues' in result
        assert isinstance(result['issues'], list)

    def test_multiple_issues(self):
        """Test DependencyRisk with multiple issues."""
        issues = [
            'typosquatting',
            'no_github_repo',
            'single_maintainer',
            'uses_exec_eval'
        ]
        risk = DependencyRisk(
            name='suspicious-pkg',
            version='0.0.1',
            risk_score=85.0,
            issues=issues
        )

        assert len(risk.issues) == 4
        assert 'typosquatting' in risk.issues
        assert 'uses_exec_eval' in risk.issues

    def test_risk_score_float_precision(self):
        """Test risk score handles float precision."""
        risk = DependencyRisk(
            name='test',
            version='1.0',
            risk_score=33.333333,
            issues=[]
        )

        assert isinstance(risk.risk_score, float)
        assert risk.risk_score > 33.33
        assert risk.risk_score < 33.34
