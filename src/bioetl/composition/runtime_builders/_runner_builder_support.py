"""Private helpers for runtime runner builder control-plane glue."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol, cast

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)

_DEFAULT_REQUIRED_PERSISTENCE_PROFILE = "degraded_observable"
_PERSISTENCE_PROFILE_REQUIREMENTS = {"replay_ready", "forensic_grade"}
_PERSISTENCE_PROFILE_ACTIVE_LAYERS = ("bronze", "silver", "gold")


class _LoggerBindableObservability(Protocol):
    logger: object


def _normalize_required_persistence_profile(required_profile: object) -> str:
    profile = (
        str(required_profile).strip()
        if required_profile is not None
        else _DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    return profile or _DEFAULT_REQUIRED_PERSISTENCE_PROFILE


def _coerce_sink_layer_mapping(yaml_config: object) -> Mapping[str, object]:
    sink = getattr(yaml_config, "sink", None)
    if isinstance(sink, Mapping):
        return sink
    return {}


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
    """Return active layers and layers missing metadata-sidecar persistence."""
    if yaml_config is None:
        active_layers = tuple(
            layer
            for layer in _PERSISTENCE_PROFILE_ACTIVE_LAYERS
            if not (layer == "gold" and skip_gold)
        )
        return active_layers, active_layers
    sink_mapping = _coerce_sink_layer_mapping(yaml_config)
    active_layers: list[str] = []
    missing_lineage_layers: list[str] = []
    for layer in _PERSISTENCE_PROFILE_ACTIVE_LAYERS:
        if layer == "gold" and skip_gold:
            continue
        layer_config = sink_mapping.get(layer)
        if not _is_sink_layer_enabled(layer_config):
            continue
        active_layers.append(layer)
        if not _has_lineage_sidecar_persistence(layer_config):
            missing_lineage_layers.append(layer)
    return tuple(active_layers), tuple(missing_lineage_layers)


def validate_required_persistence_profile(
    *,
    manifest_enabled: bool,
    ledger_enabled: bool,
    required_profile: object,
    execution_label: str,
    exact_replay_execution_context_supported: bool = True,
    missing_artifact_lineage_layers: tuple[str, ...] = (),
) -> None:
    """Fail closed when static control-plane flags cannot satisfy required profile."""
    profile = _normalize_required_persistence_profile(required_profile)
    if profile in _PERSISTENCE_PROFILE_REQUIREMENTS and not manifest_enabled:
        raise RuntimeError(
            f"{execution_label} requires run manifests for required persistence "
            f"profile '{profile}'; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    if (
        profile in _PERSISTENCE_PROFILE_REQUIREMENTS
        and not exact_replay_execution_context_supported
    ):
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because this execution context is outside the strict "
            "exact-replay support boundary"
        )
    if profile == "forensic_grade" and not ledger_enabled:
        raise RuntimeError(
            f"{execution_label} requires run ledgers for required persistence "
            "profile 'forensic_grade'; set "
            "pipeline.control_plane.run_ledger_enabled=true"
        )
    if profile == "forensic_grade" and missing_artifact_lineage_layers:
        layers = ", ".join(missing_artifact_lineage_layers)
        raise RuntimeError(
            f"{execution_label} requires metadata sidecars / lineage persistence "
            f"for active layers [{layers}] to satisfy required persistence profile "
            "'forensic_grade'; enable sink.<layer>.save_metadata for each active "
            "published layer"
        )


def resolve_control_plane_flags(
    settings: object,
    *,
    yaml_config: object | None = None,
    skip_gold: bool = False,
) -> tuple[bool, bool]:
    """Resolve control-plane feature flags for executable pipeline runs."""
    pipeline_settings = getattr(settings, "pipeline", None)
    control_plane = getattr(pipeline_settings, "control_plane", None)
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    required_profile = getattr(
        control_plane,
        "required_persistence_profile",
        "degraded_observable",
    )
    if not manifest_enabled:
        raise RuntimeError(
            "Pipeline execution requires run manifests; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    _active_layers, missing_artifact_lineage_layers = (
        resolve_required_artifact_lineage_layers(
            yaml_config=yaml_config,
            skip_gold=skip_gold,
        )
    )
    validate_required_persistence_profile(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label="Pipeline execution",
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )
    return True, ledger_enabled


def bind_manifest_logger_context(
    inputs: _RunnerInputs,
    manifest_id: str,
) -> _RunnerInputs:
    """Bind ``manifest_id`` into runtime observability when available."""
    observability = getattr(inputs, "observability", None)
    rebound_observability = _rebind_observability_logger(
        observability=observability,
        manifest_id=manifest_id,
    )
    if rebound_observability is observability:
        return inputs
    if isinstance(inputs, _RunnerInputs):
        return cast(
            _RunnerInputs,
            replace(
                inputs,
                observability=cast("ObservabilityBundle", rebound_observability),
            ),
        )
    return inputs


def _rebind_observability_logger(
    *,
    observability: object,
    manifest_id: str,
) -> object:
    """Return observability with ``manifest_id`` bound to its logger context."""
    bind_fn = getattr(observability, "bind", None)
    if callable(bind_fn):
        return bind_fn(manifest_id=manifest_id)

    logger = getattr(observability, "logger", None)
    logger_bind = getattr(logger, "bind", None)
    if not callable(logger_bind):
        return observability

    typed_observability = cast("_LoggerBindableObservability", observability)
    try:
        typed_observability.logger = logger_bind(manifest_id=manifest_id)
    except (AttributeError, TypeError):
        return observability
    return observability
