#!/usr/bin/env python3
"""
Send PagerDuty alerts for critical security issues.
"""

import argparse
import os
from datetime import datetime, timezone
from typing import Optional

import requests


def send_alert(
    severity: str,
    cve: Optional[str] = None,
    count: Optional[int] = None,
    message: Optional[str] = None,
) -> None:
    """Send PagerDuty alert for security issue.

    Args:
        severity: Alert severity (critical, error, warning, info)
        cve: Optional CVE identifier
        count: Optional count of vulnerabilities
        message: Optional custom message (auto-generated if not provided)
    """
    routing_key: Optional[str] = os.environ.get("PAGERDUTY_KEY")

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

    payload: dict = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": message,
            "severity": severity.lower(),
            "source": "security-central",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "custom_details": {"cve": cve or "N/A", "count": count or 0},
        },
    }

    response: requests.Response = requests.post(
        "https://events.pagerduty.com/v2/enqueue", json=payload
    )

    if response.status_code == 202:
        print("✅ PagerDuty alert sent")
    else:
        print(f"❌ PagerDuty alert failed: {response.text}")


def main() -> None:
    """Main entry point for PagerDuty alerting CLI."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Send PagerDuty alert")
    parser.add_argument(
        "--severity", required=True, choices=["critical", "error", "warning", "info"]
    )
    parser.add_argument("--cve", help="CVE ID")
    parser.add_argument("--count", type=int, help="Number of issues")
    parser.add_argument("--message", help="Custom message")
    args: argparse.Namespace = parser.parse_args()

    send_alert(args.severity, args.cve, args.count, args.message)


if __name__ == "__main__":
    main()
