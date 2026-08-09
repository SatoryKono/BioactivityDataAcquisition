#!/usr/bin/env python3
"""Automated DeepWiki update script for BioETL.

This script helps regenerate and update local .devin/wiki-*.json files
to reflect the current state of the repository using DeepWiki MCP.

Usage:
    python scripts/ai/update_deepwiki.py --backup
    python scripts/ai/update_deepwiki.py --update core
    python scripts/ai/update_deepwiki.py --validate
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


class DeepWikiUpdater:
    """Automated DeepWiki update utility."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.wiki_dir = repo_path / ".devin"
        self.modules = [
            "wiki-core.json",
            "wiki-architecture.json",
            "wiki-pipelines.json",
            "wiki-schemas.json",
            "wiki-providers.json",
            "wiki-observability.json",
            "wiki-reference.json",
        ]

    def backup_wiki_files(self) -> bool:
        """Create git commit with current wiki files."""
        print("Backing up wiki files...")
        try:
            subprocess.run(
                ["git", "add", ".devin/wiki-*.json"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    "backup: wiki files before DeepWiki regeneration",
                ],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            print("✓ Wiki files backed up successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Backup failed: {e}")
            return False

    def identify_changed_modules(self) -> list[str]:
        """Identify which wiki modules need updates based on git changes."""
        print("Identifying changed modules...")
        # Get changed files in last 30 days
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    "--since='30 days ago'",
                    "--name-only",
                    "--",
                    "docs/00-project/",
                    "docs/02-architecture/decisions/",
                    "AGENTS.md",
                    ".devin/agents/",
                    ".devin/skills/",
                ],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            changed_files = result.stdout.strip().split("\n")
            print(f"Found {len(changed_files)} changed files in canonical sources")

            # Map changes to wiki modules
            # This is a simplified mapping - in practice, you'd analyze
            # which canonical anchors are affected
            return self.modules
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to identify changes: {e}")
            return self.modules

    def validate_json_structure(self) -> bool:
        """Validate JSON structure of all wiki files."""
        print("Validating JSON structure...")
        all_valid = True
        for module in self.modules:
            module_path = self.wiki_dir / module
            if not module_path.exists():
                print(f"✗ {module} does not exist")
                all_valid = False
                continue
            try:
                with open(module_path, encoding="utf-8") as f:
                    json.load(f)
                print(f"✓ {module} is valid JSON")
            except json.JSONDecodeError as e:
                print(f"✗ {module} has invalid JSON: {e}")
                all_valid = False
        return all_valid

    def validate_canonical_anchors(self) -> bool:
        """Validate that canonical anchors exist."""
        print("Validating canonical anchors...")
        # This would check that all files referenced in page_notes exist
        # For now, just check key files
        key_files = [
            "AGENTS.md",
            "docs/00-project/ai/memory/README.md",
            "docs/00-project/RULES.md",
        ]
        all_valid = True
        for file_path in key_files:
            if not (self.repo_path / file_path).exists():
                print(f"✗ Canonical anchor {file_path} does not exist")
                all_valid = False
        if all_valid:
            print("✓ All key canonical anchors exist")
        return all_valid

    def check_mcp_credentials(self) -> bool:
        """Check if DeepWiki MCP credentials are configured."""
        print("Checking DeepWiki MCP credentials...")
        env_file = self.repo_path / ".env"
        if not env_file.exists():
            print("✗ .env file does not exist")
            return False

        with open(env_file, encoding="utf-8") as f:
            content = f.read()
            has_api_key = "DEEPWIKI_API_KEY" in content
            has_org_id = "DEEPWIKI_ORGANISATION_ID" in content

        if has_api_key and has_org_id:
            print("✓ DeepWiki MCP credentials found")
            return True
        else:
            print("✗ DeepWiki MCP credentials not found")
            return False

    def print_update_summary(self) -> None:
        """Print summary of what would be updated."""
        print("\n" + "=" * 60)
        print("DeepWiki Update Summary")
        print("=" * 60)
        print("\nModules to update:")
        for module in self.modules:
            module_path = self.wiki_dir / module
            if module_path.exists():
                print(f"  ✓ {module}")
            else:
                print(f"  ✗ {module} (missing)")
        print("\nCanonical sources to check:")
        print("  - docs/00-project/")
        print("  - docs/02-architecture/decisions/")
        print("  - AGENTS.md")
        print("  - .devin/agents/")
        print("  - .devin/skills/")
        print("\nSee .devin/workflows/deepwiki-regeneration.md for detailed workflow.")
        print("=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated DeepWiki update script for BioETL"
    )
    parser.add_argument(
        "--backup", action="store_true", help="Backup current wiki files"
    )
    parser.add_argument("--validate", action="store_true", help="Validate wiki files")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check prerequisites and print summary",
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path.cwd(),
        help="Path to repository root (default: cwd)",
    )

    args = parser.parse_args()
    updater = DeepWikiUpdater(args.repo_path)

    if args.backup:
        if not updater.backup_wiki_files():
            return 1

    if args.validate:
        json_valid = updater.validate_json_structure()
        anchors_valid = updater.validate_canonical_anchors()
        if not (json_valid and anchors_valid):
            return 1

    if args.check:
        updater.check_mcp_credentials()
        updater.validate_json_structure()
        updater.validate_canonical_anchors()
        updater.print_update_summary()
        return 0

    # Default: print summary
    updater.print_update_summary()
    print(
        "\nUse --backup to backup, --validate to validate, or follow the manual workflow in .devin/workflows/deepwiki-regeneration.md"
    )
    return 0


if __name__ == "__main__":
    exit(main())
