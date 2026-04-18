#!/usr/bin/env python3
"""Group SonarQube issues by file and display functions needing simplification."""

import json
import sys


def main():
    data = json.load(sys.stdin)
    issues = [
        issue for issue in data.get("issues", [])
        if "Cognitive Complexity" in issue.get("message", "")
    ]

    files = {}
    for issue in issues:
        component = issue.get("component", "")
        if ":" in component:
            file = component.split(":")[1]
        else:
            file = component

        if file not in files:
            files[file] = []
        files[file].append(issue.get("message", ""))

    for file in list(files.keys())[:20]:
        print(f"File: {file}")
        for message in files[file]:
            print(f"  - {message}")

if __name__ == "__main__":
    main()
