"""Private helpers for runtime runner builder control-plane glue."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders._run_manifest_refs import (
    is_explicit_data_root_configured,
    resolve_data_root_mode,
)
from bioetl.composition.runtime_builders.inputs_resolver import (
    RunnerInputs as _RunnerInputs,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)

_PERSISTENCE_PROFILE_ACTIVE_LAYERS = ("bronze", "silver", "gold")


class _LoggerBindableObservability(Protocol):
    logger: object


def _normalize_required_persistence_profile(required_profile: object) -> str:
    return normalize_required_persistence_profile(required_profile)


def _coerce_sink_layer_mapping(yaml_config: object) -> Mapping[str, object]:
    sink = getattr(yaml_config, "sink", None)
    if isinstance(sink, Mapping):
        return sink
    return {}


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
    """Return active layers and layers missing metadata-sidecar persistence."""
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


def requires_strict_reproducibility_context(
    *,
    required_profile: object,
    exact_replay: bool = False,
) -> bool:
    """Return ``True`` when the runtime must satisfy strict replay guarantees."""
    return bool(exact_replay) or (
        _normalize_required_persistence_profile(required_profile)
        in STRICT_PERSISTENCE_PROFILES
    )


def validate_strict_data_root_policy(
    *,
    settings: object,
    required_profile: object,
    exact_replay: bool = False,
) -> None:
    """Fail closed when strict reproducibility relies on fallback data roots."""
    if not requires_strict_reproducibility_context(
        required_profile=required_profile,
        exact_replay=exact_replay,
    ):
        return
    if is_explicit_data_root_configured(settings):
        return
    profile = _normalize_required_persistence_profile(required_profile)
    mode = resolve_data_root_mode(settings)
    raise RuntimeError(
        "Strict reproducibility contexts require an explicit settings.data_dir; "
        f"resolved fallback data root mode '{mode}' is not allowed for required "
        f"persistence profile '{profile}'"
    )


def requires_artifact_publication_closure(required_profile: object) -> bool:
    """Return ``True`` when artifact publication must be fully wired."""
    return _normalize_required_persistence_profile(required_profile) in {
        "replay_ready",
        "forensic_grade"
    }


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
        DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
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
    if not isinstance(rebound_observability, ObservabilityBundle):
        return inputs
    return _RunnerInputs(
        settings=inputs.settings,
        yaml_config=inputs.yaml_config,
        observability=rebound_observability,
        runtime_config=inputs.runtime_config,
        filter_config=inputs.filter_config,
        cached_bronze=inputs.cached_bronze,
    )


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
