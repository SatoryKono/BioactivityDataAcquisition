#!/usr/bin/env python3
"""Create GitHub issues from test_coverage_issues.md"""

import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "SatoryKono/BioactivityDataAcquisition"
ISSUES_FILE = Path(__file__).parent.parent.parent.parent / "docs" / "05-engineering" / "test_coverage_issues.md"

def parse_issues():
    """Parse issues from markdown file"""
    with open(ISSUES_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by issue headers
    issue_pattern = r"## Issue #\d+: (.+?)\n\n([\s\S]*?)(?=## Issue #\d+:|$)"
    matches = re.findall(issue_pattern, content)

    issues = []
    for i, (title, body) in enumerate(matches, 1):
        # Extract metadata
        priority_match = re.search(r"\*\*Priority:\*\* (.+)", body)
        priority = priority_match.group(1) if priority_match else "P0"

        labels_match = re.search(r"\*\*Labels:\*\* `(.+?)`", body)
        labels_str = labels_match.group(1) if labels_match else ""
        labels = [label.strip() for label in labels_str.split(",")]

        # Clean up body for GitHub API
        # Remove metadata section from body
        body_cleaned = re.sub(r"\*\*Title:\*\*.+?\n\n", "", body, count=1)

        issues.append({
            "title": title,
            "body": body_cleaned,
            "labels": labels,
            "priority": priority
        })

    return issues

def create_issue(issue_data):
    """Create a GitHub issue"""
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "title": issue_data["title"],
        "body": issue_data["body"],
        "labels": issue_data["labels"]
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        issue = response.json()
        print(f"✅ Created: {issue['title']} - {issue['html_url']}")
        return issue
    else:
        print(f"❌ Failed to create: {issue_data['title']}")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def main():
    """Main function"""
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found in .env file")
        sys.exit(1)

    if not ISSUES_FILE.exists():
        print(f"❌ Issues file not found: {ISSUES_FILE}")
        sys.exit(1)

    print(f"📋 Repository: {REPO}")
    print(f"📄 Issues file: {ISSUES_FILE}")
    print()

    issues = parse_issues()
    print(f"📊 Found {len(issues)} issues to create")
    print()

    # Ask for confirmation
    print("Issues to create:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue['title']} ({issue['priority']})")
    print()

    response = input("Proceed? (y/n): ").strip().lower()
    if response != "y":
        print("❌ Aborted")
        sys.exit(0)

    print()
    print("Creating issues...")
    print()

    created = []
    failed = []

    for issue in issues:
        result = create_issue(issue)
        if result:
            created.append(result)
        else:
            failed.append(issue["title"])

    print()
    print("=" * 60)
    print(f"✅ Created: {len(created)} issues")
    print(f"❌ Failed: {len(failed)} issues")

    if failed:
        print()
        print("Failed issues:")
        for title in failed:
            print(f"  - {title}")

if __name__ == "__main__":
    main()