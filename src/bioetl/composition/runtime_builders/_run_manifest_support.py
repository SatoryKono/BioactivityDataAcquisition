"""Private support helpers for control-plane manifest creation."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

import yaml

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunInputSnapshotRef,
    RunSourceRef,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings


def normalize_snapshot(value: object) -> object:
    """Normalize dataclass/Pydantic values into JSON-safe primitives."""
    if not isinstance(value, type) and is_dataclass(value):
        return normalize_snapshot(asdict(cast("DataclassInstance", value)))
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return normalize_snapshot(
            {key: item for key, item in vars(value).items() if not key.startswith("_")}
        )
    if isinstance(value, dict):
        return {str(key): normalize_snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalize_snapshot(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    return value


def to_serializable_mapping(value: object) -> dict[str, object]:
    """Convert dataclass or model objects into plain mappings."""
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json", exclude_none=True)
    elif hasattr(value, "dict"):
        payload = value.dict(exclude_none=True)
    elif hasattr(value, "__dict__"):
        payload = {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
    else:
        payload = normalize_snapshot(value)
    if not isinstance(payload, dict):
        return {"value": normalize_snapshot(payload)}
    normalized = normalize_snapshot(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Manifest snapshot normalization must return a mapping")
    return normalized


def build_launch_context_snapshot(
    ctx: PipelineRunContext,
    *,
    run_type_value: str,
    execution_context_value: str,
) -> dict[str, object]:
    """Capture launch-time options that materially affect execution semantics."""
    return {
        "pipeline_name": str(ctx.pipeline_name),
        "run_type": run_type_value,
        "resume": getattr(ctx, "resume", False),
        "dry_run": getattr(ctx, "dry_run", False),
        "limit": getattr(ctx, "limit", None),
        "query": getattr(ctx, "query", None),
        "start_offset": getattr(ctx, "start_offset", None),
        "log_level": getattr(ctx, "log_level", "INFO"),
        "ignore_yaml_filter": getattr(ctx, "ignore_yaml_filter", False),
        "skip_gold": getattr(ctx, "skip_gold", False),
        "execution_context": execution_context_value,
        "vacuum": to_serializable_mapping(getattr(ctx, "vacuum", None)),
        "input_filter": to_serializable_mapping(getattr(ctx, "input_filter", None)),
        "cached_bronze": to_serializable_mapping(getattr(ctx, "cached_bronze", None)),
    }


def resolve_provider_entity(
    *,
    pipeline_name: str,
    yaml_config: object,
) -> tuple[str, str]:
    """Resolve provider/entity from YAML when available, otherwise fallback."""
    if "_" in pipeline_name:
        fallback_provider, fallback_entity = pipeline_name.split("_", 1)
    else:
        fallback_provider = pipeline_name
        fallback_entity = pipeline_name
    provider = getattr(yaml_config, "provider", fallback_provider) or fallback_provider
    entity = getattr(yaml_config, "entity_type", fallback_entity) or fallback_entity
    return str(provider), str(entity)


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: object | None,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunSourceRef, ...]:
    """Build manifest source refs, including cached-Bronze snapshot provenance."""
    return (
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=ctx.pipeline_name,
            query=getattr(ctx, "query", None),
            input_snapshots=_build_cached_bronze_snapshot_refs(
                cached_bronze=cached_bronze,
                settings=settings,
                pipeline_name=ctx.pipeline_name,
                provider=provider,
                entity=entity,
            ),
        ),
    )


def _build_cached_bronze_snapshot_refs(
    *,
    cached_bronze: object | None,
    settings: Settings,
    pipeline_name: str,
    provider: str,
    entity: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Build immutable snapshot refs for cached-Bronze executions."""
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()
    bronze_root = (
        Path(cached_bronze.bronze_path)
        if getattr(cached_bronze, "bronze_path", None)
        else settings.bronze_path / provider / entity
    )
    batch_files = _resolve_cached_bronze_batch_files(
        bronze_root=bronze_root,
        bronze_date=getattr(cached_bronze, "bronze_date", None),
    )
    if not batch_files:
        raise RuntimeError(
            "Cached Bronze execution requires at least one persisted batch file for snapshot provenance"
        )
    content_hash = _compute_cached_bronze_content_hash(
        bronze_root=bronze_root,
        batch_files=batch_files,
    )
    snapshot_scope = (
        bronze_root / cached_bronze.bronze_date
        if getattr(cached_bronze, "bronze_date", None)
        else bronze_root
    )
    latest_mtime = max(file_path.stat().st_mtime for file_path in batch_files)
    snapshot_id = hashlib.sha256(
        f"{pipeline_name}:{snapshot_scope}:{content_hash}".encode("utf-8")
    ).hexdigest()
    return (
        RunInputSnapshotRef(
            snapshot_id=snapshot_id,
            content_hash=content_hash,
            immutable_uri=str(snapshot_scope),
            captured_at=datetime.fromtimestamp(latest_mtime, tz=UTC),
        ),
    )


def _resolve_cached_bronze_batch_files(
    *,
    bronze_root: Path,
    bronze_date: str | None,
) -> list[Path]:
    """Return cached Bronze batch files in deterministic order."""
    search_root = bronze_root / bronze_date if bronze_date else bronze_root
    if not search_root.exists():
        return []
    pattern = "batch_*.jsonl.zst" if bronze_date else "**/batch_*.jsonl.zst"
    return sorted(search_root.glob(pattern))


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


def _coerce_optional_text(value: object) -> str | None:
    """Return normalized non-empty text when available."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_contract_identity(
    *,
    provider: str,
    entity: str,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resolve contract identity fields from canonical registry when available."""
    contract_ref = f"{provider}.{entity}"
    registry_path = Path("configs/base/contract_registry.yaml")
    if not registry_path.exists():
        return contract_ref, None, None, None, None
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return contract_ref, None, None, None, None
    if not isinstance(payload, dict):
        return contract_ref, None, None, None, None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return contract_ref, None, None, None, None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return contract_ref, None, None, None, None
    identity = entry.get("identity")
    identity_payload = identity if isinstance(identity, dict) else {}
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    return (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )


def build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = Path(getattr(settings, "data_dir", "data")) / "output"
    return (
        RunArtifactRef(
            layer="bronze", path=str(output_root / "bronze" / provider / entity)
        ),
        RunArtifactRef(
            layer="silver", path=str(output_root / "silver" / provider / entity)
        ),
        RunArtifactRef(
            layer="gold", path=str(output_root / "gold" / provider / entity)
        ),
    )


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return Path(getattr(settings, "data_dir", "data")) / "output" / "control" / leaf


@dataclass(frozen=True, slots=True)
class ManifestControlPlaneRefs:
    """Resolved control-plane references produced before factory runner wiring."""

    manifest_id: str
    config_hash: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None
    contract_ref: str | None
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None


def resolve_run_context_values(
    ctx: PipelineRunContext,
) -> tuple[str, str]:
    """Resolve run type and execution context values from context."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = str(getattr(raw_run_type, "value", raw_run_type))
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = str(
        getattr(raw_execution_context, "value", raw_execution_context)
    )
    return run_type_value, execution_context_value


def create_control_plane_refs(
    manifest_id: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_ref: str,
    contract_version: str,
    contract_schema_hash: str,
    dq_policy_ref: str,
    rule_bundle_version: str,
) -> ManifestControlPlaneRefs:
    """Build the compact control-plane refs bundle returned to callers."""
    return ManifestControlPlaneRefs(
        manifest_id=manifest_id,
        config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
    )
