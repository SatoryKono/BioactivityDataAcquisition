#!/usr/bin/env python3
"""
Demo version of SonarQube issue processor - simulates the workflow without real API calls.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Simulated data
SIMULATED_SONAR_ISSUES = [
    {
        "key": "ISSUE-1",
        "severity": "MAJOR",
        "type": "BUG",
        "message": "Potential null pointer dereference",
        "component": "src/backend/services/UserService.java",
        "line": 42,
        "creationDate": "2024-01-15T10:30:00+0000",
    },
    {
        "key": "ISSUE-2",
        "severity": "CRITICAL",
        "type": "VULNERABILITY",
        "message": "SQL injection vulnerability",
        "component": "src/backend/api/UserController.java",
        "line": 87,
        "creationDate": "2024-01-10T09:15:00+0000",
    },
    {
        "key": "ISSUE-3",
        "severity": "MINOR",
        "type": "CODE_SMELL",
        "message": "Unused variable 'temp'",
        "component": "src/frontend/components/UserProfile.jsx",
        "line": 15,
        "creationDate": "2024-01-12T14:20:00+0000",
    },
    {
        "key": "ISSUE-4",
        "severity": "MAJOR",
        "type": "BUG",
        "message": "Missing error handling for database connection",
        "component": "src/database/repositories/BaseRepository.java",
        "line": 28,
        "creationDate": "2024-01-18T11:45:00+0000",
    },
    {
        "key": "ISSUE-5",
        "severity": "MINOR",
        "type": "CODE_SMELL",
        "message": "Method 'calculateTotal' has high cognitive complexity",
        "component": "src/utils/mathHelper.js",
        "line": 63,
        "creationDate": "2024-01-16T13:10:00+0000",
    },
]

# Project layer mapping
LAYER_MAPPING = {
    "frontend": ["src/frontend", "src/ui", "src/components"],
    "backend": ["src/backend", "src/api", "src/services"],
    "database": ["src/database", "src/models", "src/repositories"],
    "tests": ["src/tests", "test", "tests"],
    "config": ["config", "src/config"],
    "utils": ["src/utils", "src/helpers", "src/common"],
}


def get_sonar_issues(project_key: str) -> list[dict[str, Any]]:
    """Simulate fetching issues from SonarQube."""
    print(f"🔍 Simulating SonarQube API call for project: {project_key}")
    return SIMULATED_SONAR_ISSUES


def group_issues_by_layer(
    issues: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
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


def create_github_issue_simulation(layer: str, issues: list[dict[str, Any]]) -> str:
    """Simulate creating a GitHub issue for a specific layer's Sonar issues."""
    if not issues:
        return ""

    # Generate a mock GitHub issue URL
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    mock_url = f"https://github.com/bioactivitydataacquisition2/issues/{hash(layer + timestamp) % 1000}"

    print(f"📝 Simulating GitHub issue creation for {layer} layer...")
    print(f"    Title: SonarQube Issues: {layer} layer ({len(issues)} issues)")
    print(f"    Labels: sonarqube, quality, {layer}")
    print(f"    URL: {mock_url}")

    # Show issue details
    print("    Issues included:")
    for i, issue in enumerate(issues, 1):
        print(
            f"      {i}. [{issue['severity']}] {issue['message']} ({issue['component']}:{issue['line']})"
        )

    return mock_url


def main():
    """Main execution function."""
    print("🚀 Starting SonarQube Issue Processor Demo")
    print("=" * 50)

    # Simulated project key
    project_key = "bioactivitydataacquisition2"

    # Step 1: Fetch issues
    issues = get_sonar_issues(project_key)
    print(f"✅ Found {len(issues)} simulated SonarQube issues")

    # Step 2: Group by layers
    layered_issues = group_issues_by_layer(issues)

    print("\n📊 Issue Distribution by Layer:")
    print("-" * 40)
    for layer, layer_issues in layered_issues.items():
        print(f"  {layer:12}: {len(layer_issues):2} issues")

    # Step 3: Create GitHub issues
    print("\n🎯 Creating GitHub Issues:")
    print("-" * 40)

    github_issues = []
    for layer, layer_issues in layered_issues.items():
        if layer_issues:
            url = create_github_issue_simulation(layer, layer_issues)
            if url:
                github_issues.append((layer, url))

    # Step 4: Summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY REPORT")
    print("=" * 50)
    print(f"Total Issues Processed: {len(issues)}")
    print(f"GitHub Issues Created: {len(github_issues)}")
    print("\nGenerated GitHub Issues:")
    for layer, url in github_issues:
        print(f"  • {layer}: {url}")

    print("\n✅ Demo completed successfully!")
    print("\n💡 To run with real data:")
    print("   1. Create .env file with your tokens:")
    print("      SONARQUBE_TOKEN='your-sonarcloud-token'")
    print("      GITHUB_TOKEN='your-github-token'")
    print("   2. Run: python3 sonar_issue_processor.py")


if __name__ == "__main__":
    main()
