"""Tests for clone_repos.py"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.clone_repos import clone_repos


class TestCloneRepos:
    """Test clone_repos function."""

    @pytest.fixture
    def temp_repos_config(self, tmp_path):
        """Create temporary repos.yml config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        config = {
            "repositories": [
                {"name": "test-repo-1", "url": "https://github.com/test/repo1.git"},
                {"name": "test-repo-2", "url": "https://github.com/test/repo2.git"},
            ]
        }

        config_file = config_dir / "repos.yml"
        config_file.write_text(yaml.dump(config))

        return config_file

    @patch("subprocess.run")
    def test_clone_new_repos(self, mock_run, temp_repos_config, tmp_path, capsys):
        """Test cloning new repositories."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        repos_dir = tmp_path / "repos"

        clone_repos(str(temp_repos_config), str(repos_dir))

        # Should have called git clone twice
        assert mock_run.call_count == 2

        # Verify git clone was called with correct arguments
        calls = mock_run.call_args_list
        assert calls[0][0][0][0] == "git"
        assert calls[0][0][0][1] == "clone"

        captured = capsys.readouterr()
        assert "✅ 2/2 repositories ready" in captured.out

    @patch("subprocess.run")
    def test_pull_existing_repos(self, mock_run, temp_repos_config, tmp_path, capsys):
        """Test pulling existing repositories."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        # Create repos directory with existing repos
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir()
        (repos_dir / "test-repo-1").mkdir()
        (repos_dir / "test-repo-2").mkdir()

        clone_repos(str(temp_repos_config), str(repos_dir))

        # Should have called git pull twice
        assert mock_run.call_count == 2

        # Verify git pull was called
        calls = mock_run.call_args_list
        assert calls[0][0][0][0] == "git"
        assert calls[0][0][0][1] == "pull"

        captured = capsys.readouterr()
        assert "already cloned" in captured.out

    @patch("subprocess.run")
    def test_clone_failure_handling(self, mock_run, temp_repos_config, tmp_path, capsys):
        """Test handling of clone failures."""
        # First clone succeeds, second fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr="", stdout=""),
            MagicMock(returncode=1, stderr="fatal: repository not found", stdout=""),
        ]

        repos_dir = tmp_path / "repos"

        clone_repos(str(temp_repos_config), str(repos_dir))

        captured = capsys.readouterr()
        assert "✅ 1/2 repositories ready" in captured.out
        assert "⚠️  Failed to clone: test-repo-2" in captured.out

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run, temp_repos_config, tmp_path, capsys):
        """Test handling of subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 120)

        repos_dir = tmp_path / "repos"

        clone_repos(str(temp_repos_config), str(repos_dir))

        captured = capsys.readouterr()
        assert "⚠️  Error with test-repo-1" in captured.out
        assert "✅ 0/2 repositories ready" in captured.out

    @patch("subprocess.run")
    def test_creates_repos_directory(self, mock_run, temp_repos_config, tmp_path):
        """Test that repos directory is created if it doesn't exist."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        repos_dir = tmp_path / "repos"
        assert not repos_dir.exists()

        clone_repos(str(temp_repos_config), str(repos_dir))

        assert repos_dir.exists()
        assert repos_dir.is_dir()
