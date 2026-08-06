"""Support helpers for composition runtime runner control-plane policy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._runner_control_plane_artifact_policy import (
    requires_artifact_publication_closure as _requires_artifact_publication_closure,
    validate_artifact_recorder_attachment as _validate_artifact_recorder_attachment,
)
from bioetl.composition.runtime_builders._runner_control_plane_data_root_policy import (
    validate_strict_data_root_policy as _validate_strict_data_root_policy,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

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
    default_active_layers = tuple(
        layer
        for layer in _PERSISTENCE_PROFILE_ACTIVE_LAYERS
        if not (layer == "gold" and skip_gold)
    )
    # Missing yaml_config or sink=None: honor default active layers (and
    # skip_gold) rather than treating the run as having no published layers.
    if yaml_config is None or getattr(yaml_config, "sink", None) is None:
        return default_active_layers, default_active_layers
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
    settings: Settings,
    required_profile: object,
    exact_replay: bool = False,
) -> None:
    """Fail closed when strict reproducibility relies on fallback data roots."""
    _validate_strict_data_root_policy(
        settings=settings,
        required_profile=required_profile,
        exact_replay=exact_replay,
    )


requires_artifact_publication_closure = _requires_artifact_publication_closure
validate_artifact_recorder_attachment = _validate_artifact_recorder_attachment


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
