"""Ledger collaborator attachment for control-plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_ledger_service import (
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
    return service.record_artifact_published(
        layer=layer,
        artifact_path=artifact_path,
        dataset_ref=dataset_ref,
        lineage_fragment_id=lineage_fragment_id,
        details=details,
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


def attach_control_plane_collaborators(
    runner: PipelineRunnerProtocol,
    run_ledger_service: RunLedgerService,
) -> ArtifactRecorderAttachmentResult:
    """Attach ledger collaborators to the runner and its metadata writers."""
    runner.attach_run_ledger_service(run_ledger_service)

    services = getattr(runner, "services", None)
    if services is None:
        return ArtifactRecorderAttachmentResult(
            candidate_count=0,
            attached_count=0,
            missing_attach_method_count=0,
            failed_count=0,
        )

    candidates: list[object] = []
    metadata_writer = getattr(services, "metadata_writer", None)
    if metadata_writer is not None:
        candidates.append(metadata_writer)

    storage = getattr(services, "storage", None)
    if storage is not None:
        for writer_name in ("bronze", "silver", "gold"):
            writer = getattr(storage, writer_name, None)
            if writer is None:
                continue
            writer_metadata = getattr(writer, "_metadata_writer", None)
            if writer_metadata is not None:
                candidates.append(writer_metadata)

    seen: set[int] = set()
    candidate_count = 0
    attached_count = 0
    missing_attach_method_count = 0
    failed_count = 0
    for candidate in candidates:
        candidate_id = id(candidate)
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        candidate_count += 1
        attach = getattr(candidate, "attach_artifact_recorder", None)
        if not callable(attach):
            missing_attach_method_count += 1
            continue
        try:
            if _attach_artifact_recorder(candidate, run_ledger_service):
                attached_count += 1
            else:
                missing_attach_method_count += 1
        except (AttributeError, RuntimeError, TypeError, ValueError):
            failed_count += 1
    return ArtifactRecorderAttachmentResult(
        candidate_count=candidate_count,
        attached_count=attached_count,
        missing_attach_method_count=missing_attach_method_count,
        failed_count=failed_count,
    )
