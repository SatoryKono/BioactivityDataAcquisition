"""Support helpers for constructing run manifest payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._input_snapshot_resolution import (
    resolve_pipeline_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    control_plane_root,
    create_control_plane_refs,
    legacy_config_hash_from_resolved_config_hash,
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
    RunManifestContractIdentity,
    resolve_contract_identity,
)
from bioetl.domain.control_plane import ReplayCapability, RunSourceRef
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    resolve_replay_capability as _resolve_policy_replay_capability,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "ManifestControlPlaneRefs",
    "RunManifestContractIdentity",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "legacy_config_hash_from_resolved_config_hash",
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
    required_persistence_profile: object = DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
) -> tuple[RunSourceRef, ...]:
    input_snapshots = resolve_pipeline_input_snapshot_refs(
        ctx=ctx,
        cached_bronze=cached_bronze,
        settings=settings,
        provider=provider,
        entity=entity,
    )
    required_profile = normalize_required_persistence_profile(
        required_persistence_profile
    )
    strict_snapshot_required = bool(getattr(ctx, "exact_replay", False)) or (
        required_profile in STRICT_PERSISTENCE_PROFILES
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
    replay_capable_family: bool = False,
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
        _validate_append_idempotency_evidence(
            yaml_config=yaml_config,
            layer_name=layer_name,
            layer_config=layer_config,
            contract=contract,
        )
    if (strict_replay_requested or replay_capable_family) and append_layers:
        details = ", ".join(
            f"sink.{layer_name}.mode=append" for layer_name in append_layers
        )
        raise RuntimeError(
            "Replay-capable pipeline families cannot use append-mode Silver/Gold "
            f"semantic outputs ({details}); use merge/upsert, overwrite, or SCD2 "
            "semantics with stable keys instead"
        )


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


def _validate_append_idempotency_evidence(
    *,
    yaml_config: object,
    layer_name: str,
    layer_config: object | None,
    contract: str,
) -> None:
    """Require machine-readable append idempotency evidence outside strict replay."""
    if contract == "occurrence_only":
        return
    if _append_idempotency_evidence_present(
        yaml_config=yaml_config,
        layer_config=layer_config,
        contract=contract,
    ):
        return
    raise RuntimeError(
        f"sink.{layer_name}.mode=append with "
        f"sink.{layer_name}.idempotency_contract={contract} requires "
        "machine-readable idempotency evidence; add "
        f"sink.{layer_name}.idempotency_evidence or classify the output as "
        "occurrence_only"
    )


def _append_idempotency_evidence_present(
    *,
    yaml_config: object,
    layer_config: object | None,
    contract: str,
) -> bool:
    evidence = _sink_layer_idempotency_evidence(layer_config)
    if contract == "partition_append_with_stable_partition_key":
        return bool(
            _text_items(evidence.get("stable_partition_keys"))
            or _text_items(evidence.get("partition_keys"))
            or _text_items(_sink_layer_field(layer_config, "partition_keys"))
        )
    if contract == "append_log":
        return bool(
            _text_items(evidence.get("occurrence_identity_fields"))
            or _text_items(evidence.get("append_log_identity_fields"))
            or _text_items(getattr(yaml_config, "business_primary_keys", None))
        )
    return False


def _sink_layer_idempotency_evidence(
    layer_config: object | None,
) -> dict[str, object]:
    evidence = _sink_layer_field(layer_config, "idempotency_evidence")
    if isinstance(evidence, dict):
        return dict(evidence)
    proof = _sink_layer_field(layer_config, "idempotency_proof")
    if isinstance(proof, dict):
        return dict(proof)
    return {}


def _sink_layer_field(layer_config: object | None, field_name: str) -> object | None:
    if isinstance(layer_config, dict):
        return layer_config.get(field_name)
    return getattr(layer_config, field_name, None)


def _text_items(value: object) -> tuple[str, ...]:
    if value is None or isinstance(value, str | bytes):
        text = str(value or "").strip()
        return (text,) if text else ()
    if not isinstance(value, (list, tuple, set, frozenset)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())
