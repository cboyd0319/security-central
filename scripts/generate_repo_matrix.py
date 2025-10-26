#!/usr/bin/env python3
"""
Generate dynamic repository matrix for GitHub Actions workflows.

Reads repos.yml and outputs a JSON matrix that can be used in workflow matrix strategies.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from utils import safe_open


def generate_matrix(
    config_path: str = "config/repos.yml",
    output_format: str = "json",
) -> str:
    """Generate repository matrix from configuration.

    Args:
        config_path: Path to repos.yml configuration file
        output_format: Output format (json, github, or compact)

    Returns:
        String in requested format

    Raises:
        ValueError: If output_format is invalid

    Example output for GitHub Actions:
        {"repository": [
            {"repo": "repo1", "name": "My Repo", "tech": "python"},
            {"repo": "repo2", "name": "Other Repo", "tech": "npm"}
        ]}
    """
    # Validate format
    valid_formats = ["json", "github", "compact"]
    if output_format not in valid_formats:
        raise ValueError(f"Invalid output format: {output_format}. Must be one of {valid_formats}")

    # Load repos configuration
    with safe_open(config_path, allowed_base=False) as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    repositories: List[Dict[str, Any]] = config.get("repositories", [])

    # Build matrix
    matrix_entries: List[Dict[str, Any]] = []

    for repo in repositories:
        # Extract repository info
        repo_name: str = repo["name"]
        repo_url: str = repo["url"]

        # Handle both "tech" (single string) and "tech_stack" (list)
        if "tech" in repo and isinstance(repo["tech"], str):
            # Single tech string
            primary_tech: str = repo["tech"]
            tech_stack: List[str] = [primary_tech]
        elif "tech_stack" in repo:
            # Tech stack list
            tech_stack = repo.get("tech_stack", [])
            primary_tech = tech_stack[0] if tech_stack else "unknown"
        else:
            # No tech info
            primary_tech = "unknown"
            tech_stack = []

        # Create matrix entry
        entry: Dict[str, Any] = {
            "repo": repo_name,
            "name": repo_name,
            "url": repo_url,
            "tech": primary_tech,
            "tech_stack": tech_stack,
        }

        # Add optional fields if present
        if "branch" in repo:
            entry["branch"] = repo["branch"]

        if "scan_frequency" in repo:
            entry["frequency"] = repo["scan_frequency"]

        if "critical" in repo:
            entry["critical"] = repo["critical"]

        matrix_entries.append(entry)

    # Format output
    if output_format == "compact":
        # Comma-separated list of repository names
        return ",".join(entry["name"] for entry in matrix_entries)
    elif output_format == "github":
        # GitHub Actions matrix format with "repository" key
        output = {"repository": matrix_entries}
        return json.dumps(output, separators=(",", ":"))
    else:  # json
        # Pretty JSON format with "repository" key
        output = {"repository": matrix_entries}
        return json.dumps(output, indent=2)


def generate_tech_matrix(config_path: str = "config/repos.yml") -> str:
    """Generate technology-based matrix for parallel scanning.

    Args:
        config_path: Path to repos.yml configuration file

    Returns:
        JSON string of technology matrix

    Example:
        {"tech": [
            {"name": "python", "repositories": [
                {"name": "repo1", "url": "..."},
                {"name": "repo2", "url": "..."}
            ]},
            {"name": "npm", "repositories": [{"name": "repo3", "url": "..."}]}
        ]}
    """
    with safe_open(config_path, allowed_base=False) as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    repositories: List[Dict[str, Any]] = config.get("repositories", [])

    # Group by technology with full repository details
    tech_groups: Dict[str, List[Dict[str, Any]]] = {}

    for repo in repositories:
        repo_name: str = repo["name"]
        repo_url: str = repo["url"]

        # Handle both "tech" (single string) and "tech_stack" (list)
        if "tech" in repo and isinstance(repo["tech"], str):
            tech_list = [repo["tech"]]
        elif "tech_stack" in repo:
            tech_list = repo.get("tech_stack", [])
        else:
            tech_list = []

        # Create repository entry
        repo_entry: Dict[str, Any] = {
            "name": repo_name,
            "url": repo_url,
        }

        # Add optional fields
        if "branch" in repo:
            repo_entry["branch"] = repo["branch"]
        if "critical" in repo:
            repo_entry["critical"] = repo["critical"]

        # Add to each technology group
        for tech in tech_list:
            if tech not in tech_groups:
                tech_groups[tech] = []
            tech_groups[tech].append(repo_entry)

    # Build matrix with full repository details
    matrix_entries: List[Dict[str, Any]] = [
        {"name": tech, "repositories": repos}
        for tech, repos in sorted(tech_groups.items())
    ]

    output = {"tech": matrix_entries}

    return json.dumps(output, separators=(",", ":"))


def print_matrix_info(config_path: str = "config/repos.yml") -> None:
    """Print human-readable matrix information.

    Args:
        config_path: Path to repos.yml configuration file
    """
    with safe_open(config_path, allowed_base=False) as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    repositories: List[Dict[str, Any]] = config.get("repositories", [])

    print("\n" + "=" * 60)
    print("REPOSITORY MATRIX INFO")
    print("=" * 60)
    print(f"Total Repositories: {len(repositories)}")

    # Tech stack breakdown
    tech_counts: Dict[str, int] = {}
    for repo in repositories:
        for tech in repo.get("tech_stack", []):
            tech_counts[tech] = tech_counts.get(tech, 0) + 1

    print("\nTechnology Breakdown:")
    for tech, count in sorted(tech_counts.items()):
        print(f"  {tech}: {count} repositories")

    # List repositories
    print("\nRepositories:")
    for repo in repositories:
        tech_str = ", ".join(repo.get("tech_stack", []))
        print(f"  • {repo['name']} ({tech_str})")

    print("=" * 60 + "\n")


def main() -> None:
    """Main entry point for matrix generation CLI."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Generate repository matrix for GitHub Actions"
    )
    parser.add_argument(
        "--config", default="config/repos.yml", help="Path to repos.yml configuration file"
    )
    parser.add_argument(
        "--format",
        choices=["json", "github", "tech"],
        default="github",
        help="Output format (json=pretty, github=compact, tech=by-technology)",
    )
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--info", action="store_true", help="Print matrix information instead of JSON"
    )

    args: argparse.Namespace = parser.parse_args()

    # Handle --info flag
    if args.info:
        print_matrix_info(args.config)
        return

    # Generate matrix
    if args.format == "tech":
        matrix_json: str = generate_tech_matrix(args.config)
    else:
        matrix_json = generate_matrix(args.config, args.format)

    # Output
    if args.output:
        output_path: Path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with safe_open(output_path, "w", allowed_base=False) as f:
            f.write(matrix_json)
        print(f"Matrix written to: {args.output}")
    else:
        # Print to stdout for GitHub Actions
        print(matrix_json)


if __name__ == "__main__":
    main()
