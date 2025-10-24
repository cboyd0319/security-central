#!/usr/bin/env python3
"""
Automatically create PRs to fix security vulnerabilities.
"""

import json
import subprocess
import os
import argparse
from typing import Dict
from pathlib import Path


class AutoPatcher:
    def __init__(self, gh_token: str):
        self.gh_token = gh_token
        os.environ['GH_TOKEN'] = gh_token

    def create_prs(self, triage_file: str, auto_merge_safe_only: bool = False):
        """Create PRs for fixable vulnerabilities."""
        with open(triage_file) as f:
            triage = json.load(f)

        auto_fixes = triage.get('auto_fixes', [])

        if auto_merge_safe_only:
            auto_fixes = [f for f in auto_fixes if f.get('auto_merge_safe', False)]

        print(f"\n🔧 Creating {len(auto_fixes)} patch PRs...")

        for fix in auto_fixes:
            try:
                self.create_pr(fix)
            except Exception as e:
                print(f"  ❌ Failed to create PR for {fix.get('package')}: {e}")

    def create_pr(self, fix: Dict):
        """Create a single security patch PR."""
        repo_name = fix['repo']
        package = fix.get('package', 'unknown')
        cve = fix.get('cve', 'SECURITY')
        branch_name = f"security/auto-patch-{package}-{cve}".replace('/', '-')[:100]

        print(f"\n  📝 {repo_name}: {package} ({cve})")

        repo_dir = f"repos/{repo_name}"
        os.chdir(repo_dir)

        # Check if branch already exists
        existing_branches = subprocess.run(
            ['git', 'branch', '-r'],
            capture_output=True, text=True
        ).stdout

        if branch_name in existing_branches:
            print(f"    ⏭️  PR already exists for this fix")
            os.chdir('../..')
            return

        # Create branch
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)

        # Apply fix based on ecosystem
        try:
            if fix['type'] == 'python_dependency':
                self.fix_python_dependency(fix)
            elif fix['type'] == 'npm_dependency':
                self.fix_npm_dependency(fix)
            elif fix['type'] == 'jvm_dependency':
                self.fix_jvm_dependency(fix)
            else:
                print(f"    ⏭️  Unsupported fix type: {fix['type']}")
                subprocess.run(['git', 'checkout', 'main'])
                subprocess.run(['git', 'branch', '-D', branch_name])
                os.chdir('../..')
                return
        except Exception as e:
            print(f"    ❌ Fix failed: {e}")
            subprocess.run(['git', 'checkout', 'main'])
            subprocess.run(['git', 'branch', '-D', branch_name])
            os.chdir('../..')
            return

        # Check if changes were made
        status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not status.stdout.strip():
            print(f"    ⏭️  No changes needed")
            subprocess.run(['git', 'checkout', 'main'])
            subprocess.run(['git', 'branch', '-D', branch_name])
            os.chdir('../..')
            return

        # Commit changes
        commit_msg = self.generate_commit_message(fix)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)

        # Push branch
        subprocess.run(['git', 'push', 'origin', branch_name], check=True)

        # Create PR
        pr_body = self.generate_pr_body(fix)
        pr_title = f"security: fix {cve} in {package}"

        result = subprocess.run([
            'gh', 'pr', 'create',
            '--title', pr_title,
            '--body', pr_body,
            '--label', 'security,automated',
            '--assignee', '@me'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"    ✅ PR created")

            # Auto-merge if safe
            if fix.get('auto_merge_safe'):
                pr_url = result.stdout.strip()
                pr_number = pr_url.split('/')[-1]

                # Enable auto-merge (requires PR checks to pass)
                subprocess.run([
                    'gh', 'pr', 'merge', pr_number,
                    '--auto', '--squash'
                ], check=True)
                print(f"    🤖 Auto-merge enabled (will merge after CI passes)")
        else:
            print(f"    ❌ PR creation failed: {result.stderr}")

        # Return to main branch
        subprocess.run(['git', 'checkout', 'main'])
        os.chdir('../..')

    def fix_python_dependency(self, fix: Dict):
        """Update Python dependency."""
        package = fix['package']
        fixed_version = fix.get('fixed_in', [''])[0]

        if not fixed_version:
            raise ValueError(f"No fixed version available for {package}")

        # Update requirements.txt
        req_files = [
            'requirements.txt',
            'requirements-dev.txt',
            'requirements/prod.txt',
            'requirements/dev.txt'
        ]

        updated = False
        for req_file in req_files:
            if os.path.exists(req_file):
                with open(req_file, 'r') as f:
                    lines = f.readlines()

                with open(req_file, 'w') as f:
                    for line in lines:
                        if line.strip().startswith(package):
                            # Update version
                            f.write(f"{package}>={fixed_version}\n")
                            updated = True
                        else:
                            f.write(line)

        # Update pyproject.toml if it exists
        if os.path.exists('pyproject.toml'):
            with open('pyproject.toml', 'r') as f:
                content = f.read()

            # Simple string replacement (not perfect but good enough)
            import re
            pattern = f'("{package}.*?")|(\\'{package}.*?\\')'
            replacement = f'"{package}>={fixed_version}"'

            new_content = re.sub(pattern, replacement, content)

            if new_content != content:
                with open('pyproject.toml', 'w') as f:
                    f.write(new_content)
                updated = True

        if not updated:
            raise ValueError(f"Could not find {package} in any dependency file")

    def fix_npm_dependency(self, fix: Dict):
        """Update npm dependency."""
        package = fix['package']
        fixed_version = fix.get('fixed_in', '')

        if not fixed_version:
            raise ValueError(f"No fixed version available for {package}")

        # Use npm to update
        subprocess.run([
            'npm', 'install', f"{package}@{fixed_version}"
        ], check=True)

    def fix_jvm_dependency(self, fix: Dict):
        """Update JVM dependency (basic implementation)."""
        # This is complex - for now, just add comment to manual review
        print(f"    ⚠️  JVM dependency updates require manual review")
        raise ValueError("JVM dependency updates not yet automated")

    def generate_commit_message(self, fix: Dict) -> str:
        """Generate semantic commit message."""
        package = fix.get('package', 'dependency')
        cve = fix.get('cve', 'security issue')
        severity = fix.get('severity', 'UNKNOWN')

        msg = f"""security: update {package} to fix {cve}

Severity: {severity}
Current version: {fix.get('version', 'unknown')}
Fixed version: {fix.get('fixed_in', ['unknown'])[0]}

{fix.get('advisory', 'Security vulnerability detected.')}

🤖 Automatically generated by security-central
Auto-merge safe: {fix.get('auto_merge_safe', False)}
"""
        return msg

    def generate_pr_body(self, fix: Dict) -> str:
        """Generate PR description."""
        package = fix.get('package', 'dependency')
        cve = fix.get('cve', 'N/A')
        severity = fix.get('severity', 'UNKNOWN')
        current_version = fix.get('version', 'unknown')
        fixed_version = fix.get('fixed_in', ['unknown'])[0]
        advisory = fix.get('advisory', 'No advisory available.')

        body = f"""## 🔒 Security Update

**CVE**: {cve}
**Severity**: {severity}
**Package**: `{package}`
**Current Version**: {current_version}
**Fixed Version**: {fixed_version}

### Advisory

{advisory}

### Changes

- Updated `{package}` from `{current_version}` to `{fixed_version}`

### Testing

This PR will be automatically merged after CI passes if marked as safe.

- [ ] All CI checks pass
- [ ] No breaking changes detected
- [ ] Security scan clean

### Auto-Merge Status

{'✅ **Safe to auto-merge** - This is a patch/security update with high confidence.' if fix.get('auto_merge_safe') else '⚠️  **Manual review required** - Please review before merging.'}

---

🤖 This PR was automatically created by [security-central](https://github.com/cboyd0319/security-central).

Fix confidence: {fix.get('fix_confidence', 0)}/10
"""
        return body


def main():
    parser = argparse.ArgumentParser(description='Create security patch PRs')
    parser.add_argument('triage_file', help='Triage JSON file')
    parser.add_argument('--auto-merge-safe-only', action='store_true',
                        help='Only create PRs for auto-merge safe fixes')
    args = parser.parse_args()

    gh_token = os.environ.get('GH_TOKEN')
    if not gh_token:
        print("ERROR: GH_TOKEN environment variable not set")
        exit(1)

    patcher = AutoPatcher(gh_token)
    patcher.create_prs(args.triage_file, args.auto_merge_safe_only)


if __name__ == '__main__':
    main()
