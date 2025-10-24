from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field

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
        """Load scanning configuration from security-central.yaml"""
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

class ReposConfig(BaseModel):
    """Load repository definitions from repos.yml"""
    repositories: list[dict]
    notifications: Optional[dict] = None
    schedule: Optional[dict] = None
    safety_checks: Optional[dict] = None

    @classmethod
    def load(cls, config_path: Path = Path("config/repos.yml")):
        """Load repository definitions from repos.yml"""
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

# Usage example:
# scanning_config = SecurityCentralConfig.load()
# repos_config = ReposConfig.load()
