"""Verify captured composite child reports without relaxing evidence checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path


def _probe_composite_child(
    item: Mapping[str, object], root: Path, hash_artifact: Callable[[Path], str]
) -> str:
    """Verify a child only at its exact identity-bound path in this report tree."""
    from bioetl.interfaces.http._selected_run_report_assessment import (
        _load_report_assessment,
    )

    pipeline, run_id = item.get("pipeline_name"), item.get("run_id")
    if not all(
        isinstance(value, str)
        and value not in {"", ".", ".."}
        and all(c.isalnum() or c in "._-" for c in value)
        for value in (pipeline, run_id)
    ):
        return "child_identity_invalid"
    raw = item.get("ref")
    if not isinstance(raw, str):
        return "artifact_path_escape"
    reference = Path(raw)
    if reference.is_absolute():
        tree = root.parents[1]
        candidate = (
            tree / str(pipeline) / str(run_id) / "pipeline-run-report.json"
        ).resolve()
        if reference.resolve() != candidate or not candidate.is_relative_to(tree):
            return "artifact_path_escape"
    else:
        candidate = (root / reference).resolve()
        if (
            len(reference.parts) != 2
            or reference.parts[0] != "child-reports"
            or not candidate.is_relative_to(root / "child-reports")
        ):
            return "artifact_path_escape"
    if not candidate.is_file():
        return "artifact_missing"
    digest = item.get("sha256")
    if not isinstance(digest, str) or hash_artifact(candidate) != digest:
        return "child_digest_mismatch"
    try:
        _report, identity, assessment, availability, _revision = (
            _load_report_assessment(candidate, str(pipeline), str(run_id))
        )
    except (OSError, ValueError, TypeError, LookupError):
        return "child_evidence_invalid"
    if identity.get("manifest_id") != item.get("manifest_id"):
        return "child_manifest_mismatch"
    if (
        availability != "AVAILABLE"
        or identity.get("status") != "success"
        or assessment.get("verdict") not in {"OK", "N/A"}
        or assessment.get("evidence_completeness") != "COMPLETE"
    ):
        return "child_evidence_not_green"
    return ""
