"""Shared repository and docs path helpers for docs tooling."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = PROJECT_ROOT / "docs"
MKDOCS_FILE = PROJECT_ROOT / "mkdocs.yml"
WORKFLOWS_ROOT = PROJECT_ROOT / ".github" / "workflows"

GENERATED_EXPORT_MERGED_RE = re.compile(r"^exports/.+\.merged\.md$")
GENERATED_DOCS_EXPORT_REPORT_RE = re.compile(
    r"^reports/docs-export-report-\d{4}-\d{2}-\d{2}-\d{6}\.md$"
)


def is_generated_docs_artifact(path: Path, docs_root: Path = DOCS_DIR) -> bool:
    """Return True when a docs path points to a generated artifact."""
    rel_path = path.relative_to(docs_root).as_posix()
    rel_parts = Path(rel_path).parts
    if rel_parts and rel_parts[0] == "site":
        return True
    if GENERATED_EXPORT_MERGED_RE.match(rel_path):
        return True
    return bool(GENERATED_DOCS_EXPORT_REPORT_RE.match(rel_path))
