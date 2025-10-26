#!/usr/bin/env python3
"""
Sync GitHub Actions versions across all repos to latest stable versions.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List

import yaml

from utils import safe_open

# Standard GitHub Actions with recommended versions AND commit SHAs
# Format: 'action/name': ('version', 'sha256_hash')
# This ensures supply chain security - pins to exact commits
STANDARD_ACTIONS = {
    "actions/checkout": ("v4", "eef61447b9ff4aafe5dcd4e0bbf5d482be7e7871"),  # v4.2.2
    "actions/setup-python": ("v5", "f677139bbe7f9c59b41e40162b753c062f5d49a3"),  # v5.2.0
    "actions/setup-node": ("v4", "0a44ba7841725637a19e28fa30b79a866c81b0a6"),  # v4.0.4
    "actions/setup-java": ("v4", "b36c23c0d998641eff861008f374ee103c25ac73"),  # v4.4.0
    "actions/upload-artifact": ("v4", "604373da6381bf24206979c74d06a550515601b9"),  # v4.4.1
    "actions/download-artifact": ("v4", "fa0a91b85d4f404e444e00e005971372dc801d16"),  # v4.1.8
    "github/codeql-action/upload-sarif": (
        "v3",
        "f779452ac5af1c261dce0346a8b332175284d93b",
    ),  # v3.27.0
    "github/codeql-action/init": ("v3", "f779452ac5af1c261dce0346a8b332175284d93b"),  # v3.27.0
    "github/codeql-action/analyze": ("v3", "f779452ac5af1c261dce0346a8b332175284d93b"),  # v3.27.0
}

# NOTE: Update these hashes periodically by running:
# gh api repos/actions/checkout/commits/v4 --jq .sha


class GitHubActionsSync:
    def __init__(self, repos_dir: str = "repos"):
        self.repos_dir = Path(repos_dir)
        self.changes = []

    def sync_all_repos(self, auto_create_pr: bool = False):
        """Sync GitHub Actions across all repos."""
        for repo_dir in self.repos_dir.iterdir():
            if repo_dir.is_dir() and not repo_dir.name.startswith("."):
                self.sync_repo(repo_dir, auto_create_pr)

        self.print_summary()

    def sync_repo(self, repo_dir: Path, auto_create_pr: bool):
        """Sync GitHub Actions in a single repo."""
        print(f"\n🔄 Syncing {repo_dir.name}...")

        workflows_dir = repo_dir / ".github" / "workflows"
        if not workflows_dir.exists():
            print(f"  ⏭️  No workflows directory")
            return

        updated_files = []

        for workflow_file in workflows_dir.glob("*.yml"):
            if self.update_workflow_file(workflow_file):
                updated_files.append(workflow_file.name)

        if updated_files:
            print(f"  ✅ Updated {len(updated_files)} workflows")
            self.changes.append({"repo": repo_dir.name, "files": updated_files})

            if auto_create_pr:
                self.create_pr(repo_dir, updated_files)
        else:
            print(f"  ✓ Already up to date")

    def update_workflow_file(self, workflow_file: Path) -> bool:
        """Update GitHub Actions versions AND commit hashes in a workflow file."""
        with safe_open(workflow_file, allowed_base=False) as f:
            content = f.read()

        original_content = content
        updated = False

        for action, (version, sha) in STANDARD_ACTIONS.items():
            # Match multiple patterns:
            # 1. uses: actions/checkout@v3
            # 2. uses: actions/checkout@v4
            # 3. uses: actions/checkout@abc123 (old hash)
            # 4. uses: actions/checkout@v4.2.0 (specific version)

            # Pattern: Replace any existing version/hash with version + hash
            pattern = f"uses:\\s+{re.escape(action)}@[a-zA-Z0-9._-]+"
            replacement = f"uses: {action}@{sha}  # {version}"

            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                updated = True

        if updated:
            with safe_open(workflow_file, "w", allowed_base=False) as f:
                f.write(content)

        return updated

    def create_pr(self, repo_dir: Path, updated_files: List[str]):
        """Create PR for GitHub Actions updates."""
        os.chdir(repo_dir)

        branch_name = "chore/update-github-actions"

        # Create branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

        # Commit changes
        subprocess.run(["git", "add", ".github/workflows/"], check=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"chore: update GitHub Actions to latest versions\n\n"
                f"Updated workflows:\n"
                + "\n".join(f"- {f}" for f in updated_files)
                + "\n\n🤖 Automated by security-central",
            ],
            check=True,
        )

        # Push
        subprocess.run(["git", "push", "origin", branch_name], check=True)

        # Create PR
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "chore: update GitHub Actions to latest versions",
                "--body",
                self.generate_pr_body(updated_files),
                "--label",
                "dependencies,automated",
            ],
            check=True,
        )

        # Return to main
        subprocess.run(["git", "checkout", "main"], check=True)
        os.chdir("../..")

    def generate_pr_body(self, updated_files: List[str]) -> str:
        """Generate PR body."""
        return f"""## GitHub Actions Version Update

This PR updates GitHub Actions to their latest stable versions **with commit hash pinning** for supply chain security.

### Updated Workflows

{chr(10).join(f"- `{f}`" for f in updated_files)}

### Changes

Standard actions have been updated to recommended versions with SHA pinning:

{chr(10).join(f"- `{action}@{sha}` ({version})" for action, (version, sha) in STANDARD_ACTIONS.items())}

### Security Benefits

✅ **Pinned to specific commits** - prevents tag hijacking attacks
✅ **Latest stable versions** - includes security patches
✅ **Automated updates** - security-central keeps hashes current

### Verification

You can verify these hashes match the tagged versions:

```bash
# Example for actions/checkout
gh api repos/actions/checkout/commits/v4 --jq .sha
```

---

🤖 Automated by [security-central](https://github.com/cboyd0319/security-central)
"""

    def print_summary(self):
        """Print summary of changes."""
        print(f"\n{'='*60}")
        print("GITHUB ACTIONS SYNC COMPLETE")
        print(f"{'='*60}")
        print(f"Repos updated: {len(self.changes)}")
        for change in self.changes:
            print(f"  - {change['repo']}: {len(change['files'])} workflows")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync GitHub Actions versions")
    parser.add_argument(
        "--auto-create-pr", action="store_true", help="Automatically create PRs for updates"
    )
    args = parser.parse_args()

    syncer = GitHubActionsSync()
    syncer.sync_all_repos(args.auto_create_pr)


if __name__ == "__main__":
    main()
