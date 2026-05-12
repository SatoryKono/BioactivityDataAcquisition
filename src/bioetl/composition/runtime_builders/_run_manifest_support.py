"""Support helpers for constructing run manifest payloads."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders._cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    control_plane_root,
    create_control_plane_refs,
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
    normalize_snapshot,
    resolve_provider_entity,
    resolve_replay_parentage,
    to_serializable_mapping,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    resolve_contract_identity,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    resolve_replay_capability as _resolve_policy_replay_capability,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings

__all__ = [
    "ManifestControlPlaneRefs",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "normalize_snapshot",
    "resolve_contract_identity",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
    "to_serializable_mapping",
    "validate_reproducible_sink_modes",
]


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: object | None,
    settings: Settings,
    provider: str,
    entity: str,
    required_persistence_profile: object = "degraded_observable",
) -> tuple[RunSourceRef, ...]:
    input_snapshots = _build_cached_bronze_snapshot_refs(
        cached_bronze=cached_bronze,
        settings=settings,
        provider=provider,
        entity=entity,
    )
    required_profile = normalize_required_persistence_profile(
        required_persistence_profile
    )
    strict_snapshot_required = (
        getattr(ctx, "exact_replay", False)
        or required_profile in STRICT_PERSISTENCE_PROFILES
    )
    if strict_snapshot_required and not input_snapshots:
        raise RuntimeError(
            "Exact replay and strict persistence profiles require immutable "
            "input snapshots; no snapshot-backed source refs were resolved "
            f"for required persistence profile '{required_profile}'"
        )
    return (
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=ctx.pipeline_name,
            query=getattr(ctx, "query", None),
            input_snapshots=input_snapshots,
        ),
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
) -> ReplayCapability:
    return _resolve_policy_replay_capability(
        source_refs=source_refs,
        resume_requested=resume_requested,
    )


def validate_reproducible_sink_modes(
    *,
    yaml_config: object,
    strict_replay_requested: bool,
) -> None:
    """Validate append-mode semantic outputs against explicit idempotency policy."""
    sink = getattr(yaml_config, "sink", None)
    if not isinstance(sink, dict):
        return
    append_layers = [
        layer_name
        for layer_name in ("silver", "gold")
        if (layer_config := sink.get(layer_name)) is not None
        and _sink_layer_enabled(layer_config)
        and _sink_layer_mode(layer_config) == "append"
    ]
    for layer_name in append_layers:
        layer_config = sink.get(layer_name)
        contract = _sink_layer_idempotency_contract(layer_config)
        if contract is None:
            raise RuntimeError(
                f"sink.{layer_name}.mode=append requires explicit "
                f"sink.{layer_name}.idempotency_contract"
            )
        if contract == "disallowed":
            raise RuntimeError(
                f"sink.{layer_name}.mode=append is disallowed by "
                f"sink.{layer_name}.idempotency_contract=disallowed"
            )
        if contract not in {
            "append_log",
            "partition_append_with_stable_partition_key",
            "occurrence_only",
        }:
            raise RuntimeError(
                f"sink.{layer_name}.mode=append is incompatible with "
                f"sink.{layer_name}.idempotency_contract={contract}"
            )
    if strict_replay_requested and append_layers:
        details = ", ".join(
            f"sink.{layer_name}.mode=append" for layer_name in append_layers
        )
        raise RuntimeError(
            "Strict reproducibility contexts cannot use append-mode Silver/Gold "
            f"semantic outputs ({details}); use merge/upsert, overwrite, or SCD2 "
            "semantics with stable keys instead"
        )


def _build_cached_bronze_snapshot_refs(
    *,
    cached_bronze: object | None,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Build immutable snapshot refs for cached-Bronze executions."""
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()
    bronze_path = getattr(cached_bronze, "bronze_path", None)
    bronze_date = getattr(cached_bronze, "bronze_date", None)
    bronze_root = (
        Path(str(bronze_path))
        if bronze_path is not None
        else settings.bronze_path / provider / entity
    )
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=cast("str | None", bronze_date),
    )
    if not snapshot_refs:
        raise RuntimeError(
            "Cached Bronze execution requires at least one persisted batch file for snapshot provenance"
        )
    return snapshot_refs


def _sink_layer_enabled(layer_config: object) -> bool:
    if isinstance(layer_config, dict):
        return bool(layer_config.get("enabled", True))
    return bool(getattr(layer_config, "enabled", True))


def _sink_layer_mode(layer_config: object) -> str:
    raw_mode = (
        layer_config.get("mode", "")
        if isinstance(layer_config, dict)
        else getattr(layer_config, "mode", "")
    )
    return str(raw_mode or "").strip().lower()


def _sink_layer_idempotency_contract(layer_config: object | None) -> str | None:
    raw_contract = (
        layer_config.get("idempotency_contract", None)
        if isinstance(layer_config, dict)
        else getattr(layer_config, "idempotency_contract", None)
    )
    contract = str(raw_contract or "").strip().lower()
    return contract or None
