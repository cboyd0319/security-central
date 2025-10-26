"""Tests for config_loader.py"""

import os
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.config_loader import (
    ProjectConfig,
    ReposConfig,
    ScanningConfig,
    SecurityCentralConfig,
    SecurityPolicies,
)


class TestSecurityCentralConfig:
    """Test SecurityCentralConfig class."""

    def test_load_valid_config(self, temp_config_dir):
        """Test loading a valid security-central.yaml config."""
        config_path = temp_config_dir / "security-central.yaml"
        config = SecurityCentralConfig.load(config_path)

        assert config.version == "1.0"
        assert config.project.name == "security-central"
        assert config.project.owner == "test-user"
        assert config.scanning.parallel_scans == 4
        assert config.security_policies.max_critical_age_days == 1

    def test_load_missing_file(self, tmp_path):
        """Test loading a non-existent config file."""
        missing_file = tmp_path / "missing.yaml"

        with pytest.raises(FileNotFoundError):
            SecurityCentralConfig.load(missing_file)

    def test_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            SecurityCentralConfig.load(invalid_file)

    def test_validation_error_missing_required_field(self, tmp_path):
        """Test validation error when required field is missing."""
        config_file = tmp_path / "incomplete.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "version": "1.0",
                    # Missing project, scanning, security_policies
                }
            )
        )

        with pytest.raises(ValidationError):
            SecurityCentralConfig.load(config_file)

    def test_scanning_config_defaults(self):
        """Test ScanningConfig with default values."""
        config = ScanningConfig(schedule="0 9 * * *")

        assert config.parallel_scans == 4  # Default value
        assert config.timeout_minutes == 30  # Default value
        assert config.fail_on_critical is True  # Default value


class TestReposConfig:
    """Test ReposConfig class."""

    def test_load_valid_repos_config(self, temp_config_dir):
        """Test loading a valid repos.yml config."""
        repos_path = temp_config_dir / "repos.yml"
        config = ReposConfig.load(repos_path)

        assert len(config.repositories) == 2
        assert config.repositories[0]["name"] == "test-repo"
        assert config.repositories[0]["tech_stack"] == ["python"]
        assert config.notifications is not None
        assert config.safety_checks is not None

    def test_load_repos_config_missing_file(self, tmp_path):
        """Test loading non-existent repos.yml."""
        missing_file = tmp_path / "missing-repos.yml"

        with pytest.raises(FileNotFoundError):
            ReposConfig.load(missing_file)

    def test_repos_config_optional_fields(self, tmp_path):
        """Test ReposConfig with minimal required fields."""
        repos_file = tmp_path / "minimal-repos.yml"
        repos_file.write_text(
            yaml.dump(
                {
                    "repositories": [
                        {"name": "minimal-repo", "url": "https://github.com/test/minimal"}
                    ]
                }
            )
        )

        config = ReposConfig.load(repos_file)

        assert len(config.repositories) == 1
        assert config.notifications is None  # Optional field
        assert config.safety_checks is None  # Optional field


class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_scanning_config(self):
        """Test valid scanning configuration."""
        config = ScanningConfig(
            schedule="0 9 * * *", parallel_scans=4, timeout_minutes=30, fail_on_critical=True
        )

        assert config.schedule == "0 9 * * *"
        assert config.parallel_scans == 4

    def test_valid_security_policies(self):
        """Test valid security policies."""
        policies = SecurityPolicies(
            max_critical_age_days=1,
            max_high_age_days=7,
            max_medium_age_days=30,
            block_on_secrets=True,
            require_sarif=True,
        )

        assert policies.max_critical_age_days == 1
        assert policies.block_on_secrets is True

    def test_project_config(self):
        """Test project configuration."""
        project = ProjectConfig(name="test-project", owner="test-owner")

        assert project.name == "test-project"
        assert project.owner == "test-owner"
