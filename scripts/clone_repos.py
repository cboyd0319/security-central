#!/usr/bin/env python3
"""
Clone all monitored repositories for scanning.
"""

import os
import subprocess
import yaml
from pathlib import Path
from typing import Tuple, List, Dict


def clone_repos(
    config_path: str = 'config/repos.yml',
    repos_dir: str = 'repos'
) -> Tuple[int, List[str]]:
    """Clone all repositories defined in config.

    Args:
        config_path: Path to repos.yml configuration file
        repos_dir: Directory to clone repositories into

    Returns:
        Tuple of (successful_count, list_of_failed_repos)

    Example:
        >>> success, failures = clone_repos()
        >>> print(f"Cloned {success} repos, {len(failures)} failed")
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    repos_path = Path(repos_dir)
    repos_path.mkdir(exist_ok=True)

    successful: int = 0
    failed: List[str] = []

    for repo in config['repositories']:
        repo_name = repo['name']
        repo_url = repo['url']
        repo_dir = repos_path / repo_name

        try:
            if repo_dir.exists():
                print(f"✓ {repo_name} already cloned, pulling latest...")
                result = subprocess.run(['git', 'pull'], cwd=repo_dir, 
                                       capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    print(f"  ⚠️  Pull failed: {result.stderr}")
                    failed.append(repo_name)
                else:
                    successful += 1
            else:
                print(f"⬇ Cloning {repo_name}...")
                result = subprocess.run(['git', 'clone', repo_url, str(repo_dir)], 
                                       capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    print(f"  ⚠️  Clone failed: {result.stderr}")
                    failed.append(repo_name)
                else:
                    successful += 1
        except Exception as e:
            print(f"  ⚠️  Error with {repo_name}: {e}")
            failed.append(repo_name)

    print(f"\n✅ {successful}/{len(config['repositories'])} repositories ready")
    if failed:
        print(f"⚠️  Failed to clone: {', '.join(failed)}")
        print("   (This is expected if repos don't exist yet or require authentication)")

    return successful, failed


if __name__ == '__main__':
    clone_repos()
