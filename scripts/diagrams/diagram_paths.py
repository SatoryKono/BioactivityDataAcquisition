#!/usr/bin/env python3
"""Shared path helpers for BioETL diagram tooling.

These helpers intentionally auto-detect the active diagram root so the same
toolchain can work before and after the `mmd-diagrams -> diagrams` migration.
"""

from __future__ import annotations

from pathlib import Path


def resolve_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[0]


REPO_ROOT = resolve_repo_root()
ARCHITECTURE_DOCS_ROOT = REPO_ROOT / "docs" / "02-architecture"


def resolve_diagram_root() -> Path:
    for candidate_name in ("diagrams", "mmd-diagrams"):
        candidate = ARCHITECTURE_DOCS_ROOT / candidate_name
        if candidate.exists():
            return candidate
    return ARCHITECTURE_DOCS_ROOT / "mmd-diagrams"


DIAGRAM_ROOT = resolve_diagram_root()
DIAGRAM_ROOT_BASENAME = DIAGRAM_ROOT.name
DIAGRAM_THEME_DIR = DIAGRAM_ROOT / "theme"
QUALITY_GATE_MANIFEST = DIAGRAM_ROOT / "quality-gate-manifest.txt"
VISUAL_SMOKE_MANIFEST = DIAGRAM_ROOT / "visual-smoke-manifest.txt"

SOURCE_FAMILIES = ("architecture", "class-diagrams", "foundation", "views")

_BUNDLE_BASENAMES = {
    "architecture": "architecture-diagrams-with-descriptions",
    "class-diagrams": "class-diagrams-with-descriptions",
    "foundation": "foundation-diagrams-with-descriptions",
    "views": "views-diagrams-with-descriptions",
}


def source_dir(family: str) -> Path:
    return DIAGRAM_ROOT / family


def render_dir(family: str, kind: str) -> Path:
    return source_dir(family) / kind


def bundle_markdown_path(collection: str) -> Path:
    return DIAGRAM_ROOT / f"{_BUNDLE_BASENAMES[collection]}.md"


def bundle_output_path(collection: str, suffix: str) -> Path:
    return DIAGRAM_ROOT / f"{_BUNDLE_BASENAMES[collection]}{suffix}"


def source_ref(family: str, filename: str) -> str:
    return f"{DIAGRAM_ROOT_BASENAME}/{family}/{filename}"

