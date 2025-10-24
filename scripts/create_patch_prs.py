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

    def _cleanup_branch(self, branch_name: str):
        """Clean up by switching to main and deleting the branch."""
        try:
            subprocess.run(
                ['git', 'checkout', 'main'],
                check=True,
                capture_output=True,
                timeout=30
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"    ⚠️  Warning: Failed to checkout main: {e}")

        try:
            subprocess.run(
                ['git', 'branch', '-D', branch_name],
                check=True,
                capture_output=True,
                timeout=30
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"    ⚠️  Warning: Failed to delete branch {branch_name}: {e}")

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
        try:
            existing_branches_result = subprocess.run(
                ['git', 'branch', '-r'],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            existing_branches = existing_branches_result.stdout
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Failed to check existing branches: {e.stderr}")
            os.chdir('../..')
            return
        except subprocess.TimeoutExpired:
            print(f"    ❌ Timeout checking branches")
            os.chdir('../..')
            return

        if branch_name in existing_branches:
            print(f"    ⏭️  PR already exists for this fix")
            os.chdir('../..')
            return

        # Create branch
        try:
            subprocess.run(
                ['git', 'checkout', '-b', branch_name],
                check=True,
                capture_output=True,
                timeout=30
            )
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Failed to create branch {branch_name}: {e.stderr.decode() if e.stderr else 'unknown error'}")
            os.chdir('../..')
            return

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
                self._cleanup_branch(branch_name)
                os.chdir('../..')
                return
        except Exception as e:
            print(f"    ❌ Fix failed: {e}")
            self._cleanup_branch(branch_name)
            os.chdir('../..')
            return

        # Check if changes were made
        try:
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"    ❌ Failed to check git status: {e}")
            self._cleanup_branch(branch_name)
            os.chdir('../..')
            return

        if not status.stdout.strip():
            print(f"    ⏭️  No changes needed")
            self._cleanup_branch(branch_name)
            os.chdir('../..')
            return

        # Commit changes
        commit_msg = self.generate_commit_message(fix)
        try:
            subprocess.run(['git', 'add', '.'], check=True, timeout=30)
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                check=True,
                capture_output=True,
                timeout=30
            )
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Failed to commit changes: {e.stderr.decode() if e.stderr else 'unknown error'}")
            self._cleanup_branch(branch_name)
            os.chdir('../..')
            return
        except subprocess.TimeoutExpired:
            print(f"    ❌ Timeout during commit")
            self._cleanup_branch(branch_name)
            os.chdir('../..')
            return

        # Push branch
        try:
            subprocess.run(
                ['git', 'push', 'origin', branch_name],
                check=True,
                capture_output=True,
                timeout=120  # Longer timeout for network operation
            )
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Failed to push branch: {e.stderr.decode() if e.stderr else 'unknown error'}")
            self._cleanup_branch(branch_name)
            os.chdir('../..')
            return
        except subprocess.TimeoutExpired:
            print(f"    ❌ Timeout pushing to remote")
            self._cleanup_branch(branch_name)
            os.chdir('../..')
            return

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
                try:
                    subprocess.run([
                        'gh', 'pr', 'merge', pr_number,
                        '--auto', '--squash'
                    ], check=True, capture_output=True, timeout=30)
                    print(f"    🤖 Auto-merge enabled (will merge after CI passes)")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    print(f"    ⚠️  Auto-merge failed (requires repo settings): {e}")
        else:
            print(f"    ❌ PR creation failed: {result.stderr}")

        # Return to main branch
        try:
            subprocess.run(
                ['git', 'checkout', 'main'],
                check=True,
                capture_output=True,
                timeout=30
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"    ⚠️  Warning: Failed to return to main branch: {e}")
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
            pattern = f'("{package}.*?")|(\'{package}.*?\')'
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
        try:
            subprocess.run([
                'npm', 'install', f"{package}@{fixed_version}"
            ], check=True, capture_output=True, timeout=300)  # 5 min for npm
        except subprocess.CalledProcessError as e:
            raise ValueError(f"npm install failed: {e.stderr.decode() if e.stderr else 'unknown error'}")
        except subprocess.TimeoutExpired:
            raise ValueError(f"npm install timed out after 5 minutes")

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
        print("⚠️  WARNING: GH_TOKEN environment variable not set")
        print("   PR creation will be skipped. This is expected during initial setup.")
        print("   To enable PR creation, set the GH_TOKEN secret in your repository.")
        return

    patcher = AutoPatcher(gh_token)
    patcher.create_prs(args.triage_file, args.auto_merge_safe_only)


if __name__ == '__main__':
    main()
