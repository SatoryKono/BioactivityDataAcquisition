"""Shared loader for committed reports/quality artifacts (S6 / #9602)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUALITY_ROOT = PROJECT_ROOT / "reports" / "quality"
MANIFEST_NAME = "source-tree-manifest.json"


def quality_artifact_path(*parts: str) -> Path:
    """Return a path under ``reports/quality``."""
    return QUALITY_ROOT.joinpath(*parts)


def load_source_tree_manifest() -> dict[str, Any]:
    """Load the unified source-tree manifest."""
    payload = json.loads(
        quality_artifact_path(MANIFEST_NAME).read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise TypeError("source-tree-manifest.json must be an object")
    return payload


REVIEWED_MAINTENANCE_CLI_SEAM = (
    "src/bioetl/interfaces/cli/commands/domains/maintenance/service_access.py"
)
MAINTENANCE_API_PATH = "src/bioetl/composition/maintenance_api.py"


def assert_retained_entrypoint_src_importers(entry: dict[str, Any]) -> None:
    """Allow the reviewed maintenance CLI seam; keep other retained facades at zero."""
    path = str(entry["path"])
    if path == MAINTENANCE_API_PATH:
        assert int(entry["src_importer_count"]) == 1
        assert list(entry.get("src_importers") or []) == [REVIEWED_MAINTENANCE_CLI_SEAM]
        return
    assert int(entry["src_importer_count"]) == 0


def load_quality_json(*parts: str) -> Any:
    """Load a committed quality JSON artifact.

    When the payload pins ``source_tree_sha256``, it must match the manifest.
    """
    path = quality_artifact_path(*parts)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "source_tree_sha256" in payload:
        manifest = load_source_tree_manifest()
        pinned = payload.get("source_tree_sha256")
        canonical = manifest.get("source_tree_sha256")
        if pinned != canonical and path.name != MANIFEST_NAME:
            raise AssertionError(
                f"{path.as_posix()} source_tree_sha256={pinned!r} "
                f"does not match manifest {canonical!r}"
            )
    return payload
