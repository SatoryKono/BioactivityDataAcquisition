#!/usr/bin/env python3
"""Close a GitHub issue"""

import os
import sys

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "SatoryKono/BioactivityDataAcquisition"


def close_issue(issue_number: int, comment: str | None = None) -> bool:
    """Close a GitHub issue"""
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Add comment if provided
    if comment:
        comment_url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
        comment_response = requests.post(comment_url, json={"body": comment}, headers=headers)
        if comment_response.status_code != 201:
            print(f"❌ Failed to add comment: {comment_response.text}")

    # Close issue
    payload = {
        "state": "closed"
    }
    response = requests.patch(url, json=payload, headers=headers)

    if response.status_code == 200:
        print(f"✅ Closed issue #{issue_number}")
        return True
    else:
        print(f"❌ Failed to close issue #{issue_number}")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python close_github_issue.py <issue_number> [comment]")
        sys.exit(1)

    issue_number = int(sys.argv[1])
    comment = sys.argv[2] if len(sys.argv) > 2 else None

    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found in .env file")
        sys.exit(1)

    success = close_issue(issue_number, comment)
    sys.exit(0 if success else 1)