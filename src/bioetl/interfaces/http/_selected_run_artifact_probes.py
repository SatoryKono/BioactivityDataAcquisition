"""Artifact probe helpers for the exact-run persisted assessment projection."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
from bioetl.interfaces.http._forensic_request_budget import (
    _deadline_exceeded_error,
    request_deadline_exceeded,
)

_SELF_REPORT_KINDS = frozenset(
    {
        "pipeline_run_report_json",
        "pipeline_run_report_md",
        "workflow_run_report_json",
        "workflow_run_report_md",
    }
)
_SELF_REPORT_FILENAMES = {
    "pipeline_run_report_json": "pipeline-run-report.json",
    "pipeline_run_report_md": "pipeline-run-report.md",
    "workflow_run_report_json": "workflow-run-report.json",
    "workflow_run_report_md": "workflow-run-report.md",
}
_JSON_SELF_REPORT_KINDS = frozenset(
    {"pipeline_run_report_json", "workflow_run_report_json"}
)
_LAYER_KINDS = frozenset({"bronze_batch", "bronze", "silver", "gold"})


def _resolve_artifact_path(
    root: Path, relative: str, kind: str
) -> tuple[Path | None, str]:
    """Locate an artifact without joining a repo-relative ref onto the run directory."""
    filename = _SELF_REPORT_FILENAMES.get(kind)
    if filename is not None:
        canonical = (root / filename).resolve()
        if canonical.is_file() and canonical.is_relative_to(root):
            return canonical, ""
    raw = Path(relative)
    if raw.is_absolute():
        candidate = raw.resolve()
        if kind in _LAYER_KINDS and candidate.is_file():
            return candidate, ""
        if not candidate.is_relative_to(root):
            return None, "artifact_path_escape"
        return candidate, ""
    if len(raw.parts) == 1:
        candidate = (root / raw.name).resolve()
        if not candidate.is_relative_to(root):
            return None, "artifact_path_escape"
        return candidate, ""
    if kind in _SELF_REPORT_KINDS:
        return None, "artifact_missing"
    candidate = (root / raw).resolve()
    if not candidate.is_relative_to(root):
        return None, "artifact_path_escape"
    return candidate, ""


_HASH_READ_CHUNK_SIZE = 256 * 1024


def _probe_digest(candidate: Path, kind: str) -> str:
    """Hash JSON self-reports canonically; other artifacts as raw bytes."""
    if kind in _JSON_SELF_REPORT_KINDS:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return canonical_report_sha256(payload)
    return _hash_artifact_chunked(candidate)


def _hash_artifact_chunked(candidate: Path) -> str:
    """Hash one artifact in blocks, stopping new work after the deadline."""
    digest = hashlib.sha256()
    with candidate.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_HASH_READ_CHUNK_SIZE), b""):
            if request_deadline_exceeded():
                raise _deadline_exceeded_error()
            digest.update(chunk)
    return digest.hexdigest()


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


def _artifact_probes(
    report: Mapping[str, object], run_root: Path
) -> tuple[list[Mapping[str, object]], bool]:
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return [], False
    root = run_root.resolve()
    probes: list[Mapping[str, object]] = []
    for index, item in enumerate(artifacts):
        ref = f"#/artifacts/{index}"
        code = f"artifact_{index}"
        if not isinstance(item, dict):
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": "artifact_record_invalid",
                    "evidence_ref": ref,
                }
            )
            continue
        name = item.get("name") or item.get("id") or item.get("kind") or code
        code = str(name)
        relative = item.get("path") or item.get("relative_path") or item.get("ref")
        digest = item.get("sha256") or item.get("digest") or item.get("content_hash")
        if not isinstance(relative, str) or not relative.strip():
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": "hash_without_object"
                    if digest
                    else "artifact_path_missing",
                    "evidence_ref": ref,
                }
            )
            continue
        kind = str(item.get("kind") or "")
        if kind == "composite_child_run_report":
            result, reason = probe_child_artifact(root, relative, item)
            probes.append(
                {"code": code, "result": result, "reason": reason, "evidence_ref": ref}
            )
            continue
        candidate, resolve_error = _resolve_artifact_path(root, relative, kind or code)
        if resolve_error or candidate is None or not candidate.is_file():
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": resolve_error or "artifact_missing",
                    "evidence_ref": ref,
                }
            )
            continue
        if not isinstance(digest, str) or not digest.strip():
            if code in _SELF_REPORT_KINDS or kind in _SELF_REPORT_KINDS:
                probes.append(
                    {
                        "code": code,
                        "result": "pass",
                        "reason": "object_available",
                        "evidence_ref": ref,
                    }
                )
                continue
            probes.append(
                {
                    "code": code,
                    "result": "unknown",
                    "reason": "digest_not_recorded",
                    "evidence_ref": ref,
                }
            )
            continue
        actual = _probe_digest(candidate, kind)
        if actual != digest.strip().lower():
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": "digest_mismatch",
                    "evidence_ref": ref,
                }
            )
            continue
        probes.append(
            {
                "code": code,
                "result": "pass",
                "reason": "digest_matches",
                "evidence_ref": ref,
            }
        )
    return probes, True
