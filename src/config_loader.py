from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field, validator

class RepoConfig(BaseModel):
    name: str
    owner: str
    languages: list[str]
    scanners: list[str]
    auto_fix: bool = True
    critical_paths: list[str] = Field(default_factory=list)

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

class SecurityCentralConfig(BaseModel):
    version: str
    managed_repos: list[RepoConfig]
    scanning: ScanningConfig
    security_policies: SecurityPolicies
    
    @classmethod
    def load(cls, config_path: Path = Path("config/security-central.yaml")):
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

# Usage
config = SecurityCentralConfig.load()
