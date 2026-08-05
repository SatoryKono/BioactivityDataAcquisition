"""Lookup helpers for observability workflow dossiers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol

from bioetl.application.services.checkpoint.checkpoint_models import CheckpointInfo
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )


class CheckpointLookupService(Protocol):
    async def get_checkpoint(self, pipeline_name: str) -> CheckpointInfo | None: ...

    async def get_checkpoint_for_run(
        self,
        pipeline_name: str,
        run_id: str,
    ) -> CheckpointInfo | None: ...


class LineageExplainService(Protocol):
    def explain_run(self, run_id: str) -> LineageRunExplanationResult: ...


class RunManifestShowService(Protocol):
    def show(self, identifier: str) -> RunManifestInspectionResult: ...


def resolve_pipeline_name(
    run_manifest: RunManifestInspectionResult | None,
) -> str | None:
    if run_manifest is None:
        return None
    return run_manifest.manifest.pipeline_name


def _coerce_checkpoint_info(value: object) -> CheckpointInfo | None:
    if isinstance(value, CheckpointInfo):
        return value
    return None


def _copy_checkpoint_metadata(metadata: object) -> dict[str, object]:
    if isinstance(metadata, Mapping):
        return dict(metadata)
    return {}


async def resolve_checkpoint_for_run(
    *,
    checkpoint_service: CheckpointLookupService,
    run_id: str,
    pipeline_name: str | None,
) -> CheckpointInfo | None:
    if pipeline_name is None:
        return None
    checkpoint = _coerce_checkpoint_info(
        await checkpoint_service.get_checkpoint_for_run(pipeline_name, run_id)
    )
    if checkpoint is None:
        checkpoint = _coerce_checkpoint_info(
            await checkpoint_service.get_checkpoint(pipeline_name)
        )
    if checkpoint is None:
        return None
    if checkpoint.run_id in {None, run_id}:
        return checkpoint
    return CheckpointInfo(
        pipeline_name=checkpoint.pipeline_name,
        run_id=checkpoint.run_id,
        metadata={
            **_copy_checkpoint_metadata(checkpoint.metadata),
            "status": "mismatched_run_context",
        },
    )


def resolve_lineage_for_run(
    lineage_service: LineageExplainService | None,
    run_id: str,
) -> LineageRunExplanationResult | None:
    if lineage_service is None:
        return None
    try:
        return lineage_service.explain_run(run_id)
    except ValueError:
        return None


def resolve_run_manifest(
    run_manifest_service: RunManifestShowService | None,
    identifier: str,
) -> RunManifestInspectionResult | None:
    if run_manifest_service is None:
        return None
    try:
        return run_manifest_service.show(identifier)
    except ValueError:
        return None
