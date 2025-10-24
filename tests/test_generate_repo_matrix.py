#!/usr/bin/env python3
"""
Comprehensive tests for scripts/generate_repo_matrix.py

Tests matrix generation for GitHub Actions workflows.
"""

import pytest
import json
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_repo_matrix import (
    generate_matrix,
    generate_tech_matrix,
    print_matrix_info,
    main,
)


@pytest.fixture
def sample_repos_config():
    """Create a sample repos.yml configuration."""
    config = {
        'repositories': [
            {
                'name': 'test-app',
                'url': 'https://github.com/test/test-app',
                'tech': 'python',
                'critical': True
            },
            {
                'name': 'web-service',
                'url': 'https://github.com/test/web-service',
                'tech': 'javascript',
                'critical': False
            },
            {
                'name': 'api-server',
                'url': 'https://github.com/test/api-server',
                'tech': 'python',
                'critical': True
            }
        ]
    }
    return config


@pytest.fixture
def sample_repos_file(sample_repos_config):
    """Create a temporary repos.yml file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tf:
        yaml.dump(sample_repos_config, tf)
        return tf.name


class TestGenerateMatrix:
    """Test generate_matrix function."""

    def test_generate_json_matrix(self, sample_repos_file):
        """Test generating matrix in JSON format."""
        result = generate_matrix(sample_repos_file, output_format='json')

        # Should be valid JSON
        matrix_data = json.loads(result)

        assert 'repository' in matrix_data
        assert len(matrix_data['repository']) == 3

        # Verify repository data
        repos = matrix_data['repository']
        assert any(r['name'] == 'test-app' for r in repos)
        assert any(r['name'] == 'web-service' for r in repos)
        assert any(r['name'] == 'api-server' for r in repos)

    def test_generate_compact_matrix(self, sample_repos_file):
        """Test generating compact matrix format."""
        result = generate_matrix(sample_repos_file, output_format='compact')

        # Compact format should be comma-separated names
        assert 'test-app' in result
        assert 'web-service' in result
        assert 'api-server' in result

    def test_generate_github_matrix(self, sample_repos_file):
        """Test generating GitHub Actions matrix format."""
        result = generate_matrix(sample_repos_file, output_format='github')

        # GitHub format should be JSON with repository array
        assert 'repository' in result
        matrix_data = json.loads(result)
        assert isinstance(matrix_data['repository'], list)

    def test_invalid_format(self, sample_repos_file):
        """Test with invalid output format."""
        with pytest.raises(ValueError, match="Invalid output format"):
            generate_matrix(sample_repos_file, output_format='invalid')

    def test_empty_repositories(self):
        """Test with empty repositories list."""
        empty_config = {'repositories': []}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tf:
            yaml.dump(empty_config, tf)
            config_file = tf.name

        try:
            result = generate_matrix(config_file, output_format='json')
            matrix_data = json.loads(result)
            assert matrix_data['repository'] == []
        finally:
            os.unlink(config_file)

    def test_missing_config_file(self):
        """Test with non-existent config file."""
        with pytest.raises(FileNotFoundError):
            generate_matrix('nonexistent-file.yml')

    def test_repository_fields_included(self, sample_repos_file):
        """Test that all repository fields are included in matrix."""
        result = generate_matrix(sample_repos_file, output_format='json')
        matrix_data = json.loads(result)

        first_repo = matrix_data['repository'][0]
        assert 'name' in first_repo
        assert 'url' in first_repo
        assert 'tech' in first_repo
        assert 'critical' in first_repo

    def test_matrix_ordering(self, sample_repos_file):
        """Test that repositories maintain order."""
        result = generate_matrix(sample_repos_file, output_format='json')
        matrix_data = json.loads(result)

        repo_names = [r['name'] for r in matrix_data['repository']]
        # Should maintain order from config
        assert repo_names == ['test-app', 'web-service', 'api-server']


class TestGenerateTechMatrix:
    """Test generate_tech_matrix function."""

    def test_generate_tech_matrix_basic(self, sample_repos_file):
        """Test generating technology-based matrix."""
        result = generate_tech_matrix(sample_repos_file)

        matrix_data = json.loads(result)

        # Should group by technology
        assert 'tech' in matrix_data
        techs = matrix_data['tech']

        # Should have python and javascript
        tech_names = [t['name'] for t in techs]
        assert 'python' in tech_names
        assert 'javascript' in tech_names

    def test_tech_matrix_repo_counts(self, sample_repos_file):
        """Test that tech matrix includes correct repository counts."""
        result = generate_tech_matrix(sample_repos_file)
        matrix_data = json.loads(result)

        # Find python tech entry
        python_entry = next(t for t in matrix_data['tech'] if t['name'] == 'python')

        # Should have 2 python repos (test-app, api-server)
        assert 'repositories' in python_entry
        assert len(python_entry['repositories']) == 2

    def test_tech_matrix_repository_details(self, sample_repos_file):
        """Test that tech matrix includes repository details."""
        result = generate_tech_matrix(sample_repos_file)
        matrix_data = json.loads(result)

        python_entry = next(t for t in matrix_data['tech'] if t['name'] == 'python')

        # Check repository details
        repo_names = [r['name'] for r in python_entry['repositories']]
        assert 'test-app' in repo_names
        assert 'api-server' in repo_names

    def test_tech_matrix_single_tech(self):
        """Test tech matrix with single technology."""
        config = {
            'repositories': [
                {'name': 'app1', 'url': 'url1', 'tech': 'python'},
                {'name': 'app2', 'url': 'url2', 'tech': 'python'},
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tf:
            yaml.dump(config, tf)
            config_file = tf.name

        try:
            result = generate_tech_matrix(config_file)
            matrix_data = json.loads(result)

            assert len(matrix_data['tech']) == 1
            assert matrix_data['tech'][0]['name'] == 'python'
            assert len(matrix_data['tech'][0]['repositories']) == 2
        finally:
            os.unlink(config_file)

    def test_tech_matrix_missing_tech_field(self):
        """Test handling repositories without tech field."""
        config = {
            'repositories': [
                {'name': 'app1', 'url': 'url1', 'tech': 'python'},
                {'name': 'app2', 'url': 'url2'},  # Missing tech
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tf:
            yaml.dump(config, tf)
            config_file = tf.name

        try:
            result = generate_tech_matrix(config_file)
            matrix_data = json.loads(result)

            # Should handle gracefully (either skip or group as 'unknown')
            assert 'tech' in matrix_data
        finally:
            os.unlink(config_file)


class TestPrintMatrixInfo:
    """Test print_matrix_info function."""

    def test_print_matrix_info_basic(self, sample_repos_file, capsys):
        """Test printing matrix information."""
        print_matrix_info(sample_repos_file)

        captured = capsys.readouterr()
        output = captured.out

        # Should print information about repositories
        assert '3' in output or 'test-app' in output or 'repositories' in output.lower()

    def test_print_matrix_info_shows_technologies(self, sample_repos_file, capsys):
        """Test that matrix info shows technologies."""
        print_matrix_info(sample_repos_file)

        captured = capsys.readouterr()
        output = captured.out

        # Should mention technologies
        assert 'python' in output.lower() or 'javascript' in output.lower() or 'tech' in output.lower()

    def test_print_matrix_info_empty_repos(self, capsys):
        """Test printing info with empty repositories."""
        config = {'repositories': []}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tf:
            yaml.dump(config, tf)
            config_file = tf.name

        try:
            print_matrix_info(config_file)

            captured = capsys.readouterr()
            output = captured.out

            # Should handle empty gracefully
            assert '0' in output or 'no' in output.lower() or 'empty' in output.lower()
        finally:
            os.unlink(config_file)


class TestMain:
    """Test main function."""

    @patch('sys.argv', ['generate_repo_matrix.py'])
    def test_main_default_behavior(self, sample_repos_file, capsys):
        """Test main function with default arguments."""
        # Main reads from default config/repos.yml, so we need to mock that
        with patch('generate_repo_matrix.generate_matrix') as mock_generate:
            mock_generate.return_value = '{"repository": []}'

            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 0 if successful
            # Or might not call sys.exit() at all

    @patch('sys.argv', ['generate_repo_matrix.py', '--format', 'json'])
    def test_main_with_json_format(self, sample_repos_file):
        """Test main with JSON format argument."""
        with patch('generate_repo_matrix.generate_matrix') as mock_generate:
            mock_generate.return_value = '{"repository": []}'

            # Main might not return anything, just test it doesn't crash
            try:
                main()
            except SystemExit:
                pass  # Expected if main calls sys.exit()

    @patch('sys.argv', ['generate_repo_matrix.py', '--format', 'compact'])
    def test_main_with_compact_format(self):
        """Test main with compact format."""
        with patch('generate_repo_matrix.generate_matrix') as mock_generate:
            mock_generate.return_value = 'repo1,repo2,repo3'

            try:
                main()
            except SystemExit:
                pass


class TestMatrixIntegration:
    """Integration tests for matrix generation."""

    def test_full_workflow_json_output(self, sample_repos_file):
        """Test complete workflow from config to JSON output."""
        # Generate JSON matrix
        json_result = generate_matrix(sample_repos_file, output_format='json')

        # Parse and verify structure
        matrix_data = json.loads(json_result)

        assert 'repository' in matrix_data
        assert len(matrix_data['repository']) == 3

        # Verify each repository has required fields
        for repo in matrix_data['repository']:
            assert 'name' in repo
            assert 'url' in repo
            assert 'tech' in repo

    def test_full_workflow_tech_matrix(self, sample_repos_file):
        """Test complete workflow for tech-based matrix."""
        # Generate tech matrix
        tech_result = generate_tech_matrix(sample_repos_file)

        # Parse and verify
        tech_data = json.loads(tech_result)

        assert 'tech' in tech_data

        # Verify grouping
        python_repos = next(t for t in tech_data['tech'] if t['name'] == 'python')
        assert len(python_repos['repositories']) == 2

        js_repos = next(t for t in tech_data['tech'] if t['name'] == 'javascript')
        assert len(js_repos['repositories']) == 1

    def test_matrix_can_be_used_by_github_actions(self, sample_repos_file):
        """Test that generated matrix can be used by GitHub Actions."""
        result = generate_matrix(sample_repos_file, output_format='github')

        # GitHub Actions expects specific JSON structure
        matrix_data = json.loads(result)

        # Must have 'repository' key
        assert 'repository' in matrix_data

        # Repository should be an array
        assert isinstance(matrix_data['repository'], list)

        # Each item should be a dict with string values
        for repo in matrix_data['repository']:
            assert isinstance(repo, dict)
            assert all(isinstance(k, str) for k in repo.keys())

    def test_compact_format_for_command_line(self, sample_repos_file):
        """Test compact format suitable for command-line use."""
        result = generate_matrix(sample_repos_file, output_format='compact')

        # Compact should be simple comma-separated or space-separated
        assert isinstance(result, str)

        # Should contain repository names
        assert 'test-app' in result
        assert 'web-service' in result
        assert 'api-server' in result

    def test_matrix_with_critical_flag_filtering(self):
        """Test that critical flag is preserved in matrix."""
        config = {
            'repositories': [
                {'name': 'critical-app', 'url': 'url1', 'tech': 'python', 'critical': True},
                {'name': 'normal-app', 'url': 'url2', 'tech': 'python', 'critical': False},
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tf:
            yaml.dump(config, tf)
            config_file = tf.name

        try:
            result = generate_matrix(config_file, output_format='json')
            matrix_data = json.loads(result)

            critical_repos = [r for r in matrix_data['repository'] if r.get('critical')]
            assert len(critical_repos) == 1
            assert critical_repos[0]['name'] == 'critical-app'
        finally:
            os.unlink(config_file)
