#!/usr/bin/env python3
"""
Main security scanner - orchestrates scans across all repositories.
"""

import json
import subprocess
import yaml
import argparse
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class MultiRepoScanner:
    def __init__(self, config_path: str = 'config/repos.yml'):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.findings = []

    def scan_all(self) -> Dict:
        """Run all security scans across all repos."""
        for repo in self.config['repositories']:
            print(f"\n{'='*60}")
            print(f"Scanning {repo['name']}")
            print(f"{'='*60}")
            repo_findings = self.scan_repo(repo)
            self.findings.extend(repo_findings)

        return {
            'scan_time': datetime.utcnow().isoformat(),
            'total_repos': len(self.config['repositories']),
            'findings': self.findings,
            'summary': self.generate_summary()
        }

    def scan_repo(self, repo: Dict) -> List[Dict]:
        """Scan a single repository."""
        repo_dir = f"repos/{repo['name']}"
        findings = []

        # Python projects
        if 'python' in repo['tech_stack']:
            findings.extend(self.scan_python(repo_dir, repo['name']))

        # Java/Kotlin/Scala projects
        if any(lang in repo['tech_stack'] for lang in ['java', 'kotlin', 'scala']):
            findings.extend(self.scan_jvm(repo_dir, repo['name']))

        # JavaScript/npm projects
        if any(lang in repo['tech_stack'] for lang in ['npm', 'react']):
            findings.extend(self.scan_npm(repo_dir, repo['name']))

        # PowerShell projects
        if 'powershell' in repo['tech_stack']:
            findings.extend(self.scan_powershell(repo_dir, repo['name']))

        return findings

    def scan_python(self, repo_dir: str, repo_name: str) -> List[Dict]:
        """Scan Python dependencies for vulnerabilities."""
        findings = []
        print(f"  🐍 Scanning Python dependencies...")

        # Safety check
        requirements_files = list(Path(repo_dir).glob('**/requirements*.txt'))
        requirements_files.extend(Path(repo_dir).glob('**/pyproject.toml'))

        for req_file in requirements_files:
            # pip-audit (comprehensive)
            try:
                result = subprocess.run([
                    'pip-audit', '--format', 'json',
                    '--requirement', str(req_file)
                ], capture_output=True, text=True, timeout=120)

                if result.stdout:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get('dependencies', []):
                        findings.append({
                            'repo': repo_name,
                            'type': 'python_dependency',
                            'severity': self.map_severity(vuln.get('vulns', [{}])[0].get('severity', 'MEDIUM')),
                            'package': vuln['name'],
                            'version': vuln['version'],
                            'cve': vuln.get('vulns', [{}])[0].get('id', 'N/A'),
                            'advisory': vuln.get('vulns', [{}])[0].get('description', ''),
                            'fixed_in': vuln.get('vulns', [{}])[0].get('fix_versions', []),
                            'tool': 'pip-audit',
                            'file': str(req_file.relative_to(repo_dir))
                        })
            except Exception as e:
                print(f"    ⚠️  pip-audit failed: {e}")

            # Safety check
            try:
                result = subprocess.run([
                    'safety', 'check', '--json',
                    '--file', str(req_file)
                ], capture_output=True, text=True, timeout=120)

                if result.stdout and result.stdout != '[]':
                    safety_data = json.loads(result.stdout)
                    for vuln in safety_data:
                        findings.append({
                            'repo': repo_name,
                            'type': 'python_dependency',
                            'severity': self.map_severity(vuln.get('severity', 'MEDIUM')),
                            'package': vuln['package'],
                            'version': vuln['installed_version'],
                            'cve': vuln.get('CVE', 'N/A'),
                            'advisory': vuln.get('advisory', ''),
                            'fixed_in': vuln.get('vulnerable_spec', []),
                            'tool': 'safety',
                            'file': str(req_file.relative_to(repo_dir))
                        })
            except Exception as e:
                print(f"    ⚠️  Safety check failed: {e}")

        print(f"    ✓ Found {len([f for f in findings if f['repo'] == repo_name and f['type'] == 'python_dependency'])} Python issues")
        return findings

    def scan_jvm(self, repo_dir: str, repo_name: str) -> List[Dict]:
        """Scan JVM dependencies."""
        findings = []
        print(f"  ☕ Scanning JVM dependencies...")

        # Check for pom.xml, build.gradle, maven_install.json
        has_maven = (Path(repo_dir) / 'pom.xml').exists()
        has_gradle = (Path(repo_dir) / 'build.gradle').exists()
        has_bazel = (Path(repo_dir) / 'maven_install.json').exists()

        if not (has_maven or has_gradle or has_bazel):
            print(f"    ⓘ No JVM build files found")
            return findings

        # OSV Scanner for JVM
        try:
            result = subprocess.run([
                'osv-scanner',
                '--format', 'json',
                '--recursive',
                repo_dir
            ], capture_output=True, text=True, timeout=180)

            if result.stdout:
                osv_data = json.loads(result.stdout)
                for vuln_result in osv_data.get('results', []):
                    for pkg in vuln_result.get('packages', []):
                        for vuln in pkg.get('vulnerabilities', []):
                            findings.append({
                                'repo': repo_name,
                                'type': 'jvm_dependency',
                                'severity': self.map_severity(vuln.get('database_specific', {}).get('severity', 'MEDIUM')),
                                'package': pkg.get('package', {}).get('name', 'unknown'),
                                'version': pkg.get('package', {}).get('version', 'unknown'),
                                'cve': vuln.get('id', 'N/A'),
                                'advisory': vuln.get('summary', ''),
                                'tool': 'osv-scanner'
                            })
        except Exception as e:
            print(f"    ⚠️  OSV Scanner failed: {e}")

        print(f"    ✓ Found {len([f for f in findings if f['repo'] == repo_name and f['type'] == 'jvm_dependency'])} JVM issues")
        return findings

    def scan_npm(self, repo_dir: str, repo_name: str) -> List[Dict]:
        """Scan npm dependencies."""
        findings = []
        print(f"  📦 Scanning npm dependencies...")

        package_json = Path(repo_dir) / 'package.json'
        if not package_json.exists():
            print(f"    ⓘ No package.json found")
            return findings

        # npm audit
        try:
            result = subprocess.run([
                'npm', 'audit', '--json'
            ], cwd=repo_dir, capture_output=True, text=True, timeout=120)

            if result.stdout:
                audit_data = json.loads(result.stdout)

                # npm audit v7+ format
                if 'vulnerabilities' in audit_data:
                    for pkg_name, vuln_info in audit_data['vulnerabilities'].items():
                        if vuln_info.get('severity'):
                            findings.append({
                                'repo': repo_name,
                                'type': 'npm_dependency',
                                'severity': vuln_info['severity'].upper(),
                                'package': pkg_name,
                                'version': vuln_info.get('range', 'unknown'),
                                'cve': vuln_info.get('via', [{}])[0].get('url', 'N/A') if isinstance(vuln_info.get('via'), list) else 'N/A',
                                'advisory': str(vuln_info.get('via', '')),
                                'tool': 'npm-audit'
                            })

                # npm audit v6 format (legacy)
                elif 'advisories' in audit_data:
                    for advisory_id, advisory in audit_data['advisories'].items():
                        findings.append({
                            'repo': repo_name,
                            'type': 'npm_dependency',
                            'severity': advisory['severity'].upper(),
                            'package': advisory['module_name'],
                            'version': advisory.get('findings', [{}])[0].get('version', 'unknown'),
                            'cve': advisory.get('cves', ['N/A'])[0],
                            'advisory': advisory['overview'],
                            'fixed_in': advisory.get('patched_versions', ''),
                            'tool': 'npm-audit'
                        })
        except Exception as e:
            print(f"    ⚠️  npm audit failed: {e}")

        print(f"    ✓ Found {len([f for f in findings if f['repo'] == repo_name and f['type'] == 'npm_dependency'])} npm issues")
        return findings

    def scan_powershell(self, repo_dir: str, repo_name: str) -> List[Dict]:
        """Scan PowerShell code."""
        findings = []
        print(f"  ⚡ Scanning PowerShell code...")

        # Check if PowerShell files exist
        ps_files = list(Path(repo_dir).rglob('*.ps1'))
        ps_files.extend(Path(repo_dir).rglob('*.psm1'))

        if not ps_files:
            print(f"    ⓘ No PowerShell files found")
            return findings

        # PSScriptAnalyzer
        try:
            result = subprocess.run([
                'pwsh', '-Command',
                f"Invoke-ScriptAnalyzer -Path '{repo_dir}' -Recurse -Severity Error,Warning | ConvertTo-Json"
            ], capture_output=True, text=True, timeout=120)

            if result.stdout:
                try:
                    analyzer_data = json.loads(result.stdout)
                    # Handle both single object and array
                    if not isinstance(analyzer_data, list):
                        analyzer_data = [analyzer_data]

                    for issue in analyzer_data:
                        if issue.get('Severity') in ['Error', 'Warning']:
                            findings.append({
                                'repo': repo_name,
                                'type': 'powershell_code_quality',
                                'severity': 'HIGH' if issue['Severity'] == 'Error' else 'MEDIUM',
                                'file': issue.get('ScriptPath', ''),
                                'line': issue.get('Line', 0),
                                'rule': issue.get('RuleName', ''),
                                'message': issue.get('Message', ''),
                                'tool': 'PSScriptAnalyzer'
                            })
                except json.JSONDecodeError:
                    pass  # No issues found (empty output)
        except Exception as e:
            print(f"    ⚠️  PSScriptAnalyzer failed: {e}")

        print(f"    ✓ Found {len([f for f in findings if f['repo'] == repo_name and f['type'] == 'powershell_code_quality'])} PowerShell issues")
        return findings

    def map_severity(self, severity: str) -> str:
        """Normalize severity levels."""
        if not severity:
            return 'MEDIUM'

        severity_map = {
            'critical': 'CRITICAL',
            'high': 'HIGH',
            'medium': 'MEDIUM',
            'moderate': 'MEDIUM',
            'low': 'LOW',
            'info': 'LOW'
        }
        return severity_map.get(str(severity).lower(), 'MEDIUM')

    def generate_summary(self) -> Dict:
        """Generate summary statistics."""
        from collections import Counter

        severity_counts = Counter(f.get('severity', 'MEDIUM') for f in self.findings)
        repo_counts = Counter(f['repo'] for f in self.findings)
        type_counts = Counter(f['type'] for f in self.findings)

        return {
            'total_findings': len(self.findings),
            'by_severity': dict(severity_counts),
            'by_repo': dict(repo_counts),
            'by_type': dict(type_counts),
            'critical_count': severity_counts.get('CRITICAL', 0),
            'high_count': severity_counts.get('HIGH', 0),
            'medium_count': severity_counts.get('MEDIUM', 0),
            'low_count': severity_counts.get('LOW', 0)
        }

    def export_sarif(self, output_path: str):
        """Export findings to SARIF format for GitHub."""
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "security-central",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/cboyd0319/security-central"
                    }
                },
                "results": []
            }]
        }

        for finding in self.findings:
            sarif_result = {
                "ruleId": f"{finding['type']}-{finding.get('cve', 'unknown')}",
                "level": self.severity_to_sarif_level(finding.get('severity', 'MEDIUM')),
                "message": {
                    "text": finding.get('advisory', finding.get('message', 'Security vulnerability detected'))
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": f"repos/{finding['repo']}/{finding.get('file', '')}"
                        }
                    }
                }]
            }

            # Add line number if available
            if 'line' in finding:
                sarif_result['locations'][0]['physicalLocation']['region'] = {
                    'startLine': finding['line']
                }

            sarif['runs'][0]['results'].append(sarif_result)

        with open(output_path, 'w') as f:
            json.dump(sarif, f, indent=2)

    def severity_to_sarif_level(self, severity: str) -> str:
        """Map severity to SARIF levels."""
        mapping = {
            'CRITICAL': 'error',
            'HIGH': 'error',
            'MEDIUM': 'warning',
            'LOW': 'note'
        }
        return mapping.get(severity, 'warning')


def main():
    parser = argparse.ArgumentParser(description='Scan all monitored repos for security issues')
    parser.add_argument('--output', default='findings.json', help='Output JSON file')
    parser.add_argument('--sarif', default='findings.sarif', help='Output SARIF file')
    args = parser.parse_args()

    scanner = MultiRepoScanner()
    results = scanner.scan_all()

    # Write JSON output
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)

    # Write SARIF output
    scanner.export_sarif(args.sarif)

    # Print summary
    print(f"\n{'='*60}")
    print("SCAN COMPLETE")
    print(f"{'='*60}")
    print(f"Total findings: {results['summary']['total_findings']}")
    print(f"  CRITICAL: {results['summary']['critical_count']}")
    print(f"  HIGH:     {results['summary']['high_count']}")
    print(f"  MEDIUM:   {results['summary']['medium_count']}")
    print(f"  LOW:      {results['summary']['low_count']}")
    print(f"\nResults written to {args.output}")
    print(f"SARIF written to {args.sarif}")


if __name__ == '__main__':
    main()
