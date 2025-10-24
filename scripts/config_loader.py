from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field, ValidationError

# Configuration loader for security-central
# Note: Repository definitions are in config/repos.yml
# This loader handles the scanning engine configuration from config/security-central.yaml

class ScanningConfig(BaseModel):
    schedule: str
    parallel_scans: int = 4
    timeout_minutes: int = 30
    fail_on_critical: bool = True

class SecurityPolicies(BaseModel):
    max_critical_age_days: int = 1
    max_high_age_days: int = 7
    max_medium_age_days: int = 30
    block_on_secrets: bool = True
    require_sarif: bool = True

class ProjectConfig(BaseModel):
    name: str
    owner: str

class SecurityCentralConfig(BaseModel):
    """Configuration for the security-central scanning engine.

    Repository definitions are loaded separately from config/repos.yml
    """
    version: str
    project: ProjectConfig
    scanning: ScanningConfig
    security_policies: SecurityPolicies

    @classmethod
    def load(cls, config_path: Path = Path("config/security-central.yaml")):
        """Load scanning configuration from security-central.yaml

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValidationError: If config doesn't match schema
        """
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please ensure {config_path} exists and contains valid configuration."
            )
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in {config_path}: {e}\n"
                f"Please check the file for syntax errors."
            )
        except Exception as e:
            raise Exception(f"Error reading {config_path}: {e}")

        try:
            return cls(**data)
        except ValidationError as e:
            raise ValidationError(
                f"Invalid configuration in {config_path}:\n{e}\n"
                f"Please check that all required fields are present and valid."
            )

class ReposConfig(BaseModel):
    """Load repository definitions from repos.yml"""
    repositories: list[dict]
    notifications: Optional[dict] = None
    schedule: Optional[dict] = None
    safety_checks: Optional[dict] = None

    @classmethod
    def load(cls, config_path: Path = Path("config/repos.yml")):
        """Load repository definitions from repos.yml

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValidationError: If config doesn't match schema
        """
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Repository configuration not found: {config_path}\n"
                f"Please ensure {config_path} exists with repository definitions."
            )
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in {config_path}: {e}\n"
                f"Please check the file for syntax errors."
            )
        except Exception as e:
            raise Exception(f"Error reading {config_path}: {e}")

        try:
            return cls(**data)
        except ValidationError as e:
            raise ValidationError(
                f"Invalid repository configuration in {config_path}:\n{e}\n"
                f"Please check that all required fields are present and valid."
            )

# Usage example:
# scanning_config = SecurityCentralConfig.load()
# repos_config = ReposConfig.load()
