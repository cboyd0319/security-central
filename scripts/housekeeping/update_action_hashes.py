#!/usr/bin/env python3
"""
Update GitHub Actions commit hashes in sync_github_actions.py
Run this periodically to keep hashes current with latest versions.
"""

import subprocess
import json
import re
from pathlib import Path


# Actions to update (from sync_github_actions.py)
ACTIONS_TO_UPDATE = {
    'actions/checkout': 'v4',
    'actions/setup-python': 'v5',
    'actions/setup-node': 'v4',
    'actions/setup-java': 'v4',
    'actions/upload-artifact': 'v4',
    'actions/download-artifact': 'v4',
    'github/codeql-action/upload-sarif': 'v3',
    'github/codeql-action/init': 'v3',
    'github/codeql-action/analyze': 'v3',
}


def get_commit_sha(repo: str, ref: str) -> tuple:
    """Get commit SHA for a given tag/ref using GitHub API."""
    # Extract owner/repo from full path (e.g., actions/checkout)
    result = subprocess.run([
        'gh', 'api', f'repos/{repo}/commits/{ref}',
        '--jq', '.sha'
    ], capture_output=True, text=True)

    if result.returncode == 0:
        sha = result.stdout.strip()

        # Also get the exact version tag
        tag_result = subprocess.run([
            'gh', 'api', f'repos/{repo}/git/ref/tags/{ref}',
            '--jq', '.object.sha'
        ], capture_output=True, text=True)

        # Get latest release info
        release_result = subprocess.run([
            'gh', 'api', f'repos/{repo}/releases/latest',
            '--jq', '.tag_name'
        ], capture_output=True, text=True)

        exact_version = release_result.stdout.strip() if release_result.returncode == 0 else ref

        return sha, exact_version
    else:
        print(f"  ❌ Failed to get SHA for {repo}@{ref}")
        return None, None


def update_sync_script():
    """Update STANDARD_ACTIONS in sync_github_actions.py with latest hashes."""
    print("🔄 Fetching latest GitHub Actions commit hashes...\n")

    script_path = Path('scripts/housekeeping/sync_github_actions.py')

    new_actions = {}

    for action, version in ACTIONS_TO_UPDATE.items():
        print(f"  Fetching {action}@{version}...")
        sha, exact_version = get_commit_sha(action, version)

        if sha:
            print(f"    ✅ {sha[:12]} ({exact_version})")
            new_actions[action] = (version, sha, exact_version)
        else:
            print(f"    ⏭️  Skipping (could not fetch)")

    # Read current script
    with open(script_path) as f:
        content = f.read()

    # Generate new STANDARD_ACTIONS dict
    new_dict = "STANDARD_ACTIONS = {\n"
    for action, (version, sha, exact_version) in new_actions.items():
        new_dict += f"    '{action}': ('{version}', '{sha}'),  # {exact_version}\n"
    new_dict += "}"

    # Replace STANDARD_ACTIONS definition
    pattern = r'STANDARD_ACTIONS = \{[^}]+\}'
    new_content = re.sub(pattern, new_dict, content, flags=re.DOTALL)

    # Write back
    with open(script_path, 'w') as f:
        f.write(new_content)

    print(f"\n✅ Updated {len(new_actions)} action hashes in {script_path}")


def main():
    print("="*60)
    print("  GitHub Actions Hash Updater")
    print("="*60 + "\n")

    update_sync_script()

    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Review the changes:")
    print("   git diff scripts/housekeeping/sync_github_actions.py")
    print()
    print("2. Commit the updated hashes:")
    print("   git add scripts/housekeeping/sync_github_actions.py")
    print("   git commit -m 'chore: update GitHub Actions commit hashes'")
    print()
    print("3. Run housekeeping to sync across all repos:")
    print("   gh workflow run housekeeping.yml")


if __name__ == '__main__':
    main()
