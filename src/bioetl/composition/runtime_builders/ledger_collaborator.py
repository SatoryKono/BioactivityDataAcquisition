"""Ledger collaborator attachment for control-plane."""

from __future__ import annotations

from bioetl.application.ports.pipeline import PipelineRunnerProtocol
from bioetl.application.services.control_plane.ledger.artifact_recording import (
    canonical_lineage_fragment_id as _canonical_lineage_fragment_id,  # noqa: F401
    record_input_snapshots_from_artifact as _record_input_snapshots_from_artifact,  # noqa: F401
    record_published_artifact as _record_artifact,
)
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )

__all__ = [
    "ArtifactRecorderAttachmentResult",
    "PipelineRunnerProtocol",
    "attach_control_plane_collaborators",
]


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

from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
    FileContractEvidenceRecorder,
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
    launch_context: PipelineRunContext | None = None,
) -> None:
    attach = getattr(runner, "attach_contract_evidence_recorder", None)
    if not callable(attach):
        return
    ledger_port = getattr(run_ledger_service, "ledger_port", None)
    base_path = getattr(ledger_port, "base_path", None)
    if base_path is None:
        return
    from pathlib import Path

    manifest_root = Path(base_path).parent / "run_manifest"
    recorder = FileContractEvidenceRecorder(base_path=manifest_root)
    if launch_context is None:
        attach(recorder)
    else:
        attach(recorder, launch_context=launch_context)


def attach_control_plane_collaborators(
    runner: PipelineRunnerProtocol,
    run_ledger_service: RunLedgerService,
    *,
    launch_context: PipelineRunContext | None = None,
) -> ArtifactRecorderAttachmentResult:
    """Attach ledger collaborators to the runner and its metadata writers."""
    runner.attach_run_ledger_service(run_ledger_service)
    _attach_contract_evidence_recorder(runner, run_ledger_service, launch_context)

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
