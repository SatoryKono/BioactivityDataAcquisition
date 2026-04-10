"""Checkpoint metadata assembly helpers for pipeline runner composition."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.normalization import (
    normalize_runtime_anchor_payload,
    serialize_json_canonical,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.infrastructure.config import get_settings

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


def _resolve_run_context_payload(pipeline: BasePipeline) -> object | None:
    """Resolve metadata run_context from pipeline services when available."""
    metadata_coordinator = getattr(pipeline.services, "metadata_coordinator", None)
    if metadata_coordinator is None:
        return None
    return getattr(metadata_coordinator, "run_context", None)


def _coerce_optional_str(value: object | None) -> str | None:
    """Return a string value when present, otherwise None."""
    if value is None:
        return None
    text = str(value)
    return text or None


def _compute_execution_identity_fingerprint(
    payload: dict[str, str | None],
) -> str:
    """Compute deterministic execution identity fingerprint for checkpoints."""
    encoded = serialize_json_canonical(payload)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_execution_identity_payload(
    *,
    pipeline_name: str,
    run_type: str,
    pipeline_version: str | None,
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    manifest_id: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    exact_replay: bool,
    input_snapshot_fingerprint: str | None,
) -> dict[str, str | None]:
    """Return the canonical checkpoint execution-identity payload."""
    return normalize_runtime_anchor_payload(
        {
            "pipeline_name": pipeline_name,
            "run_type": run_type,
            "pipeline_version": pipeline_version,
            "effective_config_hash": effective_config_hash,
            "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
            "manifest_id": manifest_id,
            "contract_ref": contract_ref,
            "contract_version": contract_version,
            "exact_replay": str(exact_replay).lower(),
            "input_snapshot_fingerprint": input_snapshot_fingerprint,
        }
    )


def _compute_snapshot_identity_fingerprint(snapshot_ids: tuple[str, ...]) -> str | None:
    """Compute a deterministic fingerprint for checkpoint snapshot anchors."""
    if not snapshot_ids:
        return None
    encoded = serialize_json_canonical(list(snapshot_ids))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _resolve_input_snapshot_ids(pipeline: BasePipeline) -> tuple[str, ...]:
    """Resolve cached-Bronze snapshot identities for replay-safe checkpoints."""
    runtime = getattr(pipeline, "runtime", None)
    cached_bronze = None if runtime is None else getattr(runtime, "cached_bronze", None)
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()

    config = getattr(pipeline, "config", None)
    provider = _coerce_optional_str(getattr(config, "provider", None))
    entity = _coerce_optional_str(getattr(config, "entity_type", None))
    if provider is None or entity is None:
        return ()

    settings = get_settings()
    bronze_root = (
        Path(cached_bronze.bronze_path)
        if getattr(cached_bronze, "bronze_path", None)
        else settings.bronze_path / provider / entity
    )
    bronze_date = _coerce_optional_str(getattr(cached_bronze, "bronze_date", None))
    search_root = bronze_root / bronze_date if bronze_date else bronze_root
    if not search_root.exists():
        return ()

    pattern = "batch_*.jsonl.zst" if bronze_date else "**/batch_*.jsonl.zst"
    batch_files = sorted(search_root.glob(pattern))
    if not batch_files:
        return ()

    content_hash = _compute_cached_bronze_content_hash(
        bronze_root=bronze_root,
        batch_files=batch_files,
    )
    snapshot_scope = search_root if bronze_date else bronze_root
    snapshot_id = hashlib.sha256(
        f"{pipeline.config.pipeline_name}:{snapshot_scope}:{content_hash}".encode(
            "utf-8"
        )
    ).hexdigest()
    return (snapshot_id,)


def _compute_cached_bronze_content_hash(
    *,
    bronze_root: Path,
    batch_files: list[Path],
) -> str:
    """Compute a deterministic content hash over cached Bronze batch files."""
    digest = hashlib.sha256()
    for file_path in batch_files:
        digest.update(str(file_path.relative_to(bronze_root)).encode("utf-8"))
        digest.update(b"\0")
        with file_path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def build_current_checkpoint_metadata(pipeline: BasePipeline) -> CheckpointMetadata:
    """Build current execution identity metadata for checkpoint compatibility."""
    run_context = _resolve_run_context_payload(pipeline)
    pipeline_version = (
        _coerce_optional_str(getattr(run_context, "pipeline_version", None))
        if run_context is not None
        else None
    )
    effective_config_hash = (
        _coerce_optional_str(getattr(run_context, "config_hash", None))
        if run_context is not None
        else None
    )
    dq_contract_compatibility_hash = (
        _coerce_optional_str(
            getattr(run_context, "dq_contract_compatibility_hash", None)
        )
        if run_context is not None
        else None
    )
    manifest_id = (
        _coerce_optional_str(getattr(run_context, "manifest_id", None))
        if run_context is not None
        else None
    )
    contract_ref = (
        _coerce_optional_str(getattr(run_context, "contract_ref", None))
        if run_context is not None
        else None
    )
    contract_version = (
        _coerce_optional_str(getattr(run_context, "contract_version", None))
        if run_context is not None
        else None
    )
    effective_config_artifact_id = (
        _coerce_optional_str(getattr(run_context, "effective_config_artifact_id", None))
        if run_context is not None
        else None
    )
    exact_replay = bool(getattr(pipeline.runtime, "exact_replay", False))
    input_snapshot_ids = _resolve_input_snapshot_ids(pipeline)
    input_snapshot_fingerprint = _compute_snapshot_identity_fingerprint(
        input_snapshot_ids
    )

    run_type = pipeline.runtime.run_type
    run_type_value = run_type.value if hasattr(run_type, "value") else str(run_type)
    identity_payload = _normalize_execution_identity_payload(
        pipeline_name=pipeline.config.pipeline_name,
        run_type=run_type_value,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        exact_replay=exact_replay,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
    )
    execution_fingerprint = _compute_execution_identity_fingerprint(
        identity_payload
    )

    return CheckpointMetadata(
        records_processed=0,
        dq_contract_compatibility_hash=identity_payload["dq_contract_compatibility_hash"],
        pipeline_version=identity_payload["pipeline_version"],
        effective_config_hash=identity_payload["effective_config_hash"],
        effective_config_artifact_id=effective_config_artifact_id,
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref=identity_payload["contract_ref"],
        contract_version=identity_payload["contract_version"],
        exact_replay=exact_replay,
        input_snapshot_ids=input_snapshot_ids,
        run_context={
            "pipeline_name": pipeline.config.pipeline_name,
            "manifest_id": manifest_id,
        },
    )
