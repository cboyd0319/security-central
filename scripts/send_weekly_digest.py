#!/usr/bin/env python3
"""
Send weekly digest to Slack.
"""

import json
import argparse
import os
import requests


def send_digest(report_file: str, slack_webhook: str):
    """Send weekly digest to Slack."""
    
    if not slack_webhook:
        print("No Slack webhook provided, skipping notification")
        return

    with open(report_file) as f:
        audit = json.load(f)

    # Create Slack message
    message = {
        "text": "📊 Weekly Security Audit Digest",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Weekly Security Audit Digest"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Repositories*\n{audit['summary']['total_repos']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Dependencies*\n{audit['summary']['total_dependencies']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Security Issues*\n{audit['summary']['security_issues']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*License Issues*\n{audit['summary']['license_issues']}"
                    }
                ]
            }
        ]
    }

    # Add action items if there are issues
    if audit['summary']['security_issues'] > 0 or audit['summary']['license_issues'] > 0:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "⚠️ *Action Required*\nReview the weekly audit report for details."
            }
        })

    # Send to Slack
    try:
        response = requests.post(slack_webhook, json=message)
        response.raise_for_status()
        print("Weekly digest sent to Slack successfully")
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")


def main():
    parser = argparse.ArgumentParser(description='Send weekly digest to Slack')
    parser.add_argument('--report', required=True, help='Audit report JSON file')
    parser.add_argument('--slack-webhook', help='Slack webhook URL')
    args = parser.parse_args()

    webhook = args.slack_webhook or os.getenv('SLACK_WEBHOOK')
    send_digest(args.report, webhook)


if __name__ == '__main__':
    main()
