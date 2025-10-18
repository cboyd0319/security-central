#!/usr/bin/env python3
"""
Send PagerDuty alerts for critical security issues.
"""

import os
import requests
import argparse
from datetime import datetime


def send_alert(severity: str, cve: str = None, count: int = None, message: str = None):
    """Send PagerDuty alert."""
    routing_key = os.environ.get('PAGERDUTY_KEY')

    if not routing_key:
        print("PAGERDUTY_KEY not set, skipping alert")
        return

    if message is None:
        if cve:
            message = f"CRITICAL CVE: {cve}"
        elif count:
            message = f"{count} CRITICAL vulnerabilities detected"
        else:
            message = "Critical security alert"

    payload = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": message,
            "severity": severity.lower(),
            "source": "security-central",
            "timestamp": datetime.utcnow().isoformat(),
            "custom_details": {
                "cve": cve or "N/A",
                "count": count or 0
            }
        }
    }

    response = requests.post(
        'https://events.pagerduty.com/v2/enqueue',
        json=payload
    )

    if response.status_code == 202:
        print("✅ PagerDuty alert sent")
    else:
        print(f"❌ PagerDuty alert failed: {response.text}")


def main():
    parser = argparse.ArgumentParser(description='Send PagerDuty alert')
    parser.add_argument('--severity', required=True, choices=['critical', 'error', 'warning', 'info'])
    parser.add_argument('--cve', help='CVE ID')
    parser.add_argument('--count', type=int, help='Number of issues')
    parser.add_argument('--message', help='Custom message')
    args = parser.parse_args()

    send_alert(args.severity, args.cve, args.count, args.message)


if __name__ == '__main__':
    main()
