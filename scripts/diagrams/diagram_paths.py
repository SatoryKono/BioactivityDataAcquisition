#!/usr/bin/env python3
"""Shared path helpers for BioETL diagram tooling.

These helpers intentionally auto-detect the active diagram root so the same
toolchain can work before and after the `mmd-diagrams -> diagrams` migration.
They also support the staged internal layout migration:

- `docs/` -> `governance/`
- root `render.sh`/`svgo.config.js` -> `tooling/`
- root manifests -> `manifests/`
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_repo_root
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    SCRIPT_DIR = Path(__file__).resolve().parent
    REPO_CANDIDATE = SCRIPT_DIR.parents[1]
    if str(REPO_CANDIDATE) not in sys.path:
        sys.path.insert(0, str(REPO_CANDIDATE))
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_repo_root

ARCHITECTURE_DOCS_ROOT = REPO_ROOT / "docs" / "02-architecture"


def resolve_diagram_root() -> Path:
    for candidate_name in ("diagrams", "mmd-diagrams"):
        candidate = ARCHITECTURE_DOCS_ROOT / candidate_name
        if candidate.exists():
            return candidate
    return ARCHITECTURE_DOCS_ROOT / "mmd-diagrams"


def _resolve_first_existing(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


DIAGRAM_ROOT = resolve_diagram_root()
DIAGRAM_ROOT_BASENAME = DIAGRAM_ROOT.name
DIAGRAM_THEME_DIR = DIAGRAM_ROOT / "theme"
DIAGRAM_GOVERNANCE_DIR = _resolve_first_existing(
    DIAGRAM_ROOT / "governance",
    DIAGRAM_ROOT / "docs",
)
DIAGRAM_TOOLING_DIR = _resolve_first_existing(
    DIAGRAM_ROOT / "tooling",
    DIAGRAM_ROOT,
)
DIAGRAM_RENDER_SCRIPT = _resolve_first_existing(
    DIAGRAM_TOOLING_DIR / "render.sh",
    DIAGRAM_ROOT / "render.sh",
)
DIAGRAM_SVGO_CONFIG = _resolve_first_existing(
    DIAGRAM_TOOLING_DIR / "svgo.config.js",
    DIAGRAM_ROOT / "svgo.config.js",
)
DIAGRAM_MANIFESTS_DIR = _resolve_first_existing(
    DIAGRAM_ROOT / "manifests",
    DIAGRAM_ROOT,
)
QUALITY_GATE_MANIFEST = _resolve_first_existing(
    DIAGRAM_MANIFESTS_DIR / "quality-gates.txt",
    DIAGRAM_ROOT / "manifests/quality-gates.txt",
)
VISUAL_SMOKE_MANIFEST = _resolve_first_existing(
    DIAGRAM_MANIFESTS_DIR / "visual-smoke.txt",
    DIAGRAM_ROOT / "manifests/visual-smoke.txt",
)
PNG_COMPATIBILITY_MANIFEST = _resolve_first_existing(
    DIAGRAM_MANIFESTS_DIR / "png-compatibility.txt",
    DIAGRAM_ROOT / "manifests/png-compatibility.txt",
)

SOURCE_FAMILIES = ("architecture", "class-diagrams", "foundation", "views")

DIAGRAM_BUNDLES_DIR = DIAGRAM_ROOT / "bundles"

_LEGACY_BUNDLE_BASENAMES = {
    "architecture": "architecture-diagrams-with-descriptions",
    "class-diagrams": "class-diagrams-with-descriptions",
    "foundation": "foundation-diagrams-with-descriptions",
    "views": "views-diagrams-with-descriptions",
}

_BUNDLE_STUBS = {
    "architecture": "architecture.bundle",
    "class-diagrams": "class.bundle",
    "foundation": "foundation.bundle",
    "views": "views.bundle",
}


def source_dir(family: str) -> Path:
    return DIAGRAM_ROOT / family


def render_dir(family: str, kind: str) -> Path:
    return source_dir(family) / kind


def bundle_markdown_path(collection: str) -> Path:
    if DIAGRAM_BUNDLES_DIR.exists():
        return DIAGRAM_BUNDLES_DIR / f"{_BUNDLE_STUBS[collection]}.md"
    return DIAGRAM_ROOT / f"{_LEGACY_BUNDLE_BASENAMES[collection]}.md"


def bundle_output_path(collection: str, suffix: str) -> Path:
    if DIAGRAM_BUNDLES_DIR.exists():
        return DIAGRAM_BUNDLES_DIR / f"{_BUNDLE_STUBS[collection]}{suffix}"
    return DIAGRAM_ROOT / f"{_LEGACY_BUNDLE_BASENAMES[collection]}{suffix}"


def source_ref(family: str, filename: str) -> str:
    return f"{DIAGRAM_ROOT_BASENAME}/{family}/{filename}"
