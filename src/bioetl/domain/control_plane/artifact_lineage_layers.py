"""Active-layer lineage sidecar policy (#11241)."""

from __future__ import annotations

from collections.abc import Mapping

_PERSISTENCE_PROFILE_ACTIVE_LAYERS = ("bronze", "silver", "gold")


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
    if yaml_config is None or getattr(yaml_config, "sink", None) is None:
        return default_active_layers, ()
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
