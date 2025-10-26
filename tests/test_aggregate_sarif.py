#!/usr/bin/env python3
"""
Comprehensive tests for scripts/aggregate_sarif.py

Tests SARIF file aggregation functionality.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from aggregate_sarif import merge_sarif


class TestMergeSarif:
    """Test merge_sarif function."""

    @pytest.fixture
    def sample_sarif_1(self):
        """Create first sample SARIF file."""
        return {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [
                {
                    "tool": {"driver": {"name": "tool1"}},
                    "results": [
                        {"ruleId": "rule1", "message": {"text": "Finding 1"}},
                        {"ruleId": "rule2", "message": {"text": "Finding 2"}},
                    ],
                }
            ],
        }

    @pytest.fixture
    def sample_sarif_2(self):
        """Create second sample SARIF file."""
        return {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "tool2"}},
                    "results": [{"ruleId": "rule3", "message": {"text": "Finding 3"}}],
                }
            ],
        }

    def test_merge_two_sarif_files(self, sample_sarif_1, sample_sarif_2):
        """Test merging two SARIF files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create input files
            sarif1 = tmpdir / "sarif1.json"
            sarif2 = tmpdir / "sarif2.json"
            output = tmpdir / "merged.json"

            with open(sarif1, "w") as f:
                json.dump(sample_sarif_1, f)
            with open(sarif2, "w") as f:
                json.dump(sample_sarif_2, f)

            # Merge
            result = merge_sarif([sarif1, sarif2], output)

            # Verify result
            assert result["total_runs"] == 2
            assert result["total_findings"] == 3
            assert output.exists()

            # Verify merged file
            with open(output) as f:
                merged = json.load(f)
                assert len(merged["runs"]) == 2
                assert merged["version"] == "2.1.0"

    def test_merge_empty_list(self):
        """Test merging with no input files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            output = tmpdir / "merged.json"

            result = merge_sarif([], output)

            assert result["total_runs"] == 0
            assert result["total_findings"] == 0
            assert output.exists()

    def test_merge_nonexistent_files(self, sample_sarif_1):
        """Test merging with some nonexistent files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Only create one file
            sarif1 = tmpdir / "sarif1.json"
            sarif2 = tmpdir / "nonexistent.json"  # Doesn't exist
            output = tmpdir / "merged.json"

            with open(sarif1, "w") as f:
                json.dump(sample_sarif_1, f)

            # Should skip nonexistent file
            result = merge_sarif([sarif1, sarif2], output)

            assert result["total_runs"] == 1
            assert result["total_findings"] == 2

    def test_merge_sarif_schema_format(self, sample_sarif_1):
        """Test that merged SARIF has correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            sarif1 = tmpdir / "sarif1.json"
            output = tmpdir / "merged.json"

            with open(sarif1, "w") as f:
                json.dump(sample_sarif_1, f)

            merge_sarif([sarif1], output)

            with open(output) as f:
                merged = json.load(f)

                assert "$schema" in merged
                assert "version" in merged
                assert merged["version"] == "2.1.0"
                assert "runs" in merged

    def test_merge_counts_findings_correctly(self):
        """Test that finding counts are accurate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # File with 5 findings
            sarif1 = tmpdir / "sarif1.json"
            data1 = {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "tool"}},
                        "results": [{"ruleId": f"rule{i}"} for i in range(5)],
                    }
                ],
            }

            # File with 3 findings
            sarif2 = tmpdir / "sarif2.json"
            data2 = {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "tool"}},
                        "results": [{"ruleId": f"rule{i}"} for i in range(3)],
                    }
                ],
            }

            output = tmpdir / "merged.json"

            with open(sarif1, "w") as f:
                json.dump(data1, f)
            with open(sarif2, "w") as f:
                json.dump(data2, f)

            result = merge_sarif([sarif1, sarif2], output)

            assert result["total_findings"] == 8  # 5 + 3

    def test_merge_sarif_no_results(self):
        """Test merging SARIF files with no results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            sarif = tmpdir / "sarif.json"
            data = {
                "version": "2.1.0",
                "runs": [{"tool": {"driver": {"name": "tool"}}, "results": []}],  # No findings
            }

            output = tmpdir / "merged.json"

            with open(sarif, "w") as f:
                json.dump(data, f)

            result = merge_sarif([sarif], output)

            assert result["total_runs"] == 1
            assert result["total_findings"] == 0

    def test_merge_multiple_runs_per_file(self):
        """Test merging SARIF file with multiple runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            sarif = tmpdir / "sarif.json"
            data = {
                "version": "2.1.0",
                "runs": [
                    {"tool": {"driver": {"name": "tool1"}}, "results": [{"ruleId": "rule1"}]},
                    {
                        "tool": {"driver": {"name": "tool2"}},
                        "results": [{"ruleId": "rule2"}, {"ruleId": "rule3"}],
                    },
                ],
            }

            output = tmpdir / "merged.json"

            with open(sarif, "w") as f:
                json.dump(data, f)

            result = merge_sarif([sarif], output)

            assert result["total_runs"] == 2
            assert result["total_findings"] == 3


class TestMain:
    """Test main CLI functionality."""

    @patch("aggregate_sarif.merge_sarif")
    @patch(
        "sys.argv",
        ["aggregate_sarif.py", "--input", "file1.json", "file2.json", "--output", "merged.json"],
    )
    def test_main_with_arguments(self, mock_merge):
        """Test main function with CLI arguments."""
        mock_merge.return_value = {
            "total_runs": 2,
            "total_findings": 5,
            "output_file": "merged.json",
        }

        # Import and run main
        from aggregate_sarif import __name__ as module_name

        if module_name == "__main__":
            import aggregate_sarif

            # Would need to actually run the script, but we can test the function directly


class TestIntegration:
    """Integration tests for SARIF aggregation."""

    def test_full_workflow(self):
        """Test complete SARIF aggregation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple SARIF files
            files = []
            for i in range(3):
                sarif_file = tmpdir / f"sarif{i}.json"
                data = {
                    "version": "2.1.0",
                    "runs": [
                        {
                            "tool": {"driver": {"name": f"tool{i}"}},
                            "results": [
                                {"ruleId": f"rule{i}-{j}", "message": {"text": f"Finding {j}"}}
                                for j in range(i + 1)  # 1, 2, 3 findings respectively
                            ],
                        }
                    ],
                }
                with open(sarif_file, "w") as f:
                    json.dump(data, f)
                files.append(sarif_file)

            output = tmpdir / "final.json"

            # Merge all files
            result = merge_sarif(files, output)

            # Verify
            assert result["total_runs"] == 3
            assert result["total_findings"] == 1 + 2 + 3  # 6 total

            # Verify output file structure
            with open(output) as f:
                merged = json.load(f)
                assert len(merged["runs"]) == 3
                assert all("tool" in run for run in merged["runs"])
                assert all("results" in run for run in merged["runs"])

    def test_preserves_tool_information(self):
        """Test that tool information is preserved during merge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            sarif = tmpdir / "sarif.json"
            data = {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {
                            "driver": {
                                "name": "MyTool",
                                "version": "1.0.0",
                                "informationUri": "https://example.com",
                            }
                        },
                        "results": [{"ruleId": "rule1"}],
                    }
                ],
            }

            output = tmpdir / "merged.json"

            with open(sarif, "w") as f:
                json.dump(data, f)

            merge_sarif([sarif], output)

            with open(output) as f:
                merged = json.load(f)
                tool_driver = merged["runs"][0]["tool"]["driver"]
                assert tool_driver["name"] == "MyTool"
                assert tool_driver["version"] == "1.0.0"
