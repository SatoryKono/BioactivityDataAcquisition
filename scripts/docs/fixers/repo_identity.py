#!/usr/bin/env python3
"""Synchronize active docs/workflows with the canonical repository identity."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.docs.common.paths import (
    DOCS_DIR,
    PROJECT_ROOT,
    WORKFLOWS_ROOT,
    is_generated_docs_artifact,
)

ROOT = PROJECT_ROOT
DOCS_ROOT = DOCS_DIR
ACTIVE_DOC_EXCLUDED_PARTS = frozenset({"99-archive", "exports", "reports", "generated"})

LEGACY_SLUG_RE = re.compile(r"SatoryKono/BioactivityDataAcquisition2")
LEGACY_URL_RE = re.compile(
    r"https://github\.com/SatoryKono/BioactivityDataAcquisition2"
)
LEGACY_CLONE_RE = re.compile(
    r"git clone https://github\.com/SatoryKono/BioactivityDataAcquisition2\.git"
)
CANONICAL_SLUG = "SatoryKono/BioactivityDataAcquisition"
CANONICAL_URL = "https://github.com/SatoryKono/BioactivityDataAcquisition"


def _is_generated_docs_artifact(path: Path, docs_root: Path = DOCS_ROOT) -> bool:
    return is_generated_docs_artifact(path, docs_root=docs_root)


def _iter_active_docs_markdown() -> list[Path]:
    docs_markdown_files = sorted(DOCS_ROOT.rglob("*.md"))
    return sorted(
        path
        for path in docs_markdown_files
        if ACTIVE_DOC_EXCLUDED_PARTS.isdisjoint(path.parts)
        and not _is_generated_docs_artifact(path, DOCS_ROOT)
    )


def _candidate_paths() -> list[Path]:
    candidates = [ROOT / "README.md"]
    candidates.extend(_iter_active_docs_markdown())
    candidates.extend(sorted(WORKFLOWS_ROOT.glob("*.yml")))
    candidates.extend(sorted(WORKFLOWS_ROOT.glob("*.yaml")))
    return sorted(set(candidates))


def _normalize_text(text: str) -> str:
    text = LEGACY_CLONE_RE.sub(f"git clone {CANONICAL_URL}.git", text)
    text = LEGACY_URL_RE.sub(CANONICAL_URL, text)
    text = LEGACY_SLUG_RE.sub(CANONICAL_SLUG, text)
    return text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync or validate active docs/workflows against the canonical repo slug."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Rewrite mismatched files.")
    mode.add_argument("--check", action="store_true", help="Fail if mismatches are found.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    write_mode = args.write or not args.check
    changed: list[str] = []

    for path in _candidate_paths():
        original = path.read_text(encoding="utf-8")
        normalized = _normalize_text(original)
        if normalized == original:
            continue
        changed.append(path.relative_to(ROOT).as_posix())
        if write_mode:
            path.write_text(normalized, encoding="utf-8")

    if changed:
        action = "rewrote" if write_mode else "would rewrite"
        for item in changed:
            print(f"[sync-repo-identity] {action}: {item}")
        return 0 if write_mode else 1

    print("[sync-repo-identity] repo identity is already synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
