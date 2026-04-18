#!/usr/bin/env python3
"""
Extract SonarQube issues, group by project layers, and create GitHub issues.

This script:
1. Fetches SonarQube issues using the SonarQube API
2. Groups issues by project layers (e.g., frontend, backend, database, etc.)
3. Creates GitHub issues for each layer with the grouped Sonar issues
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests

# Configuration
SONARQUBE_URL = os.getenv("SONARQUBE_URL", "https://sonarcloud.io")
SONARQUBE_ORG = os.getenv("SONARQUBE_ORG")
SONARQUBE_TOKEN = os.getenv("SONARQUBE_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "bioactivitydataacquisition2")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Project layer mapping - customize this based on your project structure
LAYER_MAPPING = {
    "frontend": ["src/frontend", "src/ui", "src/components"],
    "backend": ["src/backend", "src/api", "src/services"],
    "database": ["src/database", "src/models", "src/repositories"],
    "tests": ["src/tests", "test", "tests"],
    "config": ["config", "src/config"],
    "utils": ["src/utils", "src/helpers", "src/common"]
}


def get_sonar_issues(project_key: str) -> list[dict[str, Any]]:
    """Fetch all issues from SonarQube for a given project."""
    url = f"{SONARQUBE_URL}/api/issues/search"
    params = {
        "componentKeys": project_key,
        "ps": 500,  # Page size
        "p": 1,     # Page number
        "resolved": "false"
    }

    headers = {
        "Authorization": f"Bearer {SONARQUBE_TOKEN}"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json().get("issues", [])
    except requests.RequestException as e:
        print(f"Error fetching SonarQube issues: {e}")
        return []


def group_issues_by_layer(issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group issues by project layers based on file paths."""
    layered_issues = {layer: [] for layer in LAYER_MAPPING}
    unclassified = []

    for issue in issues:
        file_path = issue.get("component", "")
        classified = False

        for layer, paths in LAYER_MAPPING.items():
            if any(path in file_path for path in paths):
                layered_issues[layer].append(issue)
                classified = True
                break

        if not classified:
            unclassified.append(issue)

    if unclassified:
        layered_issues["unclassified"] = unclassified

    return layered_issues


def create_github_issue(layer: str, issues: list[dict[str, Any]]) -> bool:
    """Create a GitHub issue for a specific layer's Sonar issues."""
    if not issues:
        return False

    title = f"SonarQube Issues: {layer} layer ({len(issues)} issues)"

    # Build issue body
    body = f"# SonarQube Issues in {layer} Layer\n\n"
    body += f"**Total Issues:** {len(issues)}\n\n"
    body += "## Issues Detail\n\n"

    for i, issue in enumerate(issues, 1):
        severity = issue.get("severity", "UNKNOWN")
        type_ = issue.get("type", "UNKNOWN")
        message = issue.get("message", "No description")
        file_path = issue.get("component", "Unknown file")
        line = issue.get("line", "?")

        body += f"### Issue {i}\n"
        body += f"- **Severity:** {severity}\n"
        body += f"- **Type:** {type_}\n"
        body += f"- **Location:** `{file_path}:{line}`\n"
        body += f"- **Message:** {message}\n\n"

    body += "## Action Required\n"
    body += "- Review and fix the identified issues\n"
    body += "- Update code to comply with quality standards\n"
    body += "- Run SonarQube analysis after fixes to verify resolution\n"

    # Create GitHub issue
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "title": title,
        "body": body,
        "labels": ["sonarqube", "quality", layer]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✅ Created GitHub issue for {layer} layer: {response.json()['html_url']}")
        return True
    except requests.RequestException as e:
        print(f"❌ Error creating GitHub issue for {layer}: {e}")
        return False


def main():
    """Main execution function."""
    if not SONARQUBE_ORG or not SONARQUBE_TOKEN:
        print("❌ SonarQube configuration missing. Please set SONARQUBE_ORG and SONARQUBE_TOKEN.")
        return

    if not GITHUB_TOKEN:
        print("❌ GitHub token missing. Please set GITHUB_TOKEN.")
        return

    # Get project key (could be passed as argument or configured)
    project_key = f"{SONARQUBE_ORG}_bioactivitydataacquisition2"  # Adjust as needed

    print(f"🔍 Fetching SonarQube issues for project: {project_key}")
    issues = get_sonar_issues(project_key)

    if not issues:
        print("✅ No SonarQube issues found!")
        return

    print(f"📊 Found {len(issues)} issues. Grouping by layers...")
    layered_issues = group_issues_by_layer(issues)

    print("\n📝 Issue distribution by layer:")
    for layer, layer_issues in layered_issues.items():
        print(f"  - {layer}: {len(layer_issues)} issues")

    print("\n🚀 Creating GitHub issues...")
    for layer, layer_issues in layered_issues.items():
        if layer_issues:  # Only create issues for layers with problems
            create_github_issue(layer, layer_issues)

    print("✅ Process completed!")


if __name__ == "__main__":
    main()
