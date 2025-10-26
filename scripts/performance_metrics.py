#!/usr/bin/env python3
"""
Performance metrics collection for security-central operations.

Tracks execution time, success rates, and resource usage for all scanning operations.
"""

import functools
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar

import psutil

from utils import safe_open

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class OperationMetrics:
    """Metrics for a single operation execution.

    Attributes:
        operation_name: Name of the operation
        start_time: ISO timestamp when operation started
        end_time: ISO timestamp when operation ended
        duration_seconds: Total execution time in seconds
        success: Whether operation completed successfully
        error_message: Error message if operation failed
        repo_name: Repository name if applicable
        findings_count: Number of findings if applicable
        memory_usage_mb: Peak memory usage in MB
        cpu_percent: Average CPU usage percentage
    """

    operation_name: str
    start_time: str
    end_time: str
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    repo_name: Optional[str] = None
    findings_count: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollector:
    """Collect and aggregate performance metrics.

    Attributes:
        metrics_file: Path to metrics JSON file
        metrics: List of collected metrics
    """

    def __init__(self, metrics_file: str = "metrics/performance.json") -> None:
        """Initialize metrics collector.

        Args:
            metrics_file: Path to metrics JSON file
        """
        self.metrics_file: Path = Path(metrics_file)
        self.metrics: list[OperationMetrics] = []
        self._ensure_metrics_dir()

    def _ensure_metrics_dir(self) -> None:
        """Create metrics directory if it doesn't exist."""
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def record_operation(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
        repo_name: Optional[str] = None,
        findings_count: Optional[int] = None,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
    ) -> None:
        """Record metrics for a completed operation.

        Args:
            operation_name: Name of the operation
            duration: Duration in seconds
            success: Whether operation succeeded
            error: Error message if failed
            repo_name: Repository name if applicable
            findings_count: Number of findings if applicable
            memory_mb: Peak memory usage in MB
            cpu_percent: Average CPU usage percentage
        """
        now = datetime.now(timezone.utc).isoformat()
        start_time = datetime.fromisoformat(now.replace("Z", "+00:00"))
        start_time = start_time.replace(tzinfo=timezone.utc)
        start_iso = start_time.timestamp() - duration

        metric = OperationMetrics(
            operation_name=operation_name,
            start_time=datetime.fromtimestamp(start_iso, tz=timezone.utc).isoformat(),
            end_time=now,
            duration_seconds=round(duration, 2),
            success=success,
            error_message=error,
            repo_name=repo_name,
            findings_count=findings_count,
            memory_usage_mb=round(memory_mb, 2) if memory_mb else None,
            cpu_percent=round(cpu_percent, 2) if cpu_percent else None,
        )
        self.metrics.append(metric)

    def save_metrics(self) -> None:
        """Save collected metrics to file."""
        existing_metrics: list[Dict[str, Any]] = []

        # Load existing metrics if file exists
        if self.metrics_file.exists():
            try:
                with safe_open(self.metrics_file, allowed_base=False) as f:
                    data = json.load(f)
                    existing_metrics = data.get("operations", [])
            except (json.JSONDecodeError, KeyError):
                existing_metrics = []

        # Append new metrics
        all_metrics = existing_metrics + [m.to_dict() for m in self.metrics]

        # Save with metadata
        output = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_operations": len(all_metrics),
            "operations": all_metrics,
        }

        with safe_open(self.metrics_file, "w", allowed_base=False) as f:
            json.dump(output, f, indent=2)

    def get_summary(self) -> Dict[str, Any]:
        """Generate summary statistics from collected metrics.

        Returns:
            Dictionary with summary statistics
        """
        if not self.metrics:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "total_findings": 0,
            }

        successful = [m for m in self.metrics if m.success]
        failed = [m for m in self.metrics if not m.success]

        durations = [m.duration_seconds for m in self.metrics]
        findings = [m.findings_count for m in self.metrics if m.findings_count is not None]

        return {
            "total_operations": len(self.metrics),
            "successful_operations": len(successful),
            "failed_operations": len(failed),
            "success_rate": round(len(successful) / len(self.metrics) * 100, 2),
            "avg_duration_seconds": round(sum(durations) / len(durations), 2),
            "min_duration_seconds": round(min(durations), 2),
            "max_duration_seconds": round(max(durations), 2),
            "total_findings": sum(findings),
            "avg_findings_per_repo": round(sum(findings) / len(findings), 2) if findings else 0,
            "operations_by_type": self._group_by_operation(),
            "failures": [{"operation": m.operation_name, "error": m.error_message} for m in failed],
        }

    def _group_by_operation(self) -> Dict[str, int]:
        """Group metrics by operation name.

        Returns:
            Dictionary mapping operation names to counts
        """
        counts: Dict[str, int] = {}
        for metric in self.metrics:
            counts[metric.operation_name] = counts.get(metric.operation_name, 0) + 1
        return counts


def measure_performance(
    operation_name: str,
    collector: Optional[MetricsCollector] = None,
    track_resources: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to measure function performance.

    Args:
        operation_name: Name of the operation being measured
        collector: MetricsCollector instance (creates new if None)
        track_resources: Whether to track memory and CPU usage

    Returns:
        Decorated function that records metrics

    Example:
        >>> @measure_performance("scan_repository")
        ... def scan_repo(repo_name):
        ...     # scanning logic
        ...     return findings
    """
    if collector is None:
        collector = MetricsCollector()

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Get process for resource monitoring
            process = psutil.Process() if track_resources else None
            initial_memory = process.memory_info().rss / 1024 / 1024 if process else None
            cpu_percent_values: list[float] = []

            start_time = time.time()
            success = False
            error_msg: Optional[str] = None
            result: Optional[T] = None

            try:
                # Monitor CPU during execution (sample every 0.1s)
                if process:
                    cpu_percent_values.append(process.cpu_percent(interval=0.1))

                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_msg = str(e)
                raise
            finally:
                duration = time.time() - start_time

                # Calculate resource usage
                memory_usage = None
                cpu_avg = None

                if process:
                    final_memory = process.memory_info().rss / 1024 / 1024
                    memory_usage = max(final_memory - initial_memory, 0) if initial_memory else None

                    # Get final CPU sample
                    cpu_percent_values.append(process.cpu_percent(interval=0.1))
                    cpu_avg = (
                        sum(cpu_percent_values) / len(cpu_percent_values)
                        if cpu_percent_values
                        else None
                    )

                # Extract repo name and findings count if available
                repo_name: Optional[str] = None
                findings_count: Optional[int] = None

                # Try to extract from args/kwargs
                if "repo_name" in kwargs:
                    repo_name = kwargs["repo_name"]
                elif len(args) > 0 and hasattr(args[0], "name"):
                    repo_name = getattr(args[0], "name")

                # Try to extract findings count from result
                if result is not None:
                    if isinstance(result, list):
                        findings_count = len(result)
                    elif isinstance(result, dict) and "findings" in result:
                        findings_count = len(result["findings"])

                collector.record_operation(
                    operation_name=operation_name,
                    duration=duration,
                    success=success,
                    error=error_msg,
                    repo_name=repo_name,
                    findings_count=findings_count,
                    memory_mb=memory_usage,
                    cpu_percent=cpu_avg,
                )

                # Auto-save metrics periodically
                if len(collector.metrics) % 10 == 0:
                    collector.save_metrics()

        return wrapper

    return decorator


class TimingContext:
    """Context manager for timing operations.

    Example:
        >>> with TimingContext("database_query") as timer:
        ...     results = db.query(...)
        >>> print(f"Query took {timer.duration} seconds")
    """

    def __init__(self, operation_name: str, collector: Optional[MetricsCollector] = None) -> None:
        """Initialize timing context.

        Args:
            operation_name: Name of the operation
            collector: MetricsCollector instance (creates new if None)
        """
        self.operation_name: str = operation_name
        self.collector: MetricsCollector = collector or MetricsCollector()
        self.start_time: float = 0.0
        self.duration: float = 0.0

    def __enter__(self) -> "TimingContext":
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop timing and record metrics."""
        self.duration = time.time() - self.start_time
        success = exc_type is None
        error_msg = str(exc_val) if exc_val else None

        self.collector.record_operation(
            operation_name=self.operation_name,
            duration=self.duration,
            success=success,
            error=error_msg,
        )


def print_metrics_summary(collector: MetricsCollector) -> None:
    """Print human-readable metrics summary.

    Args:
        collector: MetricsCollector with collected metrics
    """
    summary = collector.get_summary()

    print("\n" + "=" * 60)
    print("PERFORMANCE METRICS SUMMARY")
    print("=" * 60)
    print(f"Total Operations: {summary['total_operations']}")
    print(f"Success Rate: {summary['success_rate']}%")
    print(f"Average Duration: {summary['avg_duration_seconds']}s")
    print(
        f"Duration Range: {summary['min_duration_seconds']}s - {summary['max_duration_seconds']}s"
    )

    if summary["total_findings"] > 0:
        print(f"Total Findings: {summary['total_findings']}")
        print(f"Avg Findings/Repo: {summary['avg_findings_per_repo']}")

    if summary["operations_by_type"]:
        print("\nOperations by Type:")
        for op_type, count in sorted(summary["operations_by_type"].items()):
            print(f"  {op_type}: {count}")

    if summary["failures"]:
        print("\nFailures:")
        for failure in summary["failures"]:
            print(f"  ❌ {failure['operation']}: {failure['error']}")

    print("=" * 60 + "\n")


# Example usage
if __name__ == "__main__":
    # Example 1: Using decorator
    collector = MetricsCollector()

    @measure_performance("example_scan", collector=collector)
    def example_scan(repo_name: str) -> list:
        """Example scanning function."""
        time.sleep(0.5)  # Simulate work
        return [{"cve": "CVE-2024-1", "severity": "HIGH"}]

    # Run some operations
    findings = example_scan("test-repo-1")
    findings = example_scan("test-repo-2")

    # Example 2: Using context manager
    with TimingContext("database_query", collector=collector):
        time.sleep(0.2)  # Simulate query

    # Save and print summary
    collector.save_metrics()
    print_metrics_summary(collector)

    print(f"\nMetrics saved to: {collector.metrics_file}")
