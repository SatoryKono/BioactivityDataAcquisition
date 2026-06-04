"""Support helpers for composition runtime runner control-plane policy."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.composition.runtime_builders._run_manifest_refs import (
    is_explicit_data_root_configured,
    resolve_data_root_mode,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)

_PERSISTENCE_PROFILE_ACTIVE_LAYERS = ("bronze", "silver", "gold")


def _normalize_required_persistence_profile(required_profile: object) -> str:
    return normalize_required_persistence_profile(required_profile)


def _resolve_sink_layer_config(yaml_config: object, layer: str) -> object | None:
    sink = getattr(yaml_config, "sink", None)
    if sink is None:
        return None
    if isinstance(sink, Mapping):
        return sink.get(layer)
    return getattr(sink, layer, None)


def _is_sink_layer_enabled(layer_config: object | None) -> bool:
    if layer_config is None:
        return True
    return bool(getattr(layer_config, "enabled", True))


def _has_lineage_sidecar_persistence(layer_config: object | None) -> bool:
    if layer_config is None:
        return False
    return bool(getattr(layer_config, "save_metadata", False))


def resolve_required_artifact_lineage_layers(
    *,
    yaml_config: object | None,
    skip_gold: bool = False,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return active sink layers and layers missing metadata sidecars."""
    if yaml_config is None:
        default_active_layers = tuple(
            layer
            for layer in _PERSISTENCE_PROFILE_ACTIVE_LAYERS
            if not (layer == "gold" and skip_gold)
        )
        return default_active_layers, default_active_layers
    if getattr(yaml_config, "sink", None) is None:
        return (), ()
    active_layer_names: list[str] = []
    missing_lineage_layers: list[str] = []
    for layer in _PERSISTENCE_PROFILE_ACTIVE_LAYERS:
        if layer == "gold" and skip_gold:
            continue
        layer_config = _resolve_sink_layer_config(yaml_config, layer)
        if not _is_sink_layer_enabled(layer_config):
            continue
        active_layer_names.append(layer)
        if not _has_lineage_sidecar_persistence(layer_config):
            missing_lineage_layers.append(layer)
    return tuple(active_layer_names), tuple(missing_lineage_layers)


def validate_required_persistence_profile(
    *,
    manifest_enabled: bool,
    ledger_enabled: bool,
    required_profile: object,
    execution_label: str,
    exact_replay_execution_context_supported: bool = True,
    composite_resume_rich_replay_supported: bool = True,
    missing_artifact_lineage_layers: tuple[str, ...] = (),
) -> None:
    """Fail closed when static control-plane flags cannot satisfy required profile."""
    profile = _normalize_required_persistence_profile(required_profile)
    if profile in STRICT_PERSISTENCE_PROFILES and not manifest_enabled:
        raise RuntimeError(
            f"{execution_label} requires run manifests for required persistence "
            f"profile '{profile}'; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    if (
        profile in STRICT_PERSISTENCE_PROFILES
        and not exact_replay_execution_context_supported
    ):
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because this execution context is outside the strict "
            "exact-replay support boundary"
        )
    if profile == "forensic_grade" and not composite_resume_rich_replay_supported:
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because composite forensic replay requires rich "
            "checkpoint evidence that is not persisted by the current resume model"
        )
    if profile in STRICT_PERSISTENCE_PROFILES and not ledger_enabled:
        raise RuntimeError(
            f"{execution_label} requires run ledgers for required persistence "
            f"profile '{profile}'; set pipeline.control_plane.run_ledger_enabled=true"
        )
    if profile in STRICT_PERSISTENCE_PROFILES and missing_artifact_lineage_layers:
        layers = ", ".join(missing_artifact_lineage_layers)
        raise RuntimeError(
            f"{execution_label} requires metadata sidecars / lineage persistence "
            f"for active layers [{layers}] to satisfy required persistence profile "
            f"'{profile}'; enable sink.<layer>.save_metadata for each active "
            "published layer"
        )


def validate_strict_data_root_policy(
    *,
    settings: object,
    required_profile: object,
    exact_replay: bool = False,
) -> None:
    """Fail closed when strict reproducibility relies on fallback data roots."""
    profile = _normalize_required_persistence_profile(required_profile)
    if not (exact_replay or profile in STRICT_PERSISTENCE_PROFILES):
        return
    if is_explicit_data_root_configured(settings):
        return
    mode = resolve_data_root_mode(settings)
    raise RuntimeError(
        "Strict reproducibility contexts require an explicit settings.data_dir; "
        f"resolved fallback data root mode '{mode}' is not allowed for required "
        f"persistence profile '{profile}'"
    )


def requires_artifact_publication_closure(required_profile: object) -> bool:
    """Return ``True`` when artifact publication must be fully wired."""
    return (
        _normalize_required_persistence_profile(required_profile)
        in STRICT_PERSISTENCE_PROFILES
    )


def validate_artifact_recorder_attachment(
    *,
    required_profile: object,
    candidate_count: int,
    attached_count: int,
    missing_attach_method_count: int,
    failed_count: int,
) -> None:
    """Fail closed when strict profiles cannot guarantee artifact publication."""
    if not requires_artifact_publication_closure(required_profile):
        return
    profile = _normalize_required_persistence_profile(required_profile)
    if candidate_count == 0:
        raise RuntimeError(
            f"Required persistence profile '{profile}' requires artifact publication "
            "closure, but no metadata-writer candidates were discovered for recorder attachment"
        )
    if (
        attached_count < candidate_count
        or missing_attach_method_count > 0
        or failed_count > 0
    ):
        raise RuntimeError(
            f"Required persistence profile '{profile}' requires artifact publication "
            "closure, but recorder attachment was incomplete "
            f"(candidates={candidate_count}, attached={attached_count}, "
            f"missing_attach_method_count={missing_attach_method_count}, "
            f"failed_count={failed_count})"
        )


def validate_manifest_persistence_requirements(
    *,
    yaml_config: object,
    skip_gold: bool,
    ledger_enabled: bool,
    required_profile: str,
    strict_exact_replay_supported: bool,
) -> None:
    """Validate manifest persistence requirements before manifest creation."""
    _active_layers, missing_artifact_lineage_layers = (
        resolve_required_artifact_lineage_layers(
            yaml_config=yaml_config,
            skip_gold=skip_gold,
        )
    )
    validate_required_persistence_profile(
        manifest_enabled=True,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label="Pipeline execution",
        exact_replay_execution_context_supported=strict_exact_replay_supported,
        composite_resume_rich_replay_supported=True,
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )
