#!/usr/bin/env python3
"""
Automatically replace magic numbers with named constants.
Uses AST parsing to find numeric literals and suggest appropriate constant names.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict


class MagicNumberFinder(ast.NodeVisitor):
    """Find magic numbers in Python code."""

    # Numbers to ignore (common, self-documenting, or unavoidable)
    IGNORE_NUMBERS = {0, 1, -1, 2, 100, 1000}

    # Context-based constant name suggestions
    CONSTANT_SUGGESTIONS = {
        # HTTP status codes
        200: "HTTP_OK",
        201: "HTTP_CREATED",
        204: "HTTP_NO_CONTENT",
        400: "HTTP_BAD_REQUEST",
        401: "HTTP_UNAUTHORIZED",
        403: "HTTP_FORBIDDEN",
        404: "HTTP_NOT_FOUND",
        500: "HTTP_INTERNAL_ERROR",
        502: "HTTP_BAD_GATEWAY",
        503: "HTTP_SERVICE_UNAVAILABLE",

        # Common timeouts (seconds)
        30: "TIMEOUT_SHORT",
        60: "TIMEOUT_MEDIUM",
        120: "TIMEOUT_LONG",
        300: "TIMEOUT_EXTENDED",
        600: "TIMEOUT_VERY_LONG",

        # Retry/attempt counts
        3: "DEFAULT_RETRY_COUNT",
        5: "MAX_RETRY_ATTEMPTS",
        10: "MAX_ATTEMPTS",

        # Percentages/scores
        80: "HIGH_THRESHOLD",
        90: "EXCELLENT_THRESHOLD",
        70: "GOOD_THRESHOLD",
        50: "MEDIUM_THRESHOLD",

        # Buffer sizes
        1024: "BUFFER_SIZE_KB",
        4096: "BUFFER_SIZE_4KB",
        8192: "BUFFER_SIZE_8KB",

        # Rate limits
        1000: "MAX_REQUESTS_PER_HOUR",
    }

    def __init__(self, filename: str):
        self.filename = filename
        self.magic_numbers: List[Dict] = []
        self.current_function = None
        self.current_class = None

    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Num(self, node):
        """Visit numeric literal nodes (Python 3.7 and earlier)."""
        if hasattr(node, 'n'):
            self._check_number(node.n, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_Constant(self, node):
        """Visit constant nodes (Python 3.8+)."""
        if isinstance(node.value, (int, float)):
            self._check_number(node.value, node.lineno, node.col_offset)
        self.generic_visit(node)

    def _check_number(self, value, lineno, col_offset):
        """Check if a number should be flagged as magic."""
        # Skip ignored numbers
        if value in self.IGNORE_NUMBERS:
            return

        # Skip very small floats (likely coefficients, probabilities)
        if isinstance(value, float) and -1 < value < 1:
            return

        # Suggest constant name
        suggested_name = self._suggest_constant_name(value)

        self.magic_numbers.append({
            'file': self.filename,
            'line': lineno,
            'col': col_offset,
            'value': value,
            'function': self.current_function,
            'class': self.current_class,
            'suggested_name': suggested_name,
        })

    def _suggest_constant_name(self, value):
        """Suggest a constant name based on value and context."""
        # Check predefined suggestions
        if value in self.CONSTANT_SUGGESTIONS:
            return self.CONSTANT_SUGGESTIONS[value]

        # Generate from context
        if self.current_function:
            func_name = self.current_function.upper()
            return f"{func_name}_{int(value)}"

        if self.current_class:
            class_name = self.current_class.upper()
            return f"{class_name}_{int(value)}"

        # Generic fallback
        if isinstance(value, int):
            return f"CONSTANT_{value}"
        else:
            return f"CONSTANT_{str(value).replace('.', '_')}"


def find_magic_numbers_in_file(file_path: Path) -> List[Dict]:
    """Find all magic numbers in a Python file."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
        finder = MagicNumberFinder(str(file_path))
        finder.visit(tree)

        return finder.magic_numbers
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def group_magic_numbers(all_numbers: List[Dict]) -> Dict[float, List[Dict]]:
    """Group magic numbers by value."""
    grouped = defaultdict(list)
    for entry in all_numbers:
        grouped[entry['value']].append(entry)
    return dict(grouped)


def generate_constants_file(grouped_numbers: Dict[float, List[Dict]]) -> str:
    """Generate a constants.py file with all magic numbers."""
    lines = [
        '"""',
        'Centralized constants for security-central.',
        'Auto-generated by replace_magic_numbers.py',
        '"""',
        '',
        '# HTTP Status Codes',
    ]

    # Sort by value for organization
    http_codes = {k: v for k, v in grouped_numbers.items() if 200 <= k <= 599}
    timeouts = {k: v for k, v in grouped_numbers.items() if k in [30, 60, 120, 300, 600]}
    retries = {k: v for k, v in grouped_numbers.items() if k in [3, 5, 10]}
    thresholds = {k: v for k, v in grouped_numbers.items() if k in [50, 70, 80, 90, 100]}
    others = {k: v for k, v in grouped_numbers.items()
              if k not in http_codes and k not in timeouts and k not in retries and k not in thresholds}

    if http_codes:
        for value, occurrences in sorted(http_codes.items()):
            name = occurrences[0]['suggested_name']
            count = len(occurrences)
            lines.append(f"{name} = {int(value)}  # Used in {count} places")

    if timeouts:
        lines.append('')
        lines.append('# Timeout Values (seconds)')
        for value, occurrences in sorted(timeouts.items()):
            name = occurrences[0]['suggested_name']
            count = len(occurrences)
            lines.append(f"{name} = {int(value)}  # Used in {count} places")

    if retries:
        lines.append('')
        lines.append('# Retry Counts')
        for value, occurrences in sorted(retries.items()):
            name = occurrences[0]['suggested_name']
            count = len(occurrences)
            lines.append(f"{name} = {int(value)}  # Used in {count} places")

    if thresholds:
        lines.append('')
        lines.append('# Thresholds and Percentages')
        for value, occurrences in sorted(thresholds.items()):
            name = occurrences[0]['suggested_name']
            count = len(occurrences)
            lines.append(f"{name} = {int(value)}  # Used in {count} places")

    if others:
        lines.append('')
        lines.append('# Other Constants')
        for value, occurrences in sorted(others.items()):
            name = occurrences[0]['suggested_name']
            count = len(occurrences)
            if isinstance(value, float):
                lines.append(f"{name} = {value}  # Used in {count} places")
            else:
                lines.append(f"{name} = {int(value)}  # Used in {count} places")

    lines.append('')
    return '\n'.join(lines)


def generate_report(grouped_numbers: Dict[float, List[Dict]]) -> str:
    """Generate a report of magic numbers found."""
    lines = [
        '# Magic Numbers Report',
        '',
        f'Total unique magic numbers found: {len(grouped_numbers)}',
        f'Total occurrences: {sum(len(v) for v in grouped_numbers.values())}',
        '',
        '## Top Magic Numbers by Frequency',
        '',
    ]

    # Sort by frequency
    sorted_numbers = sorted(grouped_numbers.items(), key=lambda x: len(x[1]), reverse=True)

    for value, occurrences in sorted_numbers[:20]:
        count = len(occurrences)
        name = occurrences[0]['suggested_name']
        files = set(occ['file'] for occ in occurrences)
        lines.append(f'- **{value}** → `{name}` ({count} occurrences in {len(files)} files)')

    lines.append('')
    lines.append('## Files with Most Magic Numbers')
    lines.append('')

    # Count by file
    file_counts = defaultdict(int)
    for occurrences in grouped_numbers.values():
        for occ in occurrences:
            file_counts[occ['file']] += 1

    sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
    for file_path, count in sorted_files[:15]:
        lines.append(f'- {Path(file_path).name}: {count} magic numbers')

    lines.append('')
    return '\n'.join(lines)


def main():
    """Main entry point."""
    # Get project root (parent of tools/)
    project_root = Path(__file__).parent.parent.resolve()
    scripts_dir = project_root / 'scripts'
    docs_dir = project_root / 'docs'

    print("Scanning for magic numbers...")
    all_numbers = []

    for py_file in scripts_dir.rglob('*.py'):
        numbers = find_magic_numbers_in_file(py_file)
        all_numbers.extend(numbers)

    print(f"Found {len(all_numbers)} magic number occurrences")

    # Group by value
    grouped = group_magic_numbers(all_numbers)
    print(f"Found {len(grouped)} unique magic numbers")

    # Generate report
    report = generate_report(grouped)
    report_file = docs_dir / 'MAGIC_NUMBERS_REPORT.md'
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report written to {report_file}")

    # Generate constants file (for reference, not auto-applied)
    constants = generate_constants_file(grouped)
    constants_file = docs_dir / 'SUGGESTED_CONSTANTS.py'
    with open(constants_file, 'w') as f:
        f.write(constants)
    print(f"Suggested constants written to {constants_file}")

    print("\nTop 10 magic numbers by frequency:")
    sorted_numbers = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
    for value, occurrences in sorted_numbers[:10]:
        print(f"  {value}: {len(occurrences)} occurrences")


if __name__ == '__main__':
    main()
