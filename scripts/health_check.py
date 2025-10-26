#!/usr/bin/env python3
"""
Health check script for security-central infrastructure.

Verifies that all required components are properly configured and operational.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from utils import safe_open


@dataclass
class HealthCheckResult:
    """Result of a health check.

    Attributes:
        name: Name of the check
        status: Status (pass, warn, fail)
        message: Human-readable message
        details: Additional details
    """

    name: str
    status: str  # pass, warn, fail
    message: str
    details: Optional[Dict[str, Any]] = None

    def is_passing(self) -> bool:
        """Check if result is passing."""
        return self.status == "pass"

    def is_warning(self) -> bool:
        """Check if result is a warning."""
        return self.status == "warn"

    def is_failing(self) -> bool:
        """Check if result is failing."""
        return self.status == "fail"


class HealthChecker:
    """Perform comprehensive health checks on security-central."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize health checker.

        Args:
            verbose: Print detailed information
        """
        self.verbose: bool = verbose
        self.results: List[HealthCheckResult] = []

    def run_all_checks(self) -> bool:
        """Run all health checks.

        Returns:
            True if all critical checks pass
        """
        print("🏥 Security-Central Health Check")
        print("=" * 60)
        print()

        # Configuration checks
        self._check_config_files()
        self._check_config_validity()

        # Dependency checks
        self._check_python_version()
        self._check_required_packages()
        self._check_security_tools()

        # Directory structure checks
        self._check_directory_structure()
        self._check_permissions()

        # GitHub integration checks
        self._check_github_token()
        self._check_git_config()

        # Repository checks
        self._check_cloned_repos()

        # Recent scan checks
        self._check_recent_scans()
        self._check_metrics()

        # Print summary
        self._print_summary()

        # Return overall health status
        return not any(r.is_failing() for r in self.results)

    def _check_config_files(self) -> None:
        """Check that required configuration files exist."""
        required_configs: List[Tuple[str, bool]] = [
            ("config/repos.yml", True),  # Required
            ("config/security-central.yaml", False),  # Optional
            (".github/workflows/security-scan.yml", False),  # Optional
        ]

        for config_path, required in required_configs:
            path = Path(config_path)
            if path.exists():
                self.results.append(
                    HealthCheckResult(
                        name=f"Config: {config_path}",
                        status="pass",
                        message=f"✓ {config_path} exists",
                    )
                )
            elif required:
                self.results.append(
                    HealthCheckResult(
                        name=f"Config: {config_path}",
                        status="fail",
                        message=f"✗ Required config {config_path} not found",
                    )
                )
            else:
                self.results.append(
                    HealthCheckResult(
                        name=f"Config: {config_path}",
                        status="warn",
                        message=f"⚠ Optional config {config_path} not found",
                    )
                )

    def _check_config_validity(self) -> None:
        """Check that configuration files are valid."""
        # Check repos.yml
        repos_config = Path("config/repos.yml")
        if repos_config.exists():
            try:
                with safe_open(repos_config, allowed_base=False) as f:
                    config: Dict[str, Any] = yaml.safe_load(f)

                if "repositories" in config:
                    repo_count: int = len(config["repositories"])
                    self.results.append(
                        HealthCheckResult(
                            name="Config Validity: repos.yml",
                            status="pass",
                            message=f"✓ Valid YAML with {repo_count} repositories",
                            details={"repo_count": repo_count},
                        )
                    )
                else:
                    self.results.append(
                        HealthCheckResult(
                            name="Config Validity: repos.yml",
                            status="fail",
                            message="✗ Missing 'repositories' key in repos.yml",
                        )
                    )
            except yaml.YAMLError as e:
                self.results.append(
                    HealthCheckResult(
                        name="Config Validity: repos.yml",
                        status="fail",
                        message=f"✗ Invalid YAML: {e}",
                    )
                )

    def _check_python_version(self) -> None:
        """Check Python version."""
        version_info = sys.version_info
        version_str: str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

        if version_info >= (3, 9):
            self.results.append(
                HealthCheckResult(
                    name="Python Version",
                    status="pass",
                    message=f"✓ Python {version_str}",
                    details={"version": version_str},
                )
            )
        elif version_info >= (3, 8):
            self.results.append(
                HealthCheckResult(
                    name="Python Version",
                    status="warn",
                    message=f"⚠ Python {version_str} (3.9+ recommended)",
                )
            )
        else:
            self.results.append(
                HealthCheckResult(
                    name="Python Version",
                    status="fail",
                    message=f"✗ Python {version_str} (3.9+ required)",
                )
            )

    def _check_required_packages(self) -> None:
        """Check that required Python packages are installed."""
        required_packages: List[str] = ["yaml", "requests", "pydantic"]

        for package in required_packages:
            try:
                __import__(package)
                self.results.append(
                    HealthCheckResult(
                        name=f"Package: {package}", status="pass", message=f"✓ {package} installed"
                    )
                )
            except ImportError:
                self.results.append(
                    HealthCheckResult(
                        name=f"Package: {package}",
                        status="fail",
                        message=f"✗ {package} not installed",
                    )
                )

    def _check_security_tools(self) -> None:
        """Check that security scanning tools are available."""
        tools: List[Tuple[str, str]] = [
            ("pip-audit", "pip-audit"),
            ("safety", "safety"),
            ("bandit", "bandit"),
        ]

        for tool_name, command in tools:
            try:
                result = subprocess.run(
                    [command, "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split("\n")[0]
                    self.results.append(
                        HealthCheckResult(
                            name=f"Tool: {tool_name}",
                            status="pass",
                            message=f"✓ {tool_name} available",
                            details={"version": version},
                        )
                    )
                else:
                    self.results.append(
                        HealthCheckResult(
                            name=f"Tool: {tool_name}",
                            status="warn",
                            message=f"⚠ {tool_name} not responding",
                        )
                    )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self.results.append(
                    HealthCheckResult(
                        name=f"Tool: {tool_name}",
                        status="warn",
                        message=f"⚠ {tool_name} not found (install with pip)",
                    )
                )

    def _check_directory_structure(self) -> None:
        """Check that required directories exist."""
        required_dirs: List[str] = ["scripts", "config", "tests"]
        optional_dirs: List[str] = ["repos", "reports", "metrics", "logs"]

        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                self.results.append(
                    HealthCheckResult(
                        name=f"Directory: {dir_path}",
                        status="pass",
                        message=f"✓ {dir_path}/ exists",
                    )
                )
            else:
                self.results.append(
                    HealthCheckResult(
                        name=f"Directory: {dir_path}",
                        status="fail",
                        message=f"✗ Required directory {dir_path}/ not found",
                    )
                )

        for dir_path in optional_dirs:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                self.results.append(
                    HealthCheckResult(
                        name=f"Directory: {dir_path}",
                        status="pass",
                        message=f"✓ {dir_path}/ exists",
                    )
                )

    def _check_permissions(self) -> None:
        """Check file permissions on scripts."""
        scripts_dir = Path("scripts")
        if scripts_dir.exists():
            python_scripts = list(scripts_dir.glob("*.py"))
            executable_count: int = sum(
                1 for script in python_scripts if os.access(script, os.X_OK)
            )

            if executable_count > 0:
                self.results.append(
                    HealthCheckResult(
                        name="Script Permissions",
                        status="pass",
                        message=f"✓ {executable_count} executable scripts",
                        details={"executable": executable_count, "total": len(python_scripts)},
                    )
                )

    def _check_github_token(self) -> None:
        """Check GitHub token configuration."""
        gh_token: Optional[str] = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

        if gh_token:
            # Mask token for display
            masked = gh_token[:4] + "*" * (len(gh_token) - 8) + gh_token[-4:]
            self.results.append(
                HealthCheckResult(
                    name="GitHub Token",
                    status="pass",
                    message=f"✓ GitHub token configured ({masked})",
                )
            )
        else:
            self.results.append(
                HealthCheckResult(
                    name="GitHub Token",
                    status="warn",
                    message="⚠ GitHub token not set (PR creation will be skipped)",
                )
            )

    def _check_git_config(self) -> None:
        """Check git configuration."""
        try:
            # Check git user name
            result = subprocess.run(
                ["git", "config", "user.name"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.results.append(
                    HealthCheckResult(
                        name="Git Config",
                        status="pass",
                        message=f"✓ Git configured ({result.stdout.strip()})",
                    )
                )
            else:
                self.results.append(
                    HealthCheckResult(
                        name="Git Config", status="warn", message="⚠ Git user.name not configured"
                    )
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.results.append(
                HealthCheckResult(name="Git Config", status="warn", message="⚠ Git not available")
            )

    def _check_cloned_repos(self) -> None:
        """Check cloned repositories."""
        repos_dir = Path("repos")
        if repos_dir.exists():
            repos: List[Path] = [
                d for d in repos_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]

            if repos:
                self.results.append(
                    HealthCheckResult(
                        name="Cloned Repositories",
                        status="pass",
                        message=f"✓ {len(repos)} repositories cloned",
                        details={"count": len(repos), "repos": [r.name for r in repos]},
                    )
                )
            else:
                self.results.append(
                    HealthCheckResult(
                        name="Cloned Repositories",
                        status="warn",
                        message="⚠ No repositories cloned yet",
                    )
                )
        else:
            self.results.append(
                HealthCheckResult(
                    name="Cloned Repositories",
                    status="warn",
                    message="⚠ repos/ directory not found",
                )
            )

    def _check_recent_scans(self) -> None:
        """Check for recent scan results."""
        findings_file = Path("findings.json")
        if findings_file.exists():
            try:
                stat = findings_file.stat()
                age_hours: float = (datetime.now().timestamp() - stat.st_mtime) / 3600

                with safe_open(findings_file, allowed_base=False) as f:
                    data: Dict[str, Any] = json.load(f)
                    finding_count: int = len(data.get("findings", []))

                if age_hours < 24:
                    self.results.append(
                        HealthCheckResult(
                            name="Recent Scans",
                            status="pass",
                            message=f"✓ Scan results from {age_hours:.1f}h ago ({finding_count} findings)",
                            details={"age_hours": age_hours, "findings": finding_count},
                        )
                    )
                else:
                    self.results.append(
                        HealthCheckResult(
                            name="Recent Scans",
                            status="warn",
                            message=f"⚠ Last scan was {age_hours:.1f}h ago (consider re-scanning)",
                        )
                    )
            except (json.JSONDecodeError, KeyError):
                self.results.append(
                    HealthCheckResult(
                        name="Recent Scans",
                        status="warn",
                        message="⚠ findings.json exists but is invalid",
                    )
                )
        else:
            self.results.append(
                HealthCheckResult(
                    name="Recent Scans",
                    status="warn",
                    message="⚠ No scan results found (run scan first)",
                )
            )

    def _check_metrics(self) -> None:
        """Check performance metrics."""
        metrics_file = Path("metrics/performance.json")
        if metrics_file.exists():
            try:
                with safe_open(metrics_file, allowed_base=False) as f:
                    data: Dict[str, Any] = json.load(f)
                    op_count: int = data.get("total_operations", 0)

                self.results.append(
                    HealthCheckResult(
                        name="Performance Metrics",
                        status="pass",
                        message=f"✓ {op_count} operations tracked",
                        details={"operations": op_count},
                    )
                )
            except (json.JSONDecodeError, KeyError):
                self.results.append(
                    HealthCheckResult(
                        name="Performance Metrics",
                        status="warn",
                        message="⚠ Metrics file exists but is invalid",
                    )
                )

    def _print_summary(self) -> None:
        """Print health check summary."""
        print("\n" + "=" * 60)
        print("HEALTH CHECK SUMMARY")
        print("=" * 60)

        # Count results by status
        passing: int = sum(1 for r in self.results if r.is_passing())
        warnings: int = sum(1 for r in self.results if r.is_warning())
        failing: int = sum(1 for r in self.results if r.is_failing())

        total: int = len(self.results)

        print(f"Total Checks: {total}")
        print(f"  ✓ Passing: {passing}")
        if warnings > 0:
            print(f"  ⚠ Warnings: {warnings}")
        if failing > 0:
            print(f"  ✗ Failing: {failing}")

        # Print details if verbose or if there are failures
        if self.verbose or failing > 0 or warnings > 0:
            print("\nDetailed Results:")
            for result in self.results:
                if self.verbose or not result.is_passing():
                    print(f"  {result.message}")
                    if self.verbose and result.details:
                        for key, value in result.details.items():
                            print(f"    {key}: {value}")

        # Overall status
        print("\n" + "=" * 60)
        if failing == 0:
            if warnings == 0:
                print("✅ HEALTHY - All checks passed!")
            else:
                print(f"⚠️  MOSTLY HEALTHY - {warnings} warnings")
        else:
            print(f"❌ UNHEALTHY - {failing} critical issues")

        print("=" * 60 + "\n")

    def export_results(self, output_file: str) -> None:
        """Export health check results to JSON.

        Args:
            output_file: Path to output JSON file
        """
        output_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_checks": len(self.results),
            "passing": sum(1 for r in self.results if r.is_passing()),
            "warnings": sum(1 for r in self.results if r.is_warning()),
            "failing": sum(1 for r in self.results if r.is_failing()),
            "checks": [
                {"name": r.name, "status": r.status, "message": r.message, "details": r.details}
                for r in self.results
            ],
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with safe_open(output_path, "w", allowed_base=False) as f:
            json.dump(output_data, f, indent=2)

        print(f"Health check results exported to: {output_file}")


def main() -> None:
    """Main entry point for health check CLI."""
    import argparse

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Health check for security-central infrastructure"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed information")
    parser.add_argument("--output", help="Export results to JSON file")
    parser.add_argument(
        "--fail-on-warnings", action="store_true", help="Exit with non-zero status on warnings"
    )

    args: argparse.Namespace = parser.parse_args()

    # Run health checks
    checker = HealthChecker(verbose=args.verbose)
    all_passing: bool = checker.run_all_checks()

    # Export if requested
    if args.output:
        checker.export_results(args.output)

    # Exit with appropriate status code
    if not all_passing:
        sys.exit(1)
    elif args.fail_on_warnings and any(r.is_warning() for r in checker.results):
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
