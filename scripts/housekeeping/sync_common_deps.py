#!/usr/bin/env python3
"""
Sync common dependencies across repos (e.g., if PyGuard uses Black 24.x, JobSentinel should too).
"""

import os
import subprocess
from pathlib import Path
from typing import Dict

import yaml

from utils import safe_open


class CommonDepsSync:
    def __init__(self, config_path: str = "config/common-dependencies.yml"):
        with safe_open(config_path, allowed_base=False) as f:
            self.config = yaml.safe_load(f)

    def sync_all_repos(self, auto_create_pr: bool = False):
        """Sync common dependencies across all repos."""
        repos_dir = Path("repos")

        for repo_dir in repos_dir.iterdir():
            if repo_dir.is_dir() and not repo_dir.name.startswith("."):
                self.sync_repo(repo_dir, auto_create_pr)

    def sync_repo(self, repo_dir: Path, auto_create_pr: bool):
        """Sync common deps in a single repo."""
        print(f"\n🔄 Syncing common deps in {repo_dir.name}...")

        updated = False

        # Python repos
        if (repo_dir / "requirements.txt").exists() or (repo_dir / "pyproject.toml").exists():
            if self.sync_python_deps(repo_dir):
                updated = True

        # npm repos
        if (repo_dir / "package.json").exists():
            if self.sync_npm_deps(repo_dir):
                updated = True

        if updated:
            print(f"  ✅ Dependencies synced")
            if auto_create_pr:
                self.create_pr(repo_dir)
        else:
            print(f"  ✓ Already synced")

    def sync_python_deps(self, repo_dir: Path) -> bool:
        """Sync Python common dependencies."""
        common_py_deps = self.config.get("python", {})
        updated = False

        # Update requirements.txt
        req_file = repo_dir / "requirements.txt"
        if req_file.exists():
            with safe_open(req_file, allowed_base=False) as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                updated_line = line
                for dep_name, version in common_py_deps.items():
                    if line.strip().startswith(dep_name):
                        updated_line = f"{dep_name}>={version}\n"
                        if line != updated_line:
                            updated = True
                new_lines.append(updated_line)

            if updated:
                with safe_open(req_file, "w", allowed_base=False) as f:
                    f.writelines(new_lines)

        return updated

    def sync_npm_deps(self, repo_dir: Path) -> bool:
        """Sync npm common dependencies."""
        # Similar implementation for npm
        return False  # Placeholder

    def create_pr(self, repo_dir: Path):
        """Create PR for dependency sync."""
        os.chdir(repo_dir)

        branch_name = "chore/sync-common-dependencies"

        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "chore: sync common dependencies\n\n🤖 Automated by security-central",
            ],
            check=True,
        )

        subprocess.run(["git", "push", "origin", branch_name], check=True)

        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "chore: sync common dependencies",
                "--body",
                "🤖 Automated dependency synchronization",
                "--label",
                "dependencies,automated",
            ],
            check=True,
        )

        subprocess.run(["git", "checkout", "main"], check=True)
        os.chdir("../..")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync common dependencies")
    parser.add_argument("--config", default="config/common-dependencies.yml")
    parser.add_argument("--auto-create-pr", action="store_true")
    args = parser.parse_args()

    syncer = CommonDepsSync(args.config)
    syncer.sync_all_repos(args.auto_create_pr)


if __name__ == "__main__":
    main()
