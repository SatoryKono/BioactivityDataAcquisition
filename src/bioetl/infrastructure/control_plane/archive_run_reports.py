"""Include selected-run reports and revisions in the existing local archive pack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.run_reports.selected_status import evidence_digest, verify_snapshot


def _identity_matches(identity: object, manifest: RunManifest) -> bool:
    """Legacy identity may omit manifest_id; present values must bind exactly."""
    if not isinstance(identity, dict):
        return False
    return (
        identity.get("run_id") == str(manifest.run_id)
        and identity.get("pipeline_name") == manifest.pipeline_name
        and (
            identity.get("manifest_id") is None
            or identity["manifest_id"] == str(manifest.manifest_id)
        )
    )


def _load_report(path: Path, manifest: RunManifest) -> dict[str, object]:
    """Read a JSON report only when its identity matches the archive manifest."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("archive_report_corrupt")
    identity = payload.get("identity", {})
    if not _identity_matches(identity, manifest):
        raise ValueError("archive_report_identity_mismatch")
    return payload


def _revision_sources(payload: dict[str, object], revisions: Path) -> list[Path]:
    """Require a valid committed revision before including its history."""
    snapshot = payload.get("selected_run_snapshot")
    if snapshot is None:
        return []
    if not isinstance(snapshot, dict) or not verify_snapshot(snapshot):
        raise ValueError("archive_report_snapshot_corrupt")
    evidence = {
        key: value for key, value in payload.items() if key != "selected_run_snapshot"
    }
    if snapshot.get("evidence") != evidence:
        raise ValueError("archive_report_evidence_mismatch")
    committed = revisions / f"{snapshot['revision']}.json"
    if not committed.is_file():
        raise ValueError("archive_report_revision_missing")
    if json.loads(committed.read_text(encoding="utf-8")) != snapshot:
        raise ValueError("archive_report_revision_mismatch")
    return sorted(revisions.glob("*.json"))


def _validate_source(
    item: Path, base: Path, revisions: Path, manifest: RunManifest
) -> None:
    """Reject escaped paths and corrupt historical revisions before archiving."""
    if (
        item.is_symlink()
        or item.parent.is_symlink()
        or not item.resolve().is_relative_to(base)
    ):
        raise ValueError("archive_report_symlink_rejected")
    if item.parent == revisions:
        revision = json.loads(item.read_text(encoding="utf-8"))
        if (
            not isinstance(revision, dict)
            or not verify_snapshot(revision)
            or item.stem != revision.get("revision")
        ):
            raise ValueError("archive_report_revision_corrupt")
        evidence = revision["evidence"]
        identity = evidence.get("identity", {})
        if not _identity_matches(identity, manifest):
            raise ValueError("archive_revision_identity_mismatch")


def selected_report_sources(
    root: Path | None, manifest: RunManifest
) -> dict[str, Path]:
    """Enumerate only an exact, identity-checked report and its immutable revisions."""
    if root is None:
        return {}
    base = root.resolve()
    folder = base / "pipeline" / manifest.pipeline_name / str(manifest.run_id)
    if not folder.resolve().is_relative_to(base):
        raise ValueError("archive_report_outside_root")
    path = folder / "pipeline-run-report.json"
    if not path.is_file():
        return {}
    payload = _load_report(path, manifest)
    revisions = folder / "status-revisions"
    markdown_path = folder / "pipeline-run-report.md"
    files = [
        path,
        *([markdown_path] if markdown_path.is_file() else []),
        *_revision_sources(payload, revisions),
        *_child_report_sources(payload, folder),
    ]
    result = {}
    for item in files:
        _validate_source(item, base, revisions, manifest)
        result[f"run-reports/{item.relative_to(base).as_posix()}"] = item
    return result


def _child_report_sources(payload: dict[str, object], folder: Path) -> list[Path]:
    """Keep the parent's captured child reports inside its verified archive."""
    artifacts = payload.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("archive_report_artifacts_corrupt")
    result = []
    for artifact in artifacts:
        if (
            not isinstance(artifact, dict)
            or artifact.get("kind") != "composite_child_run_report"
        ):
            continue
        raw_ref = str(artifact.get("ref", ""))
        if "canonical_sha256" not in artifact and not raw_ref.replace(
            "\\", "/"
        ).startswith("child-reports/"):
            # Legacy references are verified separately and were never parent-owned.
            continue
        relative = Path(raw_ref)
        item = folder / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not item.resolve().is_relative_to(folder.resolve())
        ):
            raise ValueError("archive_child_report_outside_root")
        raw = item.read_bytes()
        if hashlib.sha256(raw).hexdigest() != artifact.get("sha256"):
            raise ValueError("archive_child_report_checksum_mismatch")
        child = json.loads(raw)
        identity = child.get("identity", {})
        if any(
            identity.get(key) != artifact.get(key)
            for key in ("run_id", "pipeline_name", "manifest_id")
        ):
            raise ValueError("archive_child_report_identity_mismatch")
        result.append(item)
        result.extend(_revision_sources(child, item.parent / "status-revisions"))
    return result


def selected_report_archive_key(root: Path | None, manifest: RunManifest) -> str:
    """Version the archive by the complete validated report/revision inventory."""
    sources = selected_report_sources(root, manifest)
    if not sources:
        return ""
    digests = {}
    for relative, path in sources.items():
        with path.open("rb") as stream:
            digests[relative] = hashlib.file_digest(stream, "sha256").hexdigest()
    return evidence_digest(digests)
