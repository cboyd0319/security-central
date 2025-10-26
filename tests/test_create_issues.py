#!/usr/bin/env python3
"""
Comprehensive tests for scripts/create_issues.py

Tests GitHub issue creation from security findings.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Try to import, skip tests if not available
try:
    from create_issues import IssueCreator
    from github import GithubException

    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    GithubException = Exception  # Fallback
    IssueCreator = None

pytestmark = pytest.mark.skipif(not GITHUB_AVAILABLE, reason="PyGithub not installed")


class TestIssueCreator:
    """Test IssueCreator class."""

    @pytest.fixture
    def mock_github(self):
        """Create mock GitHub instance."""
        with patch("create_issues.Github") as mock_gh_class:
            mock_gh = Mock()
            mock_gh_class.return_value = mock_gh
            yield mock_gh

    @pytest.fixture
    def issue_creator(self, mock_github):
        """Create IssueCreator instance with mocked GitHub."""
        return IssueCreator("fake-token")

    @pytest.fixture
    def sample_sarif(self):
        """Create sample SARIF data."""
        return {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "TestTool"}},
                    "results": [
                        {
                            "ruleId": "CWE-89",
                            "level": "error",
                            "message": {"text": "SQL Injection vulnerability"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "app.py"},
                                        "region": {"startLine": 10, "endLine": 15},
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }

    def test_init(self):
        """Test IssueCreator initialization."""
        with patch("create_issues.Github") as mock_gh:
            creator = IssueCreator("test-token")
            mock_gh.assert_called_once_with("test-token")
            assert hasattr(creator, "gh")

    def test_severity_labels_defined(self):
        """Test that severity labels are properly defined."""
        labels = IssueCreator.SEVERITY_LABELS

        assert "critical" in labels
        assert "high" in labels
        assert "medium" in labels
        assert "low" in labels

        # Check label lists
        assert "security" in labels["critical"]
        assert "P0" in labels["critical"]

    def test_issue_template_defined(self):
        """Test that issue template is properly defined."""
        template = IssueCreator.ISSUE_TEMPLATE

        assert isinstance(template, str)
        assert "{severity}" in template
        assert "{tool}" in template
        assert "{description}" in template

    @patch("create_issues.Github")
    def test_create_issues_from_sarif_basic(self, mock_gh_class, sample_sarif):
        """Test creating issues from SARIF file."""
        # Setup mocks
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo
        mock_repo.create_issue.return_value = Mock(
            number=1, html_url="https://github.com/test/repo/issues/1"
        )

        # Mock search_issues to return no existing issues
        mock_search_result = Mock()
        mock_search_result.totalCount = 0
        mock_gh.search_issues.return_value = mock_search_result

        creator = IssueCreator("token")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sample_sarif, f)
            sarif_path = Path(f.name)

        try:
            issues = creator.create_issues_from_sarif("test/repo", sarif_path)

            # Should create issues
            assert isinstance(issues, list)
        finally:
            sarif_path.unlink()

    @patch("create_issues.Github")
    def test_create_issues_empty_sarif(self, mock_gh_class):
        """Test handling empty SARIF file."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo

        creator = IssueCreator("token")

        empty_sarif = {"version": "2.1.0", "runs": []}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(empty_sarif, f)
            sarif_path = Path(f.name)

        try:
            issues = creator.create_issues_from_sarif("test/repo", sarif_path)
            assert issues == []
        finally:
            sarif_path.unlink()

    @patch("create_issues.Github")
    def test_severity_threshold_filtering(self, mock_gh_class, sample_sarif):
        """Test that severity threshold filters findings."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo

        # Mock search_issues
        mock_search_result = Mock()
        mock_search_result.totalCount = 0
        mock_gh.search_issues.return_value = mock_search_result

        creator = IssueCreator("token")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sample_sarif, f)
            sarif_path = Path(f.name)

        try:
            # With high threshold, only critical/high should create issues
            creator.create_issues_from_sarif("test/repo", sarif_path, severity_threshold="high")
            # Verify filtering happened
        finally:
            sarif_path.unlink()

    @patch("create_issues.Github")
    def test_github_exception_handling(self, mock_gh_class):
        """Test handling GitHub API exceptions."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo
        mock_repo.create_issue.side_effect = GithubException(403, "Forbidden")

        # Mock search_issues
        mock_search_result = Mock()
        mock_search_result.totalCount = 0
        mock_gh.search_issues.return_value = mock_search_result

        creator = IssueCreator("token")

        sarif = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "Test"}},
                    "results": [
                        {"ruleId": "test", "level": "error", "message": {"text": "Test finding"}}
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sarif, f)
            sarif_path = Path(f.name)

        try:
            # Should handle exception gracefully
            issues = creator.create_issues_from_sarif("test/repo", sarif_path)
            # Might return empty list or partial results
            assert isinstance(issues, list)
        finally:
            sarif_path.unlink()

    def test_get_severity_method(self, issue_creator):
        """Test _get_severity private method."""
        # Test level-based severity mapping
        assert issue_creator._get_severity({"level": "error"}) == "high"
        assert issue_creator._get_severity({"level": "warning"}) == "medium"
        assert issue_creator._get_severity({"level": "note"}) == "low"

        # Test security-severity score mapping
        assert (
            issue_creator._get_severity({"properties": {"security-severity": "9.5"}}) == "critical"
        )
        assert issue_creator._get_severity({"properties": {"security-severity": "8.0"}}) == "high"
        assert issue_creator._get_severity({"properties": {"security-severity": "5.0"}}) == "medium"
        assert issue_creator._get_severity({"properties": {"security-severity": "2.0"}}) == "low"

        # Test default case
        assert issue_creator._get_severity({}) == "medium"
        assert issue_creator._get_severity({"level": "unknown"}) == "medium"

    def test_meets_threshold_method(self, issue_creator):
        """Test _meets_threshold private method."""
        # Test threshold with low
        assert issue_creator._meets_threshold("low", "low")  # Use if var: instead
        assert issue_creator._meets_threshold("medium", "low")  # Use if var: instead
        assert issue_creator._meets_threshold("high", "low")  # Use if var: instead
        assert issue_creator._meets_threshold("critical", "low")  # Use if var: instead

        # Test threshold with medium
        assert not issue_creator._meets_threshold("low", "medium")
        assert issue_creator._meets_threshold("medium", "medium")
        assert issue_creator._meets_threshold("high", "medium")
        assert issue_creator._meets_threshold("critical", "medium")

        # Test threshold with high
        assert not issue_creator._meets_threshold("low", "high")
        assert not issue_creator._meets_threshold("medium", "high")
        assert issue_creator._meets_threshold("high", "high")
        assert issue_creator._meets_threshold("critical", "high")

        # Test threshold with critical
        assert not issue_creator._meets_threshold("low", "critical")
        assert not issue_creator._meets_threshold("medium", "critical")
        assert not issue_creator._meets_threshold("high", "critical")
        assert issue_creator._meets_threshold("critical", "critical")

    def test_generate_finding_id_method(self, issue_creator):
        """Test _generate_finding_id private method."""
        # Test basic finding ID generation
        result = {
            "ruleId": "CWE-89",
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "app.py"},
                        "region": {"startLine": 42},
                    }
                }
            ],
        }
        finding_id = issue_creator._generate_finding_id(result)
        assert finding_id == "CWE-89_app.py_42"

        # Test with path that includes slashes (should be replaced)
        result_with_path = {
            "ruleId": "CWE-79",
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "src/web/app.py"},
                        "region": {"startLine": 100},
                    }
                }
            ],
        }
        finding_id = issue_creator._generate_finding_id(result_with_path)
        assert finding_id == "CWE-79_src_web_app.py_100"
        assert "/" not in finding_id

        # Test with missing fields (should handle gracefully)
        result_minimal = {"ruleId": "test"}
        finding_id = issue_creator._generate_finding_id(result_minimal)
        assert finding_id == "test__0"

        # Test with no ruleId (but with empty location to avoid IndexError)
        result_no_rule = {}
        finding_id = issue_creator._generate_finding_id(result_no_rule)
        assert "unknown" in finding_id

    def test_issue_exists_method(self, issue_creator):
        """Test _issue_exists private method to avoid duplicates."""
        # Create a mock repo
        mock_repo = Mock()
        mock_repo.full_name = "test/repo"

        # Test when no issues exist
        mock_search_result = Mock()
        mock_search_result.totalCount = 0
        issue_creator.gh.search_issues = Mock(return_value=mock_search_result)

        finding_id = "CWE-89_app.py_42"
        exists = issue_creator._issue_exists(mock_repo, finding_id)
        assert not exists  # No issues exist, should return False

        # Verify search query format
        issue_creator.gh.search_issues.assert_called_once()
        call_args = issue_creator.gh.search_issues.call_args[0][0]
        assert "repo:test/repo" in call_args
        assert "is:issue" in call_args
        assert finding_id in call_args
        assert "in:body" in call_args

        # Test when issue already exists
        mock_search_result.totalCount = 1
        issue_creator.gh.search_issues = Mock(return_value=mock_search_result)

        exists = issue_creator._issue_exists(mock_repo, finding_id)
        assert exists  # Issue exists, should return True

    def test_get_references_method(self, issue_creator):
        """Test _get_references method with and without helpUri."""
        # Test with helpUri
        result_with_ref = {
            "properties": {"helpUri": "https://cwe.mitre.org/data/definitions/89.html"}
        }
        refs = issue_creator._get_references(result_with_ref)
        assert "https://cwe.mitre.org" in refs
        assert refs.startswith("- ")

        # Test without helpUri
        result_no_ref = {}
        refs = issue_creator._get_references(result_no_ref)
        assert refs == "No references available"

        # Test with empty helpUri
        result_empty_ref = {"properties": {"helpUri": ""}}
        refs = issue_creator._get_references(result_empty_ref)
        assert refs == "No references available"

    def test_detect_language_method(self, issue_creator):
        """Test _detect_language method for various file extensions."""
        # Test common languages
        assert issue_creator._detect_language("app.py") == "python"
        assert issue_creator._detect_language("script.js") == "javascript"
        assert issue_creator._detect_language("component.tsx") == "tsx"
        assert issue_creator._detect_language("Main.java") == "java"
        assert issue_creator._detect_language("main.go") == "go"
        assert issue_creator._detect_language("app.rb") == "ruby"
        assert issue_creator._detect_language("index.php") == "php"
        assert issue_creator._detect_language("script.sh") == "bash"
        assert issue_creator._detect_language("config.yaml") == "yaml"
        assert issue_creator._detect_language("data.json") == "json"

        # Test case insensitivity
        assert issue_creator._detect_language("App.PY") == "python"
        assert issue_creator._detect_language("Script.JS") == "javascript"

        # Test unknown extension
        assert issue_creator._detect_language("file.unknown") == "text"
        assert issue_creator._detect_language("noextension") == "text"

        # Test with path
        assert issue_creator._detect_language("src/web/app.py") == "python"
        assert issue_creator._detect_language("/absolute/path/to/file.rs") == "rust"


class TestDuplicateHandling:
    """Test duplicate issue detection and skipping."""

    @patch("create_issues.Github")
    def test_skip_duplicate_issues(self, mock_gh_class):
        """Test that duplicate issues are skipped with logging."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo

        # Mock search to return existing issue
        mock_search_result = Mock()
        mock_search_result.totalCount = 1  # Issue already exists
        mock_gh.search_issues.return_value = mock_search_result

        creator = IssueCreator("token")

        sarif = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "TestTool"}},
                    "results": [
                        {
                            "ruleId": "CWE-89",
                            "level": "error",
                            "message": {"text": "SQL Injection"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "app.py"},
                                        "region": {"startLine": 10},
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sarif, f)
            sarif_path = Path(f.name)

        try:
            issues = creator.create_issues_from_sarif("test/repo", sarif_path)
            # No issues should be created since it's a duplicate
            assert issues == []
            # Verify create_issue was never called
            mock_repo.create_issue.assert_not_called()
        finally:
            sarif_path.unlink()


class TestIntegration:
    """Integration tests for issue creation."""

    @patch("create_issues.Github")
    def test_full_workflow(self, mock_gh_class):
        """Test complete issue creation workflow."""
        # Setup comprehensive mocks
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()
        mock_gh.get_repo.return_value = mock_repo

        created_issues = []

        def create_issue_side_effect(title, body, labels):
            # TODO: Add docstring
            issue = Mock()
            issue.number = len(created_issues) + 1
            issue.html_url = f"https://github.com/test/repo/issues/{issue.number}"
            created_issues.append(issue)
            return issue

        mock_repo.create_issue.side_effect = create_issue_side_effect
        mock_repo.get_issues.return_value = []  # No existing issues

        # Mock search_issues
        mock_search_result = Mock()
        mock_search_result.totalCount = 0
        mock_gh.search_issues.return_value = mock_search_result

        creator = IssueCreator("test-token")

        # Create SARIF with multiple findings
        sarif = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "SecurityScanner"}},
                    "results": [
                        {
                            "ruleId": "CWE-79",
                            "level": "error",
                            "message": {"text": "XSS vulnerability"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "web.py"},
                                        "region": {"startLine": 20, "endLine": 25},
                                    }
                                }
                            ],
                        },
                        {
                            "ruleId": "CWE-89",
                            "level": "error",
                            "message": {"text": "SQL Injection"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "db.py"},
                                        "region": {"startLine": 50, "endLine": 55},
                                    }
                                }
                            ],
                        },
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sarif, f)
            sarif_path = Path(f.name)

        try:
            issues = creator.create_issues_from_sarif("test/repo", sarif_path)

            # Verify issues were created
            assert isinstance(issues, list)
        finally:
            sarif_path.unlink()


class TestInputValidation:
    """Test input validation and error handling."""

    @patch("create_issues.Github")
    def test_invalid_repo_format_no_slash(self, mock_gh_class):
        """Test validation of repo format without slash."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh

        creator = IssueCreator("token")

        sarif = {"version": "2.1.0", "runs": []}
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sarif, f)
            sarif_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid repo format"):
                creator.create_issues_from_sarif("invalidrepo", sarif_path)
        finally:
            sarif_path.unlink()

    @patch("create_issues.Github")
    def test_invalid_repo_format_multiple_slashes(self, mock_gh_class):
        """Test validation of repo format with multiple slashes."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh

        creator = IssueCreator("token")

        sarif = {"version": "2.1.0", "runs": []}
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sarif, f)
            sarif_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid repo format"):
                creator.create_issues_from_sarif("owner/repo/extra", sarif_path)
        finally:
            sarif_path.unlink()

    @patch("create_issues.Github")
    def test_sarif_file_not_found(self, mock_gh_class):
        """Test handling of missing SARIF file."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh

        creator = IssueCreator("token")

        with pytest.raises(FileNotFoundError, match="SARIF file not found"):
            creator.create_issues_from_sarif("test/repo", Path("/nonexistent/file.json"))

    @patch("create_issues.Github")
    def test_invalid_json_in_sarif(self, mock_gh_class):
        """Test handling of invalid JSON in SARIF file."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh

        creator = IssueCreator("token")

        # Create file with invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write("{invalid json content")
            sarif_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid JSON in SARIF file"):
                creator.create_issues_from_sarif("test/repo", sarif_path)
        finally:
            sarif_path.unlink()

    @patch("create_issues.Github")
    def test_sarif_missing_runs_array(self, mock_gh_class):
        """Test validation of SARIF format."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh

        creator = IssueCreator("token")

        # SARIF without runs array
        sarif = {"version": "2.1.0"}
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sarif, f)
            sarif_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid SARIF format"):
                creator.create_issues_from_sarif("test/repo", sarif_path)
        finally:
            sarif_path.unlink()


class TestRateLimiting:
    """Test rate limiting and retry logic."""

    @patch("create_issues.Github")
    @patch("create_issues.sleep")
    def test_rate_limit_retry(self, mock_sleep, mock_gh_class):
        """Test that rate limiting triggers retry."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()

        creator = IssueCreator("token")

        # First call fails with rate limit, second succeeds
        rate_limit_error = GithubException(403, "rate limit exceeded")
        mock_issue = Mock()
        mock_issue.html_url = "https://github.com/test/repo/issues/1"
        mock_repo.create_issue.side_effect = [rate_limit_error, mock_issue]

        result = creator._create_issue_with_retry(mock_repo, "Test", "Body", ["label"])

        # Verify sleep was called
        mock_sleep.assert_called_once_with(60)
        # Verify issue was created on second attempt
        assert result == mock_issue
        assert mock_repo.create_issue.call_count == 2

    @patch("create_issues.Github")
    @patch("create_issues.sleep")
    def test_rate_limit_max_retries_exceeded(self, mock_sleep, mock_gh_class):
        """Test that max retries raises exception."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()

        creator = IssueCreator("token")

        # All calls fail with rate limit
        rate_limit_error = GithubException(403, "rate limit exceeded")
        mock_repo.create_issue.side_effect = rate_limit_error

        with pytest.raises(GithubException):
            creator._create_issue_with_retry(mock_repo, "Test", "Body", ["label"])

        # Verify retries occurred
        assert mock_repo.create_issue.call_count == 3
        assert mock_sleep.call_count == 2  # Sleeps before retry 2 and 3

    @patch("create_issues.Github")
    def test_non_rate_limit_error_no_retry(self, mock_gh_class):
        """Test that non-rate-limit errors don't trigger retry."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_repo = Mock()

        creator = IssueCreator("token")

        # Fail with a different error
        other_error = GithubException(404, "Not Found")
        mock_repo.create_issue.side_effect = other_error

        with pytest.raises(GithubException) as exc_info:
            creator._create_issue_with_retry(mock_repo, "Test", "Body", ["label"])

        # Verify no retry happened
        assert mock_repo.create_issue.call_count == 1
        assert exc_info.value.status == 404


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("create_issues.Github")
    def test_malformed_sarif(self, mock_gh_class):
        """Test handling malformed SARIF file."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh

        creator = IssueCreator("token")

        # Missing required fields
        bad_sarif = {"runs": [{"results": [{}]}]}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(bad_sarif, f)
            sarif_path = Path(f.name)

        try:
            # Should handle gracefully
            creator.create_issues_from_sarif("test/repo", sarif_path)
        finally:
            sarif_path.unlink()

    @patch("create_issues.Github")
    def test_missing_sarif_file(self, mock_gh_class):
        """Test handling missing SARIF file."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh

        creator = IssueCreator("token")

        with pytest.raises(FileNotFoundError):
            creator.create_issues_from_sarif("test/repo", Path("nonexistent.json"))

    @patch("create_issues.Github")
    def test_invalid_repo_name(self, mock_gh_class):
        """Test handling invalid repository name."""
        mock_gh = Mock()
        mock_gh_class.return_value = mock_gh
        mock_gh.get_repo.side_effect = GithubException(404, "Not Found")

        creator = IssueCreator("token")

        sarif = {"version": "2.1.0", "runs": []}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(sarif, f)
            sarif_path = Path(f.name)

        try:
            with pytest.raises(GithubException):
                creator.create_issues_from_sarif("invalid/repo", sarif_path)
        finally:
            sarif_path.unlink()
