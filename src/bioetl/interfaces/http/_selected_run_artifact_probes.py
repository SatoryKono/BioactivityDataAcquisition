"""Artifact probe helpers for the exact-run persisted assessment projection."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

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
