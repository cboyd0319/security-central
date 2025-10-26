#!/usr/bin/env python3
"""Aggregate multiple SARIF files into one."""

import argparse
import json
from pathlib import Path
from typing import Any

from utils import safe_open


def merge_sarif(input_files: list[Path], output_file: Path) -> dict[str, Any]:
    """Merge multiple SARIF files into one."""

    base_sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [],
    }

    for sarif_file in input_files:
        if not sarif_file.exists():
            continue

        with safe_open(sarif_file, "r", allowed_base=False) as f:
            data = json.load(f)

        # Add tool name to each run
        for run in data.get("runs", []):
            base_sarif["runs"].append(run)

    # Write aggregated file
    with safe_open(output_file, "w", allowed_base=False) as f:
        json.dump(base_sarif, f, indent=2)

    # Count findings
    total_findings = sum(len(run.get("results", [])) for run in base_sarif["runs"])

    return {
        "total_runs": len(base_sarif["runs"]),
        "total_findings": total_findings,
        "output_file": str(output_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = merge_sarif(args.input, args.output)
    print(f"✓ Merged {result['total_runs']} SARIF files")
    print(f"✓ Total findings: {result['total_findings']}")
    print(f"✓ Output: {result['output_file']}")
