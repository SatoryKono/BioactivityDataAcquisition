"""Validate and publish the immutable reports of an isolated campaign attempt."""

from __future__ import annotations

import hashlib
import json
import re
from tempfile import TemporaryDirectory
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationRegisterOutcome,
    decide_register_outcome,
)
from bioetl.domain.run_reports.selected_status import verify_snapshot
from bioetl.infrastructure.control_plane.evidence_location_publish import (
    publish_bytes_if_absent,
    read_existing_bytes,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)


@dataclass(frozen=True, order=True)
class RunReport:
    kind: str
    owner: str
    run_id: str

    def __post_init__(self) -> None:
        if self.kind not in {"pipeline", "workflow"} or not all(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value)
            for value in (self.owner, self.run_id)
        ):
            raise ValueError(f"Invalid report identity: {self}")

    @property
    def directory(self) -> Path:
        return Path(self.kind, self.owner, self.run_id)

    @property
    def commit_file(self) -> Path:
        return self.directory / f"{self.kind}-run-report.json"

    @property
    def label(self) -> str:
        return f"{self.kind}/{self.owner}/{self.run_id}"


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def collect_reports(source: Path, *, kind: str, owner: str) -> dict[RunReport, dict]:
    """Select committed reports by identity and check parent/child coverage."""
    reports = {}
    for report_kind, fields in (
        ("pipeline", ("pipeline_name", "run_id")),
        ("workflow", ("workflow_name", "workflow_run_id")),
    ):
        for path in sorted(
            source.glob(f"{report_kind}/*/*/{report_kind}-run-report.json")
        ):
            run = RunReport(report_kind, path.parent.parent.name, path.parent.name)
            _check_source_path(path, source)
            payload = read_json(path)
            identity = payload.get("identity", {})
            versions = (1, 2) if report_kind == "pipeline" else (1,)
            if tuple(identity.get(field) for field in fields) != (
                run.owner,
                run.run_id,
            ) or payload.get("schema_version") not in {
                f"{report_kind}_run_report_v{version}" for version in versions
            }:
                raise ValueError(f"Report identity or schema mismatch: {run.label}")
            reports[run] = payload
    roots = [run for run in reports if (run.kind, run.owner) == (kind, owner)]
    if len(roots) != 1 or reports[roots[0]]["identity"].get("status") != "success":
        raise ValueError(f"Expected one successful committed {kind} report for {owner}")
    for run, payload in reports.items():
        if run.kind == "workflow":
            _check_children(run, payload, reports)
    return reports


def _check_children(
    parent: RunReport, payload: dict, reports: dict[RunReport, dict]
) -> None:
    for step in payload["execution"]:
        if step.get("kind") != "pipeline" or not (
            step.get("status") == "success" or step.get("pipeline_run_id")
        ):
            continue
        child = RunReport(
            "pipeline",
            step.get("pipeline_name") or "",
            step.get("pipeline_run_id") or "",
        )
        identity = reports.get(child, {}).get("identity", {})
        if identity.get("workflow_run_id") != parent.run_id:
            raise ValueError(
                f"Missing or unbound child report: {child.label} for {parent.label}"
            )


def _check_source_path(path: Path, root: Path) -> None:
    if path.resolve() != path or not path.is_relative_to(root):
        raise ValueError(f"Report path escapes staging or traverses a link: {path}")


def _report_files(source: Path, run: RunReport, payload: dict) -> dict[Path, bytes]:
    directory = source / run.directory
    markdown = run.commit_file.with_suffix(".md")
    paths = [markdown] if (source / markdown).exists() else []
    revisions = directory / "status-revisions"
    paths.extend(path.relative_to(source) for path in sorted(revisions.glob("*.json")))
    files = {}
    for path in (*paths, run.commit_file):
        _check_source_path(source / path, source)
        files[path] = (source / path).read_bytes()
    if run.kind == "pipeline" and payload["schema_version"] == "pipeline_run_report_v2":
        _verify_committed_revision(run, payload.get("selected_run_snapshot"), files)
    for artifact in payload.get("artifacts", []):
        if artifact.get("kind") == "pipeline_run_report_md" and (
            markdown not in files
            or hashlib.sha256(files[markdown]).hexdigest() != artifact.get("sha256")
        ):
            raise ValueError(
                f"Referenced Markdown report is missing or corrupt: {run.label}"
            )
    if json.loads(files[run.commit_file]) != payload:
        raise ValueError(f"Report changed during publication: {run.label}")
    return files


def _verify_committed_revision(
    run: RunReport, snapshot: object, files: dict[Path, bytes]
) -> None:
    if not isinstance(snapshot, dict) or not verify_snapshot(snapshot):
        raise ValueError(f"Invalid committed status snapshot: {run.label}")
    revision = snapshot["revision"]
    expected = run.directory / "status-revisions" / f"{revision}.json"
    if expected not in files:
        raise ValueError(f"Committed status revision missing: {run.label}")
    if json.loads(files[expected]) != snapshot:
        raise ValueError(f"Committed status revision differs: {run.label}")


def _verify_existing(target: Path, files: dict[Path, bytes]) -> None:
    for relative, content in files.items():
        path = target / relative
        existing = read_existing_bytes(path, trusted_base=target)
        if existing != content:
            raise ValueError(f"Published report conflicts at {relative.as_posix()}")


def _publish_directory(target: Path, run: RunReport, files: dict[Path, bytes]) -> None:
    destination = target / run.directory
    if destination.resolve() != destination:
        raise ValueError(f"Dashboard report path traverses a link: {run.label}")
    if destination.exists():
        _verify_existing(target, files)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage outside the pipeline/workflow index and on the destination volume.
    with TemporaryDirectory(prefix=".campaign-publication-", dir=target) as temporary:
        staging = Path(temporary) / run.run_id
        for relative, content in files.items():
            if not publish_bytes_if_absent(
                staging / relative.relative_to(run.directory),
                content,
                trusted_base=Path(temporary),
            ):
                raise RuntimeError(f"Duplicate staged report artifact: {relative}")
        try:
            staging.rename(destination)
        except OSError:
            if not destination.is_dir():
                raise
            _verify_existing(target, files)


def publish_reports(
    source: Path,
    target: Path,
    reports: dict[RunReport, dict],
    *,
    source_id: str,
    relative_data_root: str,
) -> None:
    """Publish dependency files and locators before the commit JSON of each run."""
    if source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("Staging and dashboard report roots must be disjoint")
    source_locations = FileEvidenceLocationStore(source)
    target_locations = FileEvidenceLocationStore(target)
    prepared = []
    for run, payload in sorted(reports.items()):
        location = source_locations.get(
            kind=run.kind, owner=run.owner, run_id=run.run_id
        )
        expected_workflow = (
            payload["identity"].get("workflow_run_id")
            if run.kind == "pipeline"
            else None
        )
        if (
            location is None
            or location.runtime_source_id != source_id
            or location.root_alias != DEFAULT_EVIDENCE_ROOT_ALIAS
            or location.relative_data_root != relative_data_root
            or location.workflow_run_id != expected_workflow
        ):
            raise ValueError(
                f"Evidence location does not bind to dashboard data: {run.label}"
            )
        existing = target_locations.get(
            kind=run.kind, owner=run.owner, run_id=run.run_id
        )
        decision = decide_register_outcome(candidate=location, existing=existing)
        if decision.outcome is EvidenceLocationRegisterOutcome.CONFLICT:
            raise ValueError(f"Published report locator conflicts: {run.label}")
        files = _report_files(source, run, payload)
        if (target / run.directory).exists():
            _verify_existing(target, files)
        prepared.append((run, location, files))
    for run, location, files in prepared:
        target_locations.register(location)
        _publish_directory(target, run, files)
