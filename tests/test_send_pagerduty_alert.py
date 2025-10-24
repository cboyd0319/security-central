#!/usr/bin/env python3
"""
Comprehensive tests for scripts/send_pagerduty_alert.py

Tests PagerDuty alert sending functionality.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from send_pagerduty_alert import send_alert, main


class TestSendAlert:
    """Test send_alert function."""

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_send_alert_with_cve(self, mock_post):
        """Test sending alert with CVE."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='critical', cve='CVE-2024-1234')

        # Verify POST was called
        assert mock_post.called
        call_args = mock_post.call_args

        # Verify payload structure
        payload = call_args[1]['json']
        assert payload['routing_key'] == 'test-key-123'
        assert payload['event_action'] == 'trigger'
        assert 'CVE-2024-1234' in payload['payload']['summary']
        assert payload['payload']['severity'] == 'critical'
        assert payload['payload']['custom_details']['cve'] == 'CVE-2024-1234'

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_send_alert_with_count(self, mock_post):
        """Test sending alert with vulnerability count."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='critical', count=5)

        payload = mock_post.call_args[1]['json']
        assert '5 CRITICAL vulnerabilities detected' in payload['payload']['summary']
        assert payload['payload']['custom_details']['count'] == 5

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_send_alert_with_custom_message(self, mock_post):
        """Test sending alert with custom message."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='error', message='Custom security alert')

        payload = mock_post.call_args[1]['json']
        assert payload['payload']['summary'] == 'Custom security alert'
        assert payload['payload']['severity'] == 'error'

    @patch.dict(os.environ, {}, clear=True)
    def test_send_alert_no_api_key(self, capsys):
        """Test sending alert without API key set."""
        send_alert(severity='critical', cve='CVE-2024-1234')

        captured = capsys.readouterr()
        assert 'PAGERDUTY_KEY not set' in captured.out

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_send_alert_default_message(self, mock_post):
        """Test sending alert with default message."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='warning')

        payload = mock_post.call_args[1]['json']
        assert payload['payload']['summary'] == 'Critical security alert'

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_send_alert_failure(self, mock_post, capsys):
        """Test handling of failed alert."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response

        send_alert(severity='critical', cve='CVE-2024-1234')

        captured = capsys.readouterr()
        assert 'PagerDuty alert failed' in captured.out
        assert 'Bad Request' in captured.out

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_send_alert_success_output(self, mock_post, capsys):
        """Test success message output."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='info', message='Test')

        captured = capsys.readouterr()
        assert 'PagerDuty alert sent' in captured.out

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_payload_structure(self, mock_post):
        """Test that payload has correct structure."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='critical', cve='CVE-2024-1234', count=10)

        # Verify URL
        assert mock_post.call_args[0][0] == 'https://events.pagerduty.com/v2/enqueue'

        # Verify payload structure
        payload = mock_post.call_args[1]['json']
        assert 'routing_key' in payload
        assert 'event_action' in payload
        assert 'payload' in payload
        assert 'summary' in payload['payload']
        assert 'severity' in payload['payload']
        assert 'source' in payload['payload']
        assert 'timestamp' in payload['payload']
        assert 'custom_details' in payload['payload']

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_timestamp_format(self, mock_post):
        """Test that timestamp is in ISO format."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='info')

        payload = mock_post.call_args[1]['json']
        timestamp = payload['payload']['timestamp']

        # Should be valid ISO format
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_severity_lowercase(self, mock_post):
        """Test that severity is converted to lowercase."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='CRITICAL')

        payload = mock_post.call_args[1]['json']
        assert payload['payload']['severity'] == 'critical'

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_custom_details_defaults(self, mock_post):
        """Test custom_details defaults when not provided."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='warning')

        payload = mock_post.call_args[1]['json']
        assert payload['payload']['custom_details']['cve'] == 'N/A'
        assert payload['payload']['custom_details']['count'] == 0

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key-123'})
    def test_source_field(self, mock_post):
        """Test that source is set to security-central."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        send_alert(severity='info')

        payload = mock_post.call_args[1]['json']
        assert payload['payload']['source'] == 'security-central'


class TestMain:
    """Test main CLI function."""

    @patch('send_pagerduty_alert.send_alert')
    @patch('sys.argv', ['send_pagerduty_alert.py', '--severity', 'critical', '--cve', 'CVE-2024-1'])
    def test_main_with_cve(self, mock_send_alert):
        """Test main function with CVE argument."""
        main()

        mock_send_alert.assert_called_once_with('critical', 'CVE-2024-1', None, None)

    @patch('send_pagerduty_alert.send_alert')
    @patch('sys.argv', ['send_pagerduty_alert.py', '--severity', 'error', '--count', '5'])
    def test_main_with_count(self, mock_send_alert):
        """Test main function with count argument."""
        main()

        mock_send_alert.assert_called_once_with('error', None, 5, None)

    @patch('send_pagerduty_alert.send_alert')
    @patch('sys.argv', ['send_pagerduty_alert.py', '--severity', 'warning', '--message', 'Test alert'])
    def test_main_with_message(self, mock_send_alert):
        """Test main function with custom message."""
        main()

        mock_send_alert.assert_called_once_with('warning', None, None, 'Test alert')

    @patch('send_pagerduty_alert.send_alert')
    @patch('sys.argv', ['send_pagerduty_alert.py', '--severity', 'critical'])
    def test_main_severity_only(self, mock_send_alert):
        """Test main with only severity argument."""
        main()

        mock_send_alert.assert_called_once_with('critical', None, None, None)

    @patch('send_pagerduty_alert.send_alert')
    @patch('sys.argv', ['send_pagerduty_alert.py', '--severity', 'info', '--cve', 'CVE-2024-1', '--count', '10', '--message', 'Full alert'])
    def test_main_all_arguments(self, mock_send_alert):
        """Test main with all arguments."""
        main()

        mock_send_alert.assert_called_once_with('info', 'CVE-2024-1', 10, 'Full alert')

    @patch('sys.argv', ['send_pagerduty_alert.py'])
    def test_main_missing_required_severity(self):
        """Test main without required severity argument."""
        with pytest.raises(SystemExit):
            main()

    @patch('sys.argv', ['send_pagerduty_alert.py', '--severity', 'invalid'])
    def test_main_invalid_severity(self):
        """Test main with invalid severity choice."""
        with pytest.raises(SystemExit):
            main()

    @patch('send_pagerduty_alert.send_alert')
    @patch('sys.argv', ['send_pagerduty_alert.py', '--severity', 'critical', '--count', 'not-a-number'])
    def test_main_invalid_count_type(self, mock_send_alert):
        """Test main with non-integer count."""
        with pytest.raises(SystemExit):
            main()


class TestIntegration:
    """Integration tests for PagerDuty alerting."""

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'integration-test-key'})
    def test_full_alert_workflow(self, mock_post):
        """Test complete alert workflow."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        # Send different types of alerts
        send_alert('critical', cve='CVE-2024-1234')
        send_alert('error', count=5)
        send_alert('warning', message='Custom warning')

        # Verify all were sent
        assert mock_post.call_count == 3

    @patch('send_pagerduty_alert.requests.post')
    @patch.dict(os.environ, {'PAGERDUTY_KEY': 'test-key'})
    def test_alert_retry_on_failure(self, mock_post):
        """Test sending alert after initial failure."""
        # First call fails
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = 'Server Error'

        # Second call succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 202

        mock_post.side_effect = [mock_response_fail, mock_response_success]

        send_alert('critical', cve='CVE-2024-1')
        send_alert('critical', cve='CVE-2024-1')  # Retry

        assert mock_post.call_count == 2
