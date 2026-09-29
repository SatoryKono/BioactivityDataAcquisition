#!/usr/bin/env python3
"""Automated DeepWiki update utility for BioETL.

`.devin/wiki.json` is the single source of truth for the local derived wiki
(consumed by memory RAG via src/memory/rag/devin_wiki.py). The modular
`.devin/wiki-*.json` files are generated projections of the monolith — never
edit them by hand; regenerate with --emit-modules / --update instead.

Usage:
    python scripts/ai/update_deepwiki.py --backup
    python scripts/ai/update_deepwiki.py --emit-modules
    python scripts/ai/update_deepwiki.py --update wiki-core.json
    python scripts/ai/update_deepwiki.py --validate
    python scripts/ai/update_deepwiki.py --check
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


MODULES = [
    "wiki-core.json",
    "wiki-architecture.json",
    "wiki-pipelines.json",
    "wiki-schemas.json",
    "wiki-providers.json",
    "wiki-observability.json",
    "wiki-reference.json",
]

# Top-level DeepWiki section -> module file. The wiki.json monolith is
# DFS-ordered, so each section's pages stay contiguous after filtering.
SECTION_MODULE = {
    "BioETL Overview": "wiki-core.json",
    "AI Agent Subsystem and Memory": "wiki-core.json",
    "Architecture": "wiki-architecture.json",
    "Data Pipelines": "wiki-pipelines.json",
    "Run Control Plane and Observability": "wiki-observability.json",
    "Quality Governance and CI/CD": "wiki-reference.json",
    "Diagram and Documentation Generation": "wiki-reference.json",
    "Operations and Deployment": "wiki-reference.json",
    "Glossary": "wiki-reference.json",
}

# Subtree overrides win over the top-level section mapping.
SUBTREE_MODULE = {
    "Provider Adapters": "wiki-providers.json",
    "Schema Governance and Parity": "wiki-schemas.json",
}

# Reference tokens extracted from "Canonical anchors:" segments only:
# directory-ish tokens end with "/", file tokens carry a known extension.
_ANCHOR_RE = re.compile(r"[\w\./\*\-]+/|[\w\./\-]+\.(?:mdc|md|json|py|yaml|yml|toml)")
_ANCHOR_SECTION_RE = re.compile(r"Canonical anchors?:\s*([^\.\n]+)")


def _anchor_refs(payload: dict[str, Any]) -> list[str]:
    """Extract canonical-anchor path refs from all page_notes."""
    refs: list[str] = []
    for page in payload.get("pages", []):
        if not isinstance(page, dict):
            continue
        for note in page.get("page_notes", []):
            content = note.get("content") if isinstance(note, dict) else note
            if not isinstance(content, str):
                continue
            for segment in _ANCHOR_SECTION_RE.findall(content):
                for token in segment.split(","):
                    for match in _ANCHOR_RE.findall(token.strip()):
                        refs.append(match)
    return refs


class DeepWikiUpdater:
    """Automated DeepWiki update utility."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.wiki_dir = repo_path / ".devin"
        self.monolith = self.wiki_dir / "wiki.json"
        self.modules = list(MODULES)

    def backup_wiki_files(self) -> bool:
        """Create git commit with current wiki files."""
        print("Backing up wiki files...")
        try:
            subprocess.run(
                ["git", "add", ".devin/wiki*.json"],
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
            print("OK wiki files backed up")
            return True
        except subprocess.CalledProcessError as e:
            print(f"FAIL backup: {e}")
            return False

    def _load_monolith(self) -> dict[str, Any]:
        return json.loads(self.monolith.read_text(encoding="utf-8"))

    @staticmethod
    def _ancestors(
        page: dict[str, Any], by_title: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Return ancestor titles from page up to the root, page first."""
        chain = [page["title"]]
        seen = {page["title"]}
        cur = page
        while cur.get("parent"):
            parent = cur["parent"]
            if parent in seen:
                break
            seen.add(parent)
            chain.append(parent)
            cur = by_title.get(parent, {})
            if not cur:
                break
        return chain

    def _module_for(
        self, page: dict[str, Any], by_title: dict[str, dict[str, Any]]
    ) -> str:
        chain = self._ancestors(page, by_title)
        for title in chain:  # nearest ancestor wins
            if title in SUBTREE_MODULE:
                return SUBTREE_MODULE[title]
        return SECTION_MODULE.get(chain[-1], "wiki-reference.json")

    def emit_modules(self, only: str | None = None) -> bool:
        """Regenerate wiki-*.json module files from the wiki.json monolith."""
        wiki = self._load_monolith()
        pages = wiki.get("pages", [])
        by_title = {p["title"]: p for p in pages}

        buckets: dict[str, list[dict[str, Any]]] = {m: [] for m in self.modules}
        for page in pages:
            buckets[self._module_for(page, by_title)].append(page)

        targets = [only] if only else self.modules
        ok = True
        for module in targets:
            name = module if module.endswith(".json") else f"wiki-{module}.json"
            if name not in buckets:
                print(f"FAIL unknown module: {module}")
                ok = False
                continue
            module_pages = buckets[name]
            payload = {
                "version": wiki.get("version", "2.1"),
                "generated_from": "wiki.json",
                "repo_notes": wiki.get("repo_notes", []),
                "pages": module_pages,
            }
            text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            path = self.wiki_dir / name
            if path.exists() and path.read_text(encoding="utf-8") == text:
                print(f"OK {name} unchanged ({len(module_pages)} pages)")
                continue
            path.write_text(text, encoding="utf-8")
            print(f"OK wrote {name} ({len(module_pages)} pages)")
        return ok

    def validate_json_structure(self) -> bool:
        """Validate JSON structure of monolith and module files."""
        print("Validating JSON structure...")
        all_valid = True
        for name in ["wiki.json", *self.modules]:
            path = self.wiki_dir / name
            if not path.exists():
                print(f"FAIL {name} does not exist")
                all_valid = False
                continue
            try:
                json.loads(path.read_text(encoding="utf-8"))
                print(f"OK {name} is valid JSON")
            except json.JSONDecodeError as e:
                print(f"FAIL {name} invalid JSON: {e}")
                all_valid = False
        return all_valid

    def validate_parents(self, payload: dict[str, Any] | None = None) -> bool:
        """Check that every page's parent exists."""
        if payload is None:
            payload = self._load_monolith()
        titles = {p.get("title") for p in payload.get("pages", [])}
        missing = sorted(
            {
                p["parent"]
                for p in payload.get("pages", [])
                if isinstance(p, dict) and p.get("parent") and p["parent"] not in titles
            }
        )
        if missing:
            print(f"FAIL pages with missing parents: {missing}")
            return False
        print("OK all page parents resolve")
        return True

    def validate_canonical_anchors(self) -> bool:
        """Check that every path in Canonical anchors segments exists."""
        print("Validating canonical anchors...")
        missing: list[str] = []
        total = 0
        for ref in _anchor_refs(self._load_monolith()):
            total += 1
            if "*" in ref:
                continue
            if not (self.repo_path / ref.rstrip("/")).exists():
                missing.append(ref)
        if missing:
            print(f"FAIL {len(missing)}/{total} anchor refs do not exist:")
            for ref in sorted(set(missing)):
                print(f"  MISSING {ref}")
            return False
        print(f"OK all {total} canonical anchor refs resolve")
        return True

    def check_mcp_credentials(self) -> bool:
        """Check if DeepWiki MCP credentials are configured."""
        print("Checking DeepWiki MCP credentials...")
        env_file = self.repo_path / ".env"
        if not env_file.exists():
            print("FAIL .env file does not exist")
            return False

        content = env_file.read_text(encoding="utf-8")
        has_api_key = "DEEPWIKI_API_KEY" in content
        has_org_id = "DEEPWIKI_ORGANISATION_ID" in content

        if has_api_key and has_org_id:
            print("OK DeepWiki MCP credentials found")
            return True
        print("FAIL DeepWiki MCP credentials not found")
        return False

    def print_update_summary(self) -> None:
        """Print summary of what would be updated."""
        print("\n" + "=" * 60)
        print("DeepWiki Update Summary")
        print("=" * 60)
        print("\nModule projections (generated from wiki.json):")
        for module in self.modules:
            module_path = self.wiki_dir / module
            status = "present" if module_path.exists() else "missing"
            print(f"  {status:8} {module}")
        print("\nCanonical sources to check:")
        print("  - docs/00-project/")
        print("  - docs/02-architecture/decisions/")
        print("  - AGENTS.md")
        print("  - .devin/agents/ , .devin/skills/")
        print("\nSee .devin/workflows/deepwiki-regeneration.md for the workflow.")
        print("=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated DeepWiki update script for BioETL"
    )
    parser.add_argument(
        "--backup", action="store_true", help="Backup current wiki files"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate JSON, parent links, and canonical anchors",
    )
    parser.add_argument(
        "--emit-modules",
        action="store_true",
        help="Regenerate all wiki-*.json module files from wiki.json",
    )
    parser.add_argument(
        "--update",
        metavar="MODULE",
        help="Regenerate a single module (e.g. core or wiki-core.json)",
    )
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

    if args.backup and not updater.backup_wiki_files():
        return 1

    if args.update:
        return 0 if updater.emit_modules(only=args.update) else 1

    if args.emit_modules and not updater.emit_modules():
        return 1

    if args.validate:
        ok = (
            updater.validate_json_structure()
            and updater.validate_parents()
            and updater.validate_canonical_anchors()
        )
        if not ok:
            return 1

    if args.check:
        updater.check_mcp_credentials()
        updater.validate_json_structure()
        updater.validate_parents()
        updater.validate_canonical_anchors()
        updater.print_update_summary()
        return 0

    if not (args.backup or args.update or args.emit_modules or args.validate):
        updater.print_update_summary()
        print(
            "\nUse --backup, --emit-modules, --update MODULE, --validate, "
            "or see .devin/workflows/deepwiki-regeneration.md"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
