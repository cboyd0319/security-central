#!/usr/bin/env python3
"""
Utility functions for security-central.
Common operations used across multiple scripts.
"""

import hashlib
import os
import subprocess
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def deduplicate_findings(findings: List[Dict]) -> Tuple[List[Dict], int]:
    """Deduplicate security findings from multiple scanners.

    Multiple scanners (pip-audit, safety, npm audit, etc.) can find the same
    vulnerability. This function deduplicates based on package, CVE, and repo,
    while preserving the most detailed/reliable information.

    Args:
        findings: List of finding dictionaries with keys like:
            - repo: Repository name
            - package: Package name
            - cve: CVE identifier
            - severity: Severity level
            - tool: Scanner that found it
            - fixed_in: Fixed versions (may vary by scanner)

    Returns:
        Tuple of (deduplicated_findings, duplicate_count)

    Example:
        >>> findings = [
        ...     {'package': 'requests', 'cve': 'CVE-2024-1', 'repo': 'app1', 'tool': 'pip-audit'},
        ...     {'package': 'requests', 'cve': 'CVE-2024-1', 'repo': 'app1', 'tool': 'safety'},
        ... ]
        >>> unique, dupes = deduplicate_findings(findings)
        >>> len(unique)
        1
        >>> dupes
        1
    """
    seen = {}
    duplicates = 0

    # Scanner reliability ranking (higher = more reliable)
    scanner_priority = {
        "pip-audit": 10,
        "npm-audit": 9,
        "osv-scanner": 8,
        "safety": 7,
        "bandit": 6,
        "semgrep": 5,
        "dependency-check": 4,
        "PSScriptAnalyzer": 3,
    }

    for finding in findings:
        # Create unique fingerprint for this vulnerability
        key = _create_finding_fingerprint(finding)

        if key not in seen:
            # First time seeing this vulnerability
            seen[key] = finding
        else:
            # Duplicate found - merge information
            duplicates += 1
            existing = seen[key]

            # Prefer data from more reliable scanner
            current_priority = scanner_priority.get(finding.get("tool", ""), 0)
            existing_priority = scanner_priority.get(existing.get("tool", ""), 0)

            if current_priority > existing_priority:
                # Replace with more reliable source
                existing["tool"] = finding.get("tool")
                existing["fixed_in"] = finding.get("fixed_in", existing.get("fixed_in"))
                existing["advisory"] = finding.get("advisory", existing.get("advisory"))

            # Merge fixed_in versions from both scanners
            existing_fixed = set(existing.get("fixed_in", []) or [])
            new_fixed = set(finding.get("fixed_in", []) or [])
            if existing_fixed or new_fixed:
                existing["fixed_in"] = sorted(list(existing_fixed | new_fixed))

            # Track all scanners that found this
            if "detected_by" not in existing:
                existing["detected_by"] = [existing.get("tool")]
            if finding.get("tool") not in existing["detected_by"]:
                existing["detected_by"].append(finding.get("tool"))

    return list(seen.values()), duplicates


def _create_finding_fingerprint(finding: Dict) -> str:
    """Create unique fingerprint for a finding.

    Fingerprint is based on:
    - Repository name
    - Package name
    - CVE/vulnerability ID
    - File path (for code quality issues)

    Args:
        finding: Finding dictionary

    Returns:
        SHA256 hash as fingerprint
    """
    components = [
        finding.get("repo", ""),
        finding.get("package", finding.get("rule", "")),  # package or rule name
        finding.get("cve", finding.get("id", "")),  # CVE or other ID
        finding.get("file", ""),  # File path for code quality issues
    ]

    # Create stable fingerprint
    fingerprint_str = "|".join(str(c).lower() for c in components)
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()


def rate_limit(calls_per_minute: int = 30):
    """Rate limiting decorator for API calls.

    Prevents hitting GitHub API rate limits or other service limits.

    Args:
        calls_per_minute: Maximum number of calls allowed per minute

    Example:
        @rate_limit(calls_per_minute=30)
        def create_github_issue(repo, title, body):
            # API call here
            pass
    """
    min_interval = 60.0 / calls_per_minute
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            last_called[0] = time.time()
            return func(*args, **kwargs)

        return wrapper

    return decorator


def safe_subprocess_run(
    cmd: List[str],
    timeout: int = 60,
    check: bool = True,
    capture_output: bool = True,
    cwd: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Safely run subprocess with proper error handling.

    Wrapper around subprocess.run with:
    - Default timeout
    - Proper error handling
    - Consistent error messages

    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds (default 60)
        check: Raise CalledProcessError on non-zero exit (default True)
        capture_output: Capture stdout/stderr (default True)
        cwd: Working directory (optional)

    Returns:
        CompletedProcess instance

    Raises:
        subprocess.CalledProcessError: If command fails and check=True
        subprocess.TimeoutExpired: If command exceeds timeout

    Example:
        >>> result = safe_subprocess_run(['git', 'status'], timeout=30)
        >>> print(result.stdout.decode())
    """
    try:
        return subprocess.run(
            cmd, timeout=timeout, check=check, capture_output=capture_output, cwd=cwd, text=True
        )
    except subprocess.CalledProcessError as e:
        # Add context to error message
        cmd_str = " ".join(cmd)
        error_msg = e.stderr if e.stderr else "No error output"
        raise subprocess.CalledProcessError(
            e.returncode, cmd, output=e.stdout, stderr=f"Command '{cmd_str}' failed: {error_msg}"
        )
    except subprocess.TimeoutExpired as e:
        cmd_str = " ".join(cmd)
        raise subprocess.TimeoutExpired(
            cmd, timeout, output=e.stdout, stderr=f"Command '{cmd_str}' timed out after {timeout}s"
        )


def merge_findings_metadata(findings: List[Dict]) -> Dict:
    """Generate metadata about findings for reporting.

    Args:
        findings: List of findings

    Returns:
        Dictionary with metadata:
        - total_count
        - by_severity
        - by_type
        - by_repo
        - scanners_used
        - most_common_cves
    """
    from collections import Counter

    metadata = {
        "total_count": len(findings),
        "by_severity": dict(Counter(f.get("severity", "UNKNOWN") for f in findings)),
        "by_type": dict(Counter(f.get("type", "unknown") for f in findings)),
        "by_repo": dict(Counter(f.get("repo", "unknown") for f in findings)),
        "scanners_used": list(set(f.get("tool", "unknown") for f in findings)),
    }

    # Most common CVEs
    cves = [f.get("cve") for f in findings if f.get("cve") and f.get("cve") != "N/A"]
    if cves:
        cve_counts = Counter(cves)
        metadata["most_common_cves"] = cve_counts.most_common(10)
    else:
        metadata["most_common_cves"] = []

    return metadata


def create_session_with_retries(
    total_retries: int = 5,
    backoff_factor: float = 1.0,
    status_forcelist: Optional[List[int]] = None,
) -> requests.Session:
    """Create requests session with automatic retry logic.

    Handles transient network failures, rate limiting, and server errors.

    Args:
        total_retries: Maximum number of retry attempts (default 5)
        backoff_factor: Exponential backoff multiplier (default 1.0)
            Sleep time = {backoff factor} * (2 ** {retry count - 1})
            e.g., 1.0 → sleeps: 0s, 1s, 2s, 4s, 8s
        status_forcelist: HTTP status codes to retry on
            Default: [429, 500, 502, 503, 504]

    Returns:
        Configured requests.Session with retry logic

    Example:
        >>> session = create_session_with_retries()
        >>> response = session.get('https://api.github.com/rate_limit')
        >>> response.raise_for_status()
    """
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    session = requests.Session()

    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple = (Exception,),
) -> Callable:
    """Decorator to retry function on specific exceptions.

    Args:
        max_attempts: Maximum number of attempts (default 3)
        delay: Initial delay between retries in seconds (default 1.0)
        backoff: Multiplier for delay on each retry (default 2.0)
        exceptions: Tuple of exception types to catch (default all)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_exception(max_attempts=3, exceptions=(requests.RequestException,))
        def fetch_data(url):
            return requests.get(url).json()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        # Last attempt failed
                        raise

                    print(f"  ⚠️  Attempt {attempt}/{max_attempts} failed: {e}")
                    print(f"     Retrying in {current_delay:.1f}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff

            # Should never reach here, but just in case
            raise last_exception

        return wrapper

    return decorator


def validate_version_format(version: str) -> bool:
    """Validate if a string is a valid semantic version.

    Args:
        version: Version string to validate

    Returns:
        True if valid semver-ish format, False otherwise

    Example:
        >>> validate_version_format("1.2.3")
        True
        >>> validate_version_format("invalid")
        False
    """
    if not version:
        return False

    parts = version.strip().split(".")
    if len(parts) < 2:  # At least major.minor
        return False

    try:
        # Try to parse first 3 parts as integers
        for i in range(min(3, len(parts))):
            int(parts[i].split("-")[0].split("+")[0])  # Handle pre-release/build
        return True
    except (ValueError, AttributeError):
        return False


# Security Constants
DEFAULT_ALLOWED_BASE_DIR = Path.cwd()
MAX_PATH_LENGTH = 4096


def safe_path_resolve(
    filepath: Union[str, Path], allowed_base: Optional[Union[str, Path]] = None
) -> Path:
    """
    Safely resolve a file path preventing directory traversal attacks.

    This function validates that the resolved absolute path is within the allowed
    base directory, preventing path traversal attacks like '../../../etc/passwd'.

    Args:
        filepath: Path to validate and resolve
        allowed_base: Base directory that the path must be within.
                     Defaults to current working directory.

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is outside allowed base or contains traversal attempts
        FileNotFoundError: If the resolved path doesn't exist

    Example:
        >>> safe_path_resolve("data/file.json", "/trusted/dir")
        PosixPath('/trusted/dir/data/file.json')
        >>> safe_path_resolve("../../../etc/passwd", "/trusted/dir")
        Traceback (most recent call last):
        ValueError: Path traversal attempt detected
    """
    # Convert to Path object
    filepath = Path(filepath)

    # Resolve to absolute path
    try:
        abs_path = filepath.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Failed to resolve path: {e}")

    # Skip validation if explicitly disabled (allowed_base=False)
    if allowed_base is False:
        return abs_path

    # Use default base if None
    if allowed_base is None:
        allowed_base = DEFAULT_ALLOWED_BASE_DIR

    # Convert and resolve base directory
    allowed_base = Path(allowed_base)
    try:
        abs_base = allowed_base.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Failed to resolve base path: {e}")

    # Check path length
    if len(str(abs_path)) > MAX_PATH_LENGTH:
        raise ValueError(f"Path exceeds maximum length of {MAX_PATH_LENGTH}")

    # Verify the path is within the allowed base
    try:
        abs_path.relative_to(abs_base)
    except ValueError:
        raise ValueError(
            f"Path traversal attempt detected: '{filepath}' resolves to "
            f"'{abs_path}' which is outside allowed base '{abs_base}'"
        )

    return abs_path


def safe_open(
    filepath: Union[str, Path],
    mode: str = "r",
    allowed_base: Optional[Union[str, Path]] = None,
    **kwargs,
):
    """
    Safely open a file with path traversal protection.

    Validates the file path before opening to prevent directory traversal attacks.
    All arguments except 'allowed_base' are passed directly to open().

    Args:
        filepath: Path to file to open
        mode: File mode ('r', 'w', 'rb', etc.)
        allowed_base: Base directory the file must be within
        **kwargs: Additional arguments passed to open()

    Returns:
        File object from open()

    Raises:
        ValueError: If path validation fails
        FileNotFoundError: If file doesn't exist (in read modes)

    Example:
        >>> with safe_open("data/file.json", "r", "/trusted/dir") as f:
        ...     data = f.read()
    """
    validated_path = safe_path_resolve(filepath, allowed_base)

    # For read modes, check file exists
    if "r" in mode and not validated_path.exists():
        raise FileNotFoundError(f"File not found: {validated_path}")

    return open(validated_path, mode, **kwargs)


def safe_read_json(
    filepath: Union[str, Path],
    allowed_base: Optional[Union[str, Path]] = None,
) -> Dict:
    """
    Safely read and parse a JSON file with path traversal protection.

    Args:
        filepath: Path to JSON file
        allowed_base: Base directory the file must be within

    Returns:
        Parsed JSON data as dictionary

    Raises:
        ValueError: If path validation fails or JSON is invalid
        FileNotFoundError: If file doesn't exist

    Example:
        >>> data = safe_read_json("config.json", "/app/config")
    """
    import json

    with safe_open(filepath, "r", allowed_base) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")


def safe_write_json(
    filepath: Union[str, Path],
    data: Dict,
    allowed_base: Optional[Union[str, Path]] = None,
    indent: int = 2,
) -> None:
    """
    Safely write data to a JSON file with path traversal protection.

    Args:
        filepath: Path to JSON file
        data: Data to write (must be JSON serializable)
        allowed_base: Base directory the file must be within
        indent: JSON indentation level

    Raises:
        ValueError: If path validation fails or data isn't serializable

    Example:
        >>> safe_write_json("output.json", {"key": "value"}, "/app/data")
    """
    import json

    with safe_open(filepath, "w", allowed_base) as f:
        json.dump(data, f, indent=indent)


def safe_read_file(
    filepath: Union[str, Path],
    allowed_base: Optional[Union[str, Path]] = None,
    encoding: str = "utf-8",
) -> str:
    """
    Safely read a text file with path traversal protection.

    Args:
        filepath: Path to text file
        allowed_base: Base directory the file must be within
        encoding: Text encoding (default: utf-8)

    Returns:
        File contents as string

    Raises:
        ValueError: If path validation fails
        FileNotFoundError: If file doesn't exist

    Example:
        >>> content = safe_read_file("data.txt", "/trusted/dir")
    """
    with safe_open(filepath, "r", allowed_base, encoding=encoding) as f:
        return f.read()


def safe_write_file(
    filepath: Union[str, Path],
    content: str,
    allowed_base: Optional[Union[str, Path]] = None,
    encoding: str = "utf-8",
) -> None:
    """
    Safely write content to a text file with path traversal protection.

    Args:
        filepath: Path to text file
        content: Content to write
        allowed_base: Base directory the file must be within
        encoding: Text encoding (default: utf-8)

    Raises:
        ValueError: If path validation fails

    Example:
        >>> safe_write_file("output.txt", "Hello World", "/trusted/dir")
    """
    with safe_open(filepath, "w", allowed_base, encoding=encoding) as f:
        f.write(content)
