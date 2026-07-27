"""Checkpoint metadata assembly helpers for pipeline runner composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.checkpoint_metadata_resolution import (
    _coerce_optional_str,
    _normalize_execution_identity_payload,
    _resolve_checkpoint_snapshot_identity,
    _resolve_run_context_metadata,
)
from bioetl.domain.normalization import (
    compute_execution_identity_fingerprint,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.filtering.silver_filter_identity import (
    resolve_silver_filter_compatibility_mode,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


def _build_checkpoint_run_context(
    *,
    pipeline_name: str,
    run_context_metadata: dict[str, str | None],
    execution_fingerprint: str,
    silver_filter_compatibility_mode: str,
    identity_payload: dict[str, str | None],
) -> dict[str, str | None]:
    """Build the persisted run-context checkpoint fragment."""
    return {
        "pipeline_name": pipeline_name,
        "manifest_id": run_context_metadata["manifest_id"],
        "execution_fingerprint": execution_fingerprint,
        "silver_filter_compatibility_mode": silver_filter_compatibility_mode,
        "required_persistence_profile": run_context_metadata[
            "required_persistence_profile"
        ],
        "git_commit": run_context_metadata["git_commit"],
        "dependency_lock_hash": run_context_metadata["dependency_lock_hash"],
        "effective_config_hash": identity_payload["effective_config_hash"],
        "effective_config_artifact_id": run_context_metadata[
            "effective_config_artifact_id"
        ],
        "dq_contract_compatibility_hash": identity_payload[
            "dq_contract_compatibility_hash"
        ],
        "normalization_profile_ref": identity_payload["normalization_profile_ref"],
        "normalization_profile_version": identity_payload[
            "normalization_profile_version"
        ],
        "normalization_profile_hash": identity_payload["normalization_profile_hash"],
    }


def _build_checkpoint_metadata_from_identity(
    *,
    pipeline_name: str,
    run_type_value: str,
    run_context_metadata: dict[str, str | None],
    identity_payload: dict[str, str | None],
    execution_fingerprint: str,
    exact_replay: bool,
    input_snapshot_refs: tuple[dict[str, object], ...],
    input_snapshot_ids: tuple[str, ...],
    input_snapshot_fingerprint: str | None,
    silver_filter_compatibility_mode: str,
    run_context: dict[str, str | None],
) -> CheckpointMetadata:
    """Build the final checkpoint metadata value object."""
    return CheckpointMetadata(
        records_processed=0,
        pipeline_name=pipeline_name,
        run_type=run_type_value,
        dq_contract_compatibility_hash=identity_payload[
            "dq_contract_compatibility_hash"
        ],
        pipeline_version=identity_payload["pipeline_version"],
        git_commit=identity_payload["git_commit"],
        dependency_lock_hash=run_context_metadata["dependency_lock_hash"],
        effective_config_hash=identity_payload["effective_config_hash"],
        effective_config_artifact_id=run_context_metadata[
            "effective_config_artifact_id"
        ],
        execution_fingerprint=execution_fingerprint,
        composite_run_identity=run_context_metadata["composite_run_identity"],
        manifest_id=run_context_metadata["manifest_id"],
        contract_ref=identity_payload["contract_ref"],
        contract_version=identity_payload["contract_version"],
        normalization_profile_ref=identity_payload["normalization_profile_ref"],
        normalization_profile_version=identity_payload["normalization_profile_version"],
        normalization_profile_hash=identity_payload["normalization_profile_hash"],
        exact_replay=exact_replay,
        required_persistence_profile=run_context_metadata[
            "required_persistence_profile"
        ],
        input_snapshot_refs=input_snapshot_refs,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        run_context=run_context,
    )


def build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    """Build current execution identity metadata for checkpoint compatibility."""
    run_context_metadata = _resolve_run_context_metadata(pipeline)
    exact_replay = bool(getattr(pipeline.runtime, "exact_replay", False))
    (
        input_snapshot_refs,
        input_snapshot_ids,
        input_snapshot_fingerprint,
    ) = _resolve_checkpoint_snapshot_identity(pipeline)

    run_type = pipeline.runtime.run_type
    run_type_value = run_type.value if hasattr(run_type, "value") else str(run_type)
    pipeline_name = pipeline.config.pipeline_name
    silver_filter_compatibility_mode = (
        run_context_metadata["silver_filter_compatibility_mode"]
        or _coerce_optional_str(
            getattr(pipeline.runtime, "silver_filter_compatibility_mode", None)
        )
        or resolve_silver_filter_compatibility_mode()
    )
    identity_payload = _normalize_execution_identity_payload(
        pipeline_name=pipeline_name,
        run_type=run_type_value,
        pipeline_version=run_context_metadata["pipeline_version"],
        git_commit=run_context_metadata["git_commit"],
        dependency_lock_hash=run_context_metadata["dependency_lock_hash"],
        effective_config_hash=run_context_metadata["effective_config_hash"],
        dq_contract_compatibility_hash=run_context_metadata[
            "dq_contract_compatibility_hash"
        ],
        manifest_id=run_context_metadata["manifest_id"],
        contract=(
            run_context_metadata["contract_ref"],
            run_context_metadata["contract_version"],
        ),
        normalization_profile=(
            run_context_metadata["normalization_profile_ref"],
            run_context_metadata["normalization_profile_version"],
            run_context_metadata["normalization_profile_hash"],
        ),
        effective_config_artifact_id=run_context_metadata[
            "effective_config_artifact_id"
        ],
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
    )
    execution_fingerprint = run_context_metadata["execution_fingerprint"] or (
        compute_execution_identity_fingerprint(identity_payload)
    )
    run_context = _build_checkpoint_run_context(
        pipeline_name=pipeline_name,
        run_context_metadata=run_context_metadata,
        execution_fingerprint=execution_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        identity_payload=identity_payload,
    )

    return _build_checkpoint_metadata_from_identity(
        pipeline_name=pipeline_name,
        run_type_value=run_type_value,
        run_context_metadata=run_context_metadata,
        identity_payload=identity_payload,
        execution_fingerprint=execution_fingerprint,
        exact_replay=exact_replay,
        input_snapshot_refs=input_snapshot_refs,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
        run_context=run_context,
    )
