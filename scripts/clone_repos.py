#!/usr/bin/env python3
"""
Clone all monitored repositories for scanning.
"""

import os
import subprocess
import yaml
from pathlib import Path


def clone_repos(config_path: str = 'config/repos.yml', repos_dir: str = 'repos'):
    """Clone all repositories defined in config."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    repos_path = Path(repos_dir)
    repos_path.mkdir(exist_ok=True)

    for repo in config['repositories']:
        repo_name = repo['name']
        repo_url = repo['url']
        repo_dir = repos_path / repo_name

        if repo_dir.exists():
            print(f"✓ {repo_name} already cloned, pulling latest...")
            subprocess.run(['git', 'pull'], cwd=repo_dir, check=True)
        else:
            print(f"⬇ Cloning {repo_name}...")
            subprocess.run(['git', 'clone', repo_url, str(repo_dir)], check=True)

    print(f"\n✅ All {len(config['repositories'])} repositories ready")


if __name__ == '__main__':
    clone_repos()
