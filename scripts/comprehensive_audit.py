#!/usr/bin/env python3
"""
Comprehensive dependency audit for all repositories.
"""

import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timezone


class ComprehensiveAuditor:
    def __init__(self, include_license: bool = False, include_maintenance: bool = False, include_security: bool = True):
        self.include_license = include_license
        self.include_maintenance = include_maintenance
        self.include_security = include_security

    def audit(self, output_file: str):
        """Run comprehensive audit across all repositories."""
        results = {
            'audit_time': datetime.now(timezone.utc).isoformat(),
            'repositories': [],
            'summary': {
                'total_repos': 0,
                'total_dependencies': 0,
                'security_issues': 0,
                'license_issues': 0,
                'maintenance_issues': 0
            }
        }

        # Find cloned repos
        repos_dir = Path('repos')
        scanned_any = False
        
        if repos_dir.exists():
            for repo_dir in repos_dir.iterdir():
                if repo_dir.is_dir() and not repo_dir.name.startswith('.'):
                    print(f"Auditing {repo_dir.name}...")
                    repo_results = self.audit_repository(repo_dir)
                    results['repositories'].append(repo_results)
                    results['summary']['total_repos'] += 1
                    scanned_any = True
        
        # If no repos were scanned, audit security-central itself as fallback
        if not scanned_any:
            print("⚠️  No cloned repositories found in repos/ directory.")
            print("   This is expected during initial setup or if repos couldn't be cloned.")
            print("   Audit will run on security-central itself as fallback.")
            
            # Audit security-central itself
            self_results = self.audit_repository(Path('.'))
            self_results['name'] = 'security-central'
            results['repositories'].append(self_results)
            results['summary']['total_repos'] = 1

        # Calculate totals
        for repo in results['repositories']:
            results['summary']['total_dependencies'] += repo.get('dependency_count', 0)
            results['summary']['security_issues'] += len(repo.get('security_findings', []))
            results['summary']['license_issues'] += len(repo.get('license_issues', []))
            results['summary']['maintenance_issues'] += len(repo.get('maintenance_concerns', []))

        # Write output
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nAudit complete: {output_file}")
        print(f"Total repositories: {results['summary']['total_repos']}")
        print(f"Total dependencies: {results['summary']['total_dependencies']}")
        print(f"Security issues: {results['summary']['security_issues']}")

        return results

    def audit_repository(self, repo_dir: Path) -> Dict:
        """Audit a single repository."""
        repo_result = {
            'name': repo_dir.name,
            'path': str(repo_dir),
            'dependency_count': 0,
            'security_findings': [],
            'license_issues': [],
            'maintenance_concerns': []
        }

        # Count dependencies
        repo_result['dependency_count'] = self.count_dependencies(repo_dir)

        # Security checks
        if self.include_security:
            repo_result['security_findings'] = self.check_security(repo_dir)

        # License checks
        if self.include_license:
            repo_result['license_issues'] = self.check_licenses(repo_dir)

        # Maintenance checks
        if self.include_maintenance:
            repo_result['maintenance_concerns'] = self.check_maintenance(repo_dir)

        return repo_result

    def count_dependencies(self, repo_dir: Path) -> int:
        """Count total dependencies in a repository."""
        count = 0

        # Python
        requirements_file = repo_dir / 'requirements.txt'
        if requirements_file.exists():
            with open(requirements_file) as f:
                count += len([line for line in f if line.strip() and not line.startswith('#')])

        # npm
        package_json = repo_dir / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    count += len(data.get('dependencies', {}))
                    count += len(data.get('devDependencies', {}))
            except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                # Handle missing or invalid package.json files
                print(f"    ⚠️  Failed to parse {package_json}: {e}")

        return count

    def check_security(self, repo_dir: Path) -> List[Dict]:
        """Basic security checks."""
        findings = []
        
        # Check for common security files
        if not (repo_dir / 'SECURITY.md').exists():
            findings.append({
                'type': 'missing_security_policy',
                'severity': 'LOW',
                'message': 'No SECURITY.md file found'
            })

        return findings

    def check_licenses(self, repo_dir: Path) -> List[Dict]:
        """Check for license compliance issues."""
        issues = []
        
        if not (repo_dir / 'LICENSE').exists():
            issues.append({
                'type': 'missing_license',
                'severity': 'MEDIUM',
                'message': 'No LICENSE file found'
            })

        return issues

    def check_maintenance(self, repo_dir: Path) -> List[Dict]:
        """Check for maintenance concerns."""
        concerns = []
        
        # Check for README
        if not (repo_dir / 'README.md').exists():
            concerns.append({
                'type': 'missing_readme',
                'severity': 'LOW',
                'message': 'No README.md file found'
            })

        return concerns


def main():
    parser = argparse.ArgumentParser(description='Run comprehensive dependency audit')
    parser.add_argument('--output', default='weekly-audit.json', help='Output file')
    parser.add_argument('--include-license-check', action='store_true', help='Include license checks')
    parser.add_argument('--include-maintenance-check', action='store_true', help='Include maintenance checks')
    parser.add_argument('--include-security-check', action='store_true', default=True, help='Include security checks')
    args = parser.parse_args()

    auditor = ComprehensiveAuditor(
        include_license=args.include_license_check,
        include_maintenance=args.include_maintenance_check,
        include_security=args.include_security_check
    )

    auditor.audit(args.output)


if __name__ == '__main__':
    main()
