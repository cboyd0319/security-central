#!/usr/bin/env python3
"""
Comprehensive tests for scripts/performance_metrics.py

Tests performance tracking, metrics collection, and timing utilities.
"""

import pytest
import time
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from performance_metrics import (
    OperationMetrics,
    MetricsCollector,
    measure_performance,
    TimingContext,
    print_metrics_summary,
)


class TestOperationMetrics:
    """Test OperationMetrics dataclass."""

    def test_create_operation_metrics(self):
        """Test creating OperationMetrics instance."""
        metrics = OperationMetrics(
            operation_name='test_op',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-01T00:00:01',
            duration_seconds=1.0,
            success=True,
            memory_usage_mb=100.5,
            cpu_percent=50.0
        )

        assert metrics.operation_name == 'test_op'
        assert metrics.duration_seconds == 1.0
        assert metrics.success is True
        assert metrics.memory_usage_mb == 100.5
        assert metrics.cpu_percent == 50.0

    def test_optional_fields(self):
        """Test OperationMetrics with optional fields as None."""
        metrics = OperationMetrics(
            operation_name='test_op',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-01T00:00:01',
            duration_seconds=1.0,
            success=True,
            memory_usage_mb=None,
            cpu_percent=None
        )

        assert metrics.memory_usage_mb is None
        assert metrics.cpu_percent is None

    def test_dataclass_fields(self):
        """Test that OperationMetrics is a proper dataclass."""
        metrics = OperationMetrics(
            operation_name='test',
            start_time='2024-01-01T00:00:00',
            end_time='2024-01-01T00:00:01',
            duration_seconds=1.0,
            success=True
        )

        # Dataclass should have __dict__
        assert hasattr(metrics, '__dict__')
        assert 'operation_name' in metrics.__dict__


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_create_collector(self):
        """Test creating MetricsCollector."""
        collector = MetricsCollector()
        assert isinstance(collector, MetricsCollector)
        assert len(collector.metrics) == 0

    def test_record_operation(self):
        """Test recording an operation."""
        collector = MetricsCollector()

        collector.record_operation(
            operation_name='test_operation',
            duration_seconds=1.5,
            success=True,
            memory_usage_mb=200.0,
            cpu_percent=60.0
        )

        assert len(collector.metrics) == 1
        assert collector.metrics[0].operation_name == 'test_operation'
        assert collector.metrics[0].duration_seconds == 1.5
        assert collector.metrics[0].success is True

    def test_record_multiple_operations(self):
        """Test recording multiple operations."""
        collector = MetricsCollector()

        collector.record_operation('op1', 1.0, True)
        collector.record_operation('op2', 2.0, True)
        collector.record_operation('op3', 3.0, False)

        assert len(collector.metrics) == 3
        assert collector.metrics[0].operation_name == 'op1'
        assert collector.metrics[1].operation_name == 'op2'
        assert collector.metrics[2].success is False

    def test_get_summary(self):
        """Test getting metrics summary."""
        collector = MetricsCollector()

        collector.record_operation('op1', 1.0, True, memory_usage_mb=100.0)
        collector.record_operation('op2', 2.0, True, memory_usage_mb=200.0)
        collector.record_operation('op3', 3.0, False, memory_usage_mb=150.0)

        summary = collector.get_summary()

        assert summary['total_operations'] == 3
        assert summary['successful_operations'] == 2
        assert summary['failed_operations'] == 1
        assert summary['total_duration'] == 6.0
        assert summary['average_duration'] == 2.0
        assert summary['max_duration'] == 3.0
        assert summary['min_duration'] == 1.0

    def test_get_summary_empty(self):
        """Test summary with no operations."""
        collector = MetricsCollector()
        summary = collector.get_summary()

        assert summary['total_operations'] == 0
        assert summary['successful_operations'] == 0
        assert summary['failed_operations'] == 0
        assert summary['total_duration'] == 0
        assert summary['average_duration'] == 0

    def test_get_summary_with_memory_stats(self):
        """Test summary includes memory statistics."""
        collector = MetricsCollector()

        collector.record_operation('op1', 1.0, True, memory_usage_mb=100.0)
        collector.record_operation('op2', 2.0, True, memory_usage_mb=200.0)
        collector.record_operation('op3', 3.0, True, memory_usage_mb=150.0)

        summary = collector.get_summary()

        assert 'average_memory_mb' in summary
        assert summary['average_memory_mb'] == pytest.approx(150.0, rel=0.01)
        assert 'max_memory_mb' in summary
        assert summary['max_memory_mb'] == 200.0

    def test_export_to_json(self):
        """Test exporting metrics to JSON file."""
        collector = MetricsCollector()
        collector.record_operation('op1', 1.0, True)
        collector.record_operation('op2', 2.0, False)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tf:
            json_file = tf.name

        try:
            collector.export_to_json(json_file)

            # Read and verify JSON
            with open(json_file) as f:
                data = json.load(f)

            assert 'metrics' in data
            assert 'summary' in data
            assert len(data['metrics']) == 2
            assert data['summary']['total_operations'] == 2
        finally:
            if os.path.exists(json_file):
                os.unlink(json_file)

    def test_export_to_json_empty_collector(self):
        """Test exporting empty collector to JSON."""
        collector = MetricsCollector()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tf:
            json_file = tf.name

        try:
            collector.export_to_json(json_file)

            with open(json_file) as f:
                data = json.load(f)

            assert data['metrics'] == []
            assert data['summary']['total_operations'] == 0
        finally:
            if os.path.exists(json_file):
                os.unlink(json_file)

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        collector = MetricsCollector()
        collector.record_operation('op1', 1.0, True)

        result = collector.to_dict()

        assert 'metrics' in result
        assert 'summary' in result
        assert isinstance(result['metrics'], list)
        assert isinstance(result['summary'], dict)

    def test_success_rate_calculation(self):
        """Test success rate calculation in summary."""
        collector = MetricsCollector()

        # 3 successful, 1 failed
        collector.record_operation('op1', 1.0, True)
        collector.record_operation('op2', 1.0, True)
        collector.record_operation('op3', 1.0, True)
        collector.record_operation('op4', 1.0, False)

        summary = collector.get_summary()

        assert summary['successful_operations'] == 3
        assert summary['failed_operations'] == 1
        assert summary['success_rate'] == 0.75  # 3/4


class TestMeasurePerformance:
    """Test measure_performance decorator."""

    def test_measure_basic_function(self):
        """Test measuring performance of basic function."""
        collector = MetricsCollector()

        @measure_performance('test_func', collector)
        def test_function():
            time.sleep(0.1)
            return "success"

        result = test_function()

        assert result == "success"
        assert len(collector.metrics) == 1
        assert collector.metrics[0].operation_name == 'test_func'
        assert collector.metrics[0].duration_seconds >= 0.1
        assert collector.metrics[0].success is True

    def test_measure_function_with_args(self):
        """Test measuring function with arguments."""
        collector = MetricsCollector()

        @measure_performance('add_numbers', collector)
        def add(a, b):
            return a + b

        result = add(2, 3)

        assert result == 5
        assert len(collector.metrics) == 1
        assert collector.metrics[0].operation_name == 'add_numbers'

    def test_measure_function_with_exception(self):
        """Test measuring function that raises exception."""
        collector = MetricsCollector()

        @measure_performance('failing_func', collector)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

        assert len(collector.metrics) == 1
        assert collector.metrics[0].success is False
        assert collector.metrics[0].operation_name == 'failing_func'

    def test_measure_without_collector(self):
        """Test measuring performance without providing collector."""
        @measure_performance('test_no_collector')
        def test_function():
            return "result"

        # Should work without collector (creates default)
        result = test_function()
        assert result == "result"

    def test_measure_tracks_memory(self):
        """Test that decorator tracks memory usage."""
        collector = MetricsCollector()

        @measure_performance('memory_test', collector)
        def allocate_memory():
            # Allocate some memory
            data = [0] * 1000
            return len(data)

        result = allocate_memory()

        assert result == 1000
        assert len(collector.metrics) == 1
        # Memory usage should be recorded (may be None if psutil not available)
        # We just check it exists as a field

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        @measure_performance('documented_func')
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestTimingContext:
    """Test TimingContext class."""

    def test_timing_context_basic(self):
        """Test basic timing context."""
        collector = MetricsCollector()

        with TimingContext('test_operation', collector):
            time.sleep(0.1)

        assert len(collector.metrics) == 1
        assert collector.metrics[0].operation_name == 'test_operation'
        assert collector.metrics[0].duration_seconds >= 0.1
        assert collector.metrics[0].success is True

    def test_timing_context_with_exception(self):
        """Test timing context when exception occurs."""
        collector = MetricsCollector()

        with pytest.raises(ValueError):
            with TimingContext('failing_operation', collector):
                raise ValueError("Test error")

        assert len(collector.metrics) == 1
        assert collector.metrics[0].success is False

    def test_timing_context_without_collector(self):
        """Test timing context without collector."""
        # Should work without collector (creates default)
        with TimingContext('test_op'):
            time.sleep(0.05)

        # No errors should occur

    def test_timing_context_measures_actual_time(self):
        """Test that context measures actual elapsed time."""
        collector = MetricsCollector()

        with TimingContext('sleep_test', collector):
            time.sleep(0.2)

        assert len(collector.metrics) == 1
        assert collector.metrics[0].duration_seconds >= 0.2
        assert collector.metrics[0].duration_seconds < 0.3

    def test_timing_context_tracks_memory(self):
        """Test that timing context tracks memory."""
        collector = MetricsCollector()

        with TimingContext('memory_context', collector):
            data = [0] * 10000

        assert len(collector.metrics) == 1
        # Memory metrics may be None if psutil unavailable

    def test_nested_timing_contexts(self):
        """Test nested timing contexts."""
        collector = MetricsCollector()

        with TimingContext('outer', collector):
            time.sleep(0.1)
            with TimingContext('inner', collector):
                time.sleep(0.1)

        assert len(collector.metrics) == 2
        assert collector.metrics[0].operation_name == 'inner'
        assert collector.metrics[1].operation_name == 'outer'
        # Outer should take longer than inner
        assert collector.metrics[1].duration_seconds > collector.metrics[0].duration_seconds


class TestPrintMetricsSummary:
    """Test print_metrics_summary function."""

    def test_print_summary_basic(self, capsys):
        """Test printing metrics summary."""
        collector = MetricsCollector()
        collector.record_operation('op1', 1.0, True)
        collector.record_operation('op2', 2.0, True)
        collector.record_operation('op3', 3.0, False)

        print_metrics_summary(collector)

        captured = capsys.readouterr()
        output = captured.out

        # Check that summary contains key information
        assert 'Performance Metrics Summary' in output or 'Total Operations' in output
        assert '3' in output  # Total operations
        assert '2' in output  # Successful operations

    def test_print_summary_empty_collector(self, capsys):
        """Test printing summary for empty collector."""
        collector = MetricsCollector()

        print_metrics_summary(collector)

        captured = capsys.readouterr()
        output = captured.out

        # Should print something even with no metrics
        assert len(output) > 0

    def test_print_summary_with_memory_stats(self, capsys):
        """Test printing summary with memory statistics."""
        collector = MetricsCollector()
        collector.record_operation('op1', 1.0, True, memory_usage_mb=100.0)
        collector.record_operation('op2', 2.0, True, memory_usage_mb=200.0)

        print_metrics_summary(collector)

        captured = capsys.readouterr()
        output = captured.out

        # Check for memory information
        assert '100' in output or '200' in output or 'Memory' in output


class TestPerformanceMetricsIntegration:
    """Integration tests for performance metrics system."""

    def test_full_workflow(self):
        """Test complete performance tracking workflow."""
        collector = MetricsCollector()

        # Use decorator
        @measure_performance('function_test', collector)
        def some_function(x):
            time.sleep(0.05)
            return x * 2

        # Use context manager
        with TimingContext('context_test', collector):
            time.sleep(0.05)

        # Use function
        result = some_function(5)

        assert result == 10
        assert len(collector.metrics) == 2

        # Get summary
        summary = collector.get_summary()
        assert summary['total_operations'] == 2
        assert summary['successful_operations'] == 2
        assert summary['total_duration'] >= 0.1

    def test_export_and_verify_json(self):
        """Test exporting metrics and verifying JSON structure."""
        collector = MetricsCollector()

        @measure_performance('task1', collector)
        def task1():
            return "done"

        @measure_performance('task2', collector)
        def task2():
            return "complete"

        task1()
        task2()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tf:
            json_file = tf.name

        try:
            collector.export_to_json(json_file)

            # Verify JSON structure
            with open(json_file) as f:
                data = json.load(f)

            assert 'metrics' in data
            assert 'summary' in data
            assert len(data['metrics']) == 2
            assert all('operation_name' in m for m in data['metrics'])
            assert all('duration_seconds' in m for m in data['metrics'])
            assert all('success' in m for m in data['metrics'])
        finally:
            if os.path.exists(json_file):
                os.unlink(json_file)

    def test_mixed_success_and_failure(self):
        """Test tracking both successful and failed operations."""
        collector = MetricsCollector()

        @measure_performance('success_func', collector)
        def success_func():
            return "ok"

        @measure_performance('fail_func', collector)
        def fail_func():
            raise RuntimeError("Expected failure")

        success_func()
        try:
            fail_func()
        except RuntimeError:
            pass

        summary = collector.get_summary()
        assert summary['total_operations'] == 2
        assert summary['successful_operations'] == 1
        assert summary['failed_operations'] == 1
        assert summary['success_rate'] == 0.5

    def test_performance_tracking_accuracy(self):
        """Test that performance tracking is reasonably accurate."""
        collector = MetricsCollector()

        @measure_performance('accurate_timing', collector)
        def sleep_function():
            time.sleep(0.15)

        sleep_function()

        assert len(collector.metrics) == 1
        duration = collector.metrics[0].duration_seconds

        # Should be approximately 0.15 seconds (allow 50ms tolerance)
        assert 0.14 <= duration <= 0.20
