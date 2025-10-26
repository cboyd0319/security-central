#!/usr/bin/env python3
"""
Run PyGuard security scan on security-central Python files.

Requires PyGuard to be available. Install or clone:
- Install: pip install pyguard (if published)
- Clone: git clone https://github.com/cboyd0319/PyGuard ../PyGuard

Or set PYGUARD_PATH environment variable to PyGuard location.
"""
import os
import sys
from pathlib import Path

# Get project root (parent of tools/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Try to find PyGuard
pyguard_path = os.environ.get('PYGUARD_PATH')
if pyguard_path:
    sys.path.insert(0, pyguard_path)
elif (PROJECT_ROOT.parent / 'PyGuard').exists():
    # Check sibling directory
    sys.path.insert(0, str(PROJECT_ROOT.parent / 'PyGuard'))
else:
    print("ERROR: PyGuard not found!")
    print("\nTo use this tool, either:")
    print("  1. Clone PyGuard: git clone https://github.com/cboyd0319/PyGuard ../PyGuard")
    print("  2. Set PYGUARD_PATH: export PYGUARD_PATH=/path/to/PyGuard")
    print("  3. Install PyGuard: pip install pyguard (if available)")
    sys.exit(1)

try:
    from pyguard.cli import PyGuardCLI
except ImportError as e:
    print(f"ERROR: Could not import PyGuard: {e}")
    print("\nMake sure PyGuard is properly installed or cloned.")
    sys.exit(1)

def main():
    """Run PyGuard scan."""
    # Initialize PyGuard CLI in scan-only mode
    cli = PyGuardCLI(allow_unsafe_fixes=False)

    # Get all Python files using relative paths
    scripts_dir = PROJECT_ROOT / 'scripts'
    tests_dir = PROJECT_ROOT / 'tests'

    all_files = []
    all_files.extend(cli.file_ops.find_python_files(scripts_dir, exclude_patterns=[]))
    all_files.extend(cli.file_ops.find_python_files(tests_dir, exclude_patterns=[]))

    print(f"Found {len(all_files)} Python files to scan")
    print("=" * 80)

    # Run in scan-only mode to verify remaining issues
    print("Running PyGuard in SCAN-ONLY mode...")
    print("Verifying fixes and checking for remaining issues...")
    results = cli.run_full_analysis(all_files, create_backup=False, fix=False)

    print("\n" + "=" * 80)
    print("PyGuard Results:")
    print("=" * 80)
    print(f"Total files scanned: {results.get('total_files', 0)}")
    print(f"Files fixed: {results.get('files_fixed', 0)}")
    print(f"Total issues found: {results.get('total_issues', 0)}")
    print(f"Fixes applied: {results.get('fixes_applied', 0)}")
    print(f"Security issues: {results.get('security_issues', 0)}")
    print(f"Quality issues: {results.get('quality_issues', 0)}")
    print("\nBackups created in: ~/.pyguard/backups/")

    # Print detailed issues
    if results.get('all_issues'):
        print("\n" + "=" * 80)
        print(f"Detailed Issues ({len(results['all_issues'])} total):")
        print("=" * 80)
        for i, issue in enumerate(results['all_issues'][:20], 1):  # Show first 20
            print(f"\n{i}. {issue.get('file', 'unknown')}")
            print(f"   Type: {issue.get('type', 'unknown')}")
            print(f"   Severity: {issue.get('severity', 'unknown')}")
            print(f"   Message: {issue.get('message', 'No message')}")

        if len(results['all_issues']) > 20:
            print(f"\n... and {len(results['all_issues']) - 20} more issues")

    return 0

if __name__ == '__main__':
    sys.exit(main())
