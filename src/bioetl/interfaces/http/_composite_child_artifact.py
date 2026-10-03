"""Resolve composite child evidence within the selected report catalog."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)


def _child_path(
    root: Path, reference: str, item: Mapping[str, object]
) -> tuple[Path | None, str]:
    """Rebase portable/legacy references without trusting their external prefix."""
    pipeline, run_id = item.get("pipeline_name"), item.get("run_id")
    if any(
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or any(char in value for char in "/\\:")
        for value in (pipeline, run_id)
    ):
        return None, "artifact_record_invalid"
    parts = PurePosixPath(reference.replace("\\", "/")).parts
    if ".." in parts:
        return None, "artifact_path_escape"
    suffix = ("pipeline", str(pipeline), str(run_id), "pipeline-run-report.json")
    if tuple(parts[-4:]) != suffix or root.parent.parent.name != "pipeline":
        return None, "artifact_record_invalid"
    catalog = root.parent.parent.resolve()
    candidate = (catalog / str(pipeline) / str(run_id) / suffix[-1]).resolve()
    if not candidate.is_relative_to(catalog):
        return None, "artifact_path_escape"
    return candidate, ""


def probe_child_artifact(
    root: Path, reference: str, item: Mapping[str, object]
) -> tuple[str, str]:
    """Verify child identity and digest, or its immutable legacy snapshot/revision."""
    # Reuse the exact-run reader rather than treating mere file existence as proof.
    from bioetl.interfaces.http._selected_run_report_assessment import (
        _load_report_assessment,
    )

    candidate, error = _child_path(root, reference, item)
    if error or candidate is None:
        return "fail", error
    if not candidate.is_file():
        return "fail", "artifact_missing"
    try:
        report, identity, _, availability, _ = _load_report_assessment(
            candidate, str(item["pipeline_name"]), str(item["run_id"])
        )
        if (
            item.get("manifest_id") is not None
            and identity.get("manifest_id") != item["manifest_id"]
        ):
            return "fail", "artifact_record_invalid"
        digest = item.get("sha256") or item.get("digest") or item.get("content_hash")
        if isinstance(digest, str) and digest.strip():
            if canonical_report_sha256(report) != digest.strip().lower():
                return "fail", "digest_mismatch"
            return "pass", "digest_matches"
        if availability == "AVAILABLE":
            return "pass", "snapshot_verified"
        return "unknown", "digest_not_recorded"
    except FileNotFoundError:
        return "fail", "artifact_missing"
    except (OSError, ValueError, TypeError, LookupError):
        return "fail", "artifact_record_invalid"
