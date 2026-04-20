#!/usr/bin/env python3
"""Compatibility shim for the historical ``scripts.ai.src.sonar_issue_processor`` path."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.sonar_issue_processor import *  # noqa: F403
from scripts.ai.sonar_issue_processor import main


if __name__ == "__main__":
    main()
    if not SONARQUBE_TOKEN:
        print("❌ SonarQube configuration missing. Please set SONARQUBE_TOKEN.")
        return

    if not GITHUB_TOKEN:
        print("❌ GitHub token missing. Please set GITHUB_TOKEN.")
        return

    # Get project key (could be passed as argument or configured)
    project_key = "bioactivitydataacquisition2"  # Adjust as needed

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
