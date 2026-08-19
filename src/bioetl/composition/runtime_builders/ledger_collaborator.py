"""Ledger collaborator attachment for control-plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )


class PipelineRunnerProtocol(Protocol):
    """Minimal runner contract required for ledger collaborator attachment."""

    services: object

    def attach_run_ledger_service(self, service: RunLedgerService) -> None:
        """Attach the run-ledger collaborator."""
        ...


@dataclass(frozen=True, slots=True)
class ArtifactRecorderAttachmentResult:
    """Bounded recorder attachment summary for strict control-plane validation."""

    candidate_count: int
    attached_count: int
    missing_attach_method_count: int
    failed_count: int


def _empty_attachment_result() -> ArtifactRecorderAttachmentResult:
    return ArtifactRecorderAttachmentResult(
        candidate_count=0,
        attached_count=0,
        missing_attach_method_count=0,
        failed_count=0,
    )


def _record_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> object:
    """Record one published artifact in the control-plane ledger."""
    dataset_ref = None
    lineage_fragment_id = None
    if details is not None:
        raw_dataset_ref = details.get("dataset_ref")
        raw_lineage_fragment_id = details.get("lineage_fragment_id")
        dataset_ref = None if raw_dataset_ref is None else str(raw_dataset_ref)
        lineage_fragment_id = (
            None if raw_lineage_fragment_id is None else str(raw_lineage_fragment_id)
        )
        artifact_content_hash = str(
            details.get("artifact_content_hash") or details.get("content_hash") or ""
        )
    else:
        artifact_content_hash = ""
    entry = service.record_artifact_published(
        layer=layer,
        artifact_path=artifact_path,
        artifact_content_hash=artifact_content_hash,
        dataset_ref=dataset_ref,
        lineage_fragment_id=lineage_fragment_id,
        details=details,
    )
    _record_input_snapshots_from_artifact(
        service,
        layer=layer,
        artifact_path=artifact_path,
        details=details,
    )
    return entry


def _record_input_snapshots_from_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> None:
    """Record immutable input snapshots published with Bronze metadata."""
    if layer != "bronze" or not details:
        return
    raw_snapshots = details.get("input_snapshots")
    if not isinstance(raw_snapshots, list):
        return
    for snapshot in raw_snapshots:
        if not isinstance(snapshot, dict):
            continue
        immutable_uri = snapshot.get("immutable_uri")
        if immutable_uri is None:
            continue
        service.record_input_snapshot_published(
            provider=str(details.get("provider") or ""),
            entity=str(details.get("entity") or ""),
            pipeline_name=str(details.get("pipeline_name") or ""),
            snapshot_id=str(snapshot.get("snapshot_id") or ""),
            content_hash=str(snapshot.get("content_hash") or ""),
            immutable_uri=str(immutable_uri),
            bronze_batch_ref=artifact_path,
            query_fingerprint=(
                None
                if snapshot.get("query_fingerprint") is None
                else str(snapshot.get("query_fingerprint"))
            ),
            details={
                key: value
                for key, value in snapshot.items()
                if key not in {"snapshot_id", "content_hash", "immutable_uri"}
            },
        )


def _attach_artifact_recorder(
    target: object,
    service: RunLedgerService,
) -> bool:
    """Attach an artifact-recorder callback to one metadata writer when supported."""
    attach = getattr(target, "attach_artifact_recorder", None)
    if not callable(attach):
        return False
    attach(
        lambda layer, artifact_path, details=None: _record_artifact(
            service,
            layer=layer,
            artifact_path=artifact_path,
            details=details,
        )
    )
    return True


from bioetl.composition.runtime_builders._ledger_metadata_candidates import (
    _collect_metadata_writer_candidates,
    _iter_unique_candidates,
)

def _attach_candidate_artifact_recorder(
    candidate: object,
    run_ledger_service: RunLedgerService,
) -> str:
    attach = getattr(candidate, "attach_artifact_recorder", None)
    if not callable(attach):
        return "missing"
    try:
        return (
            "attached"
            if _attach_artifact_recorder(candidate, run_ledger_service)
            else "missing"
        )
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return "failed"


def _attach_contract_evidence_recorder(
    runner: PipelineRunnerProtocol,
    run_ledger_service: RunLedgerService,
) -> None:
    attach = getattr(runner, "attach_contract_evidence_recorder", None)
    if not callable(attach):
        return
    ledger_port = getattr(run_ledger_service, "ledger_port", None)
    base_path = getattr(ledger_port, "base_path", None)
    if base_path is None:
        return
    from pathlib import Path

    from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
        FileContractEvidenceRecorder,
    )

    manifest_root = Path(base_path).parent / "run_manifest"
    attach(FileContractEvidenceRecorder(base_path=manifest_root))


def attach_control_plane_collaborators(
    runner: PipelineRunnerProtocol,
    run_ledger_service: RunLedgerService,
) -> ArtifactRecorderAttachmentResult:
    """Attach ledger collaborators to the runner and its metadata writers."""
    runner.attach_run_ledger_service(run_ledger_service)
    _attach_contract_evidence_recorder(runner, run_ledger_service)

    services = getattr(runner, "services", None)
    if services is None:
        return _empty_attachment_result()

    unique_candidates = _iter_unique_candidates(
        _collect_metadata_writer_candidates(services)
    )
    attached_count = 0
    missing_attach_method_count = 0
    failed_count = 0
    for candidate in unique_candidates:
        outcome = _attach_candidate_artifact_recorder(candidate, run_ledger_service)
        if outcome == "attached":
            attached_count += 1
        elif outcome == "missing":
            missing_attach_method_count += 1
        else:
            failed_count += 1
    return ArtifactRecorderAttachmentResult(
        candidate_count=len(unique_candidates),
        attached_count=attached_count,
        missing_attach_method_count=missing_attach_method_count,
        failed_count=failed_count,
    )
