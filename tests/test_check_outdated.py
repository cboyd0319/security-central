#!/usr/bin/env python3
"""Tests for scripts/check_outdated.py"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from check_outdated import OutdatedChecker, main


class TestOutdatedChecker:
    """Test OutdatedChecker class."""

    def test_check_basic(self):
        """Test basic outdated check."""
        checker = OutdatedChecker()

        audit_data = {
            "audit_time": "2024-01-01T00:00:00",
            "repositories": [{"name": "repo1", "packages": []}, {"name": "repo2", "packages": []}],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(audit_data, f)
            audit_file = f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = checker.check(audit_file, output_file)

            assert "repositories" in result
            assert "summary" in result
            assert result["summary"]["total_outdated"] == 0
        finally:
            Path(audit_file).unlink()
            Path(output_file).unlink()

    def test_check_creates_output_file(self):
        """Test that check creates output file."""
        checker = OutdatedChecker()

        audit_data = {"audit_time": "2024-01-01", "repositories": []}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(audit_data, f)
            audit_file = f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            checker.check(audit_file, output_file)
            assert Path(output_file).exists()

            with open(output_file) as f:
                result = json.load(f)
                assert "repositories" in result
        finally:
            Path(audit_file).unlink()
            if Path(output_file).exists():
                Path(output_file).unlink()

    def test_check_missing_audit_file(self):
        """Test handling of missing audit file."""
        checker = OutdatedChecker()

        with pytest.raises(FileNotFoundError):
            checker.check("nonexistent.json", "output.json")

    def test_check_summary_structure(self):
        """Test that summary has correct structure."""
        checker = OutdatedChecker()

        audit_data = {"audit_time": "2024-01-01", "repositories": [{"name": "test"}]}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(audit_data, f)
            audit_file = f.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            output_file = f.name

        try:
            result = checker.check(audit_file, output_file)

            assert "major_updates" in result["summary"]
            assert "minor_updates" in result["summary"]
            assert "patch_updates" in result["summary"]
        finally:
            Path(audit_file).unlink()
            Path(output_file).unlink()
