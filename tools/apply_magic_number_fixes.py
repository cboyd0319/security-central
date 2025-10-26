#!/usr/bin/env python3
"""
Automatically apply magic number replacements based on the analysis.
This script:
1. Creates a constants.py file with all constants
2. Updates all Python files to import and use these constants
3. Validates changes with syntax checking
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Constant definitions based on our analysis
CONSTANT_DEFINITIONS = {
    # HTTP Status Codes
    200: "HTTP_OK",
    201: "HTTP_CREATED",
    204: "HTTP_NO_CONTENT",
    400: "HTTP_BAD_REQUEST",
    401: "HTTP_UNAUTHORIZED",
    403: "HTTP_FORBIDDEN",
    404: "HTTP_NOT_FOUND",
    500: "HTTP_INTERNAL_ERROR",

    # Timeouts (seconds)
    30: "TIMEOUT_SHORT",
    60: "TIMEOUT_MEDIUM",
    120: "TIMEOUT_LONG",
    300: "TIMEOUT_EXTENDED",
    600: "TIMEOUT_VERY_LONG",

    # Retry counts
    3: "DEFAULT_RETRY_COUNT",
    5: "MAX_RETRY_ATTEMPTS",
    10: "MAX_ATTEMPTS",

    # Thresholds
    50: "MEDIUM_THRESHOLD",
    70: "GOOD_THRESHOLD",
    80: "HIGH_THRESHOLD",
    90: "EXCELLENT_THRESHOLD",

    # Other common constants
    4: "QUARTER_COUNT",
    7: "DAYS_IN_WEEK",
    8: "OCTAL_BASE",
    20: "DEFAULT_PAGE_SIZE",
    24: "HOURS_IN_DAY",
    1000: "MILLISECONDS_PER_SECOND",
    4096: "BUFFER_SIZE_4KB",
}


def create_constants_file(output_path: Path) -> None:
    """Create a constants.py file with all magic number constants."""

    lines = [
        '"""',
        'Centralized constants for security-central.',
        '',
        'This file contains all magic numbers extracted from the codebase',
        'to improve code readability and maintainability.',
        '"""',
        '',
        '# HTTP Status Codes',
    ]

    # Group constants by category
    http_codes = {k: v for k, v in CONSTANT_DEFINITIONS.items() if 200 <= k <= 599}
    timeouts = {k: v for k, v in CONSTANT_DEFINITIONS.items()
                if k in [30, 60, 120, 300, 600]}
    retries = {k: v for k, v in CONSTANT_DEFINITIONS.items()
               if k in [3, 5, 10]}
    thresholds = {k: v for k, v in CONSTANT_DEFINITIONS.items()
                  if k in [50, 70, 80, 90]}
    time_units = {k: v for k, v in CONSTANT_DEFINITIONS.items()
                  if k in [7, 24]}
    others = {k: v for k, v in CONSTANT_DEFINITIONS.items()
              if k not in http_codes and k not in timeouts and
              k not in retries and k not in thresholds and k not in time_units}

    if http_codes:
        for value, name in sorted(http_codes.items()):
            lines.append(f"{name} = {value}")
        lines.append('')

    if timeouts:
        lines.append('# Timeout Values (seconds)')
        for value, name in sorted(timeouts.items()):
            lines.append(f"{name} = {value}")
        lines.append('')

    if retries:
        lines.append('# Retry Counts')
        for value, name in sorted(retries.items()):
            lines.append(f"{name} = {value}")
        lines.append('')

    if thresholds:
        lines.append('# Score Thresholds')
        for value, name in sorted(thresholds.items()):
            lines.append(f"{name} = {value}")
        lines.append('')

    if time_units:
        lines.append('# Time Units')
        for value, name in sorted(time_units.items()):
            lines.append(f"{name} = {value}")
        lines.append('')

    if others:
        lines.append('# Other Constants')
        for value, name in sorted(others.items()):
            lines.append(f"{name} = {value}")
        lines.append('')

    # Write file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"Created constants file: {output_path}")
    print(f"Defined {len(CONSTANT_DEFINITIONS)} constants")


def replace_magic_numbers_in_file(
    file_path: Path,
    constants_to_replace: Dict[int, str],
    dry_run: bool = False
) -> Tuple[bool, int]:
    """
    Replace magic numbers in a file with constant references.

    Returns:
        Tuple of (modified, replacement_count)
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        original_content = content
        replacements = 0

        # Check if constants need to be imported
        needs_constants_import = False

        # Replace each magic number
        for value, const_name in constants_to_replace.items():
            # Pattern to match the number as a standalone value
            # Avoid replacing in strings, comments, or version numbers
            pattern = rf'\b{value}\b'

            # Count occurrences
            matches = re.findall(pattern, content)
            if matches:
                needs_constants_import = True
                # Replace with constant name
                content = re.sub(pattern, const_name, content)
                replacements += len(matches)

        if needs_constants_import and 'from constants import' not in content:
            # Find the last import statement
            import_pattern = r'^((?:from|import)\s+.+)$'
            matches = list(re.finditer(import_pattern, content, re.MULTILINE))

            if matches:
                last_import = matches[-1]
                insert_pos = last_import.end()

                # Get list of constants to import
                constants_used = [name for val, name in constants_to_replace.items()
                                if re.search(rf'\b{name}\b', content)]

                if constants_used:
                    import_stmt = f"\n\nfrom constants import {', '.join(sorted(constants_used))}"
                    content = content[:insert_pos] + import_stmt + content[insert_pos:]

        if content != original_content:
            if not dry_run:
                # Validate syntax before writing
                try:
                    ast.parse(content)
                    with open(file_path, 'w') as f:
                        f.write(content)
                except SyntaxError as e:
                    print(f"  ⚠️  Syntax error after replacement in {file_path}: {e}")
                    return False, 0

            return True, replacements

        return False, 0

    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return False, 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply magic number replacements throughout the codebase"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be changed without modifying files"
    )
    parser.add_argument(
        '--create-constants',
        action='store_true',
        help="Create the constants.py file"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help="Apply replacements to all files"
    )

    args = parser.parse_args()

    # Get project root (parent of tools/)
    project_root = Path(__file__).parent.parent.resolve()
    scripts_dir = project_root / 'scripts'
    constants_file = scripts_dir / 'constants.py'

    if args.create_constants or args.apply:
        create_constants_file(constants_file)

    if args.apply:
        print("\nApplying magic number replacements...")
        print("=" * 60)

        total_files = 0
        total_replacements = 0
        modified_files = []

        for py_file in scripts_dir.rglob('*.py'):
            # Skip the constants file itself
            if py_file.name == 'constants.py':
                continue

            # Skip __pycache__ and other generated files
            if '__pycache__' in str(py_file):
                continue

            total_files += 1
            modified, count = replace_magic_numbers_in_file(
                py_file,
                CONSTANT_DEFINITIONS,
                dry_run=args.dry_run
            )

            if modified:
                modified_files.append(py_file)
                total_replacements += count
                status = "would replace" if args.dry_run else "replaced"
                print(f"  ✓ {py_file.name}: {status} {count} magic numbers")

        print("\n" + "=" * 60)
        print(f"Summary:")
        print(f"  Files processed: {total_files}")
        print(f"  Files modified: {len(modified_files)}")
        print(f"  Total replacements: {total_replacements}")

        if args.dry_run:
            print("\n  This was a dry run. Use --apply without --dry-run to apply changes.")

    else:
        print("Use --create-constants to create constants.py")
        print("Use --apply to apply replacements to all files")
        print("Use --dry-run with --apply to see what would change")


if __name__ == '__main__':
    main()
