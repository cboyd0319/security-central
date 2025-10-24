#!/usr/bin/env python3
"""
Generate dynamic repository matrix for GitHub Actions workflows.

Reads repos.yml and outputs a JSON matrix that can be used in workflow matrix strategies.
"""

import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Any


def generate_matrix(
    config_path: str = 'config/repos.yml',
    output_format: str = 'json'
) -> str:
    """Generate repository matrix from configuration.

    Args:
        config_path: Path to repos.yml configuration file
        output_format: Output format (json or github)

    Returns:
        JSON string of repository matrix

    Example output for GitHub Actions:
        {"include": [
            {"repo": "repo1", "name": "My Repo", "tech": "python"},
            {"repo": "repo2", "name": "Other Repo", "tech": "npm"}
        ]}
    """
    # Load repos configuration
    with open(config_path) as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    repositories: List[Dict[str, Any]] = config.get('repositories', [])

    # Build matrix
    matrix_entries: List[Dict[str, Any]] = []

    for repo in repositories:
        # Extract repository info
        repo_name: str = repo['name']
        repo_url: str = repo['url']
        tech_stack: List[str] = repo.get('tech_stack', [])

        # Primary tech (first in list)
        primary_tech: str = tech_stack[0] if tech_stack else 'unknown'

        # Create matrix entry
        entry: Dict[str, Any] = {
            'repo': repo_name,
            'name': repo_name,
            'url': repo_url,
            'tech': primary_tech,
            'tech_stack': tech_stack
        }

        # Add optional fields if present
        if 'branch' in repo:
            entry['branch'] = repo['branch']

        if 'scan_frequency' in repo:
            entry['frequency'] = repo['scan_frequency']

        matrix_entries.append(entry)

    # Format output
    if output_format == 'github':
        # GitHub Actions matrix format
        output = {
            'include': matrix_entries
        }
        return json.dumps(output, separators=(',', ':'))
    else:
        # Pretty JSON format
        return json.dumps(matrix_entries, indent=2)


def generate_tech_matrix(config_path: str = 'config/repos.yml') -> str:
    """Generate technology-based matrix for parallel scanning.

    Args:
        config_path: Path to repos.yml configuration file

    Returns:
        JSON string of technology matrix

    Example:
        {"include": [
            {"tech": "python", "repos": ["repo1", "repo2"]},
            {"tech": "npm", "repos": ["repo3"]}
        ]}
    """
    with open(config_path) as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    repositories: List[Dict[str, Any]] = config.get('repositories', [])

    # Group by technology
    tech_groups: Dict[str, List[str]] = {}

    for repo in repositories:
        repo_name: str = repo['name']
        tech_stack: List[str] = repo.get('tech_stack', [])

        for tech in tech_stack:
            if tech not in tech_groups:
                tech_groups[tech] = []
            tech_groups[tech].append(repo_name)

    # Build matrix
    matrix_entries: List[Dict[str, Any]] = [
        {'tech': tech, 'repos': repos}
        for tech, repos in sorted(tech_groups.items())
    ]

    output = {
        'include': matrix_entries
    }

    return json.dumps(output, separators=(',', ':'))


def print_matrix_info(config_path: str = 'config/repos.yml') -> None:
    """Print human-readable matrix information.

    Args:
        config_path: Path to repos.yml configuration file
    """
    with open(config_path) as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    repositories: List[Dict[str, Any]] = config.get('repositories', [])

    print("\n" + "="*60)
    print("REPOSITORY MATRIX INFO")
    print("="*60)
    print(f"Total Repositories: {len(repositories)}")

    # Tech stack breakdown
    tech_counts: Dict[str, int] = {}
    for repo in repositories:
        for tech in repo.get('tech_stack', []):
            tech_counts[tech] = tech_counts.get(tech, 0) + 1

    print("\nTechnology Breakdown:")
    for tech, count in sorted(tech_counts.items()):
        print(f"  {tech}: {count} repositories")

    # List repositories
    print("\nRepositories:")
    for repo in repositories:
        tech_str = ', '.join(repo.get('tech_stack', []))
        print(f"  • {repo['name']} ({tech_str})")

    print("="*60 + "\n")


def main() -> None:
    """Main entry point for matrix generation CLI."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Generate repository matrix for GitHub Actions'
    )
    parser.add_argument(
        '--config',
        default='config/repos.yml',
        help='Path to repos.yml configuration file'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'github', 'tech'],
        default='github',
        help='Output format (json=pretty, github=compact, tech=by-technology)'
    )
    parser.add_argument(
        '--output',
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Print matrix information instead of JSON'
    )

    args: argparse.Namespace = parser.parse_args()

    # Handle --info flag
    if args.info:
        print_matrix_info(args.config)
        return

    # Generate matrix
    if args.format == 'tech':
        matrix_json: str = generate_tech_matrix(args.config)
    else:
        matrix_json = generate_matrix(args.config, args.format)

    # Output
    if args.output:
        output_path: Path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(matrix_json)
        print(f"Matrix written to: {args.output}")
    else:
        # Print to stdout for GitHub Actions
        print(matrix_json)


if __name__ == '__main__':
    main()
