"""Pure replay write-risk assessment and bounded metric emission."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.medallion import MedallionPolicy
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

REPLAY_WRITE_RISK_METRIC = "bioetl_replay_duplicate_overwrite_risk_total"


class ReplayWriteRiskClassification(StrEnum):
    """Bounded replay write-risk vocabulary exposed to Prometheus."""

    DUPLICATE = "duplicate"
    OVERWRITE = "overwrite"


_RISK_TYPES: tuple[ReplayWriteRiskClassification, ...] = tuple(
    ReplayWriteRiskClassification
)
_REPLAY_MODES = frozenset({"exact_replay", "rebuild", "replay", "resume"})
_CLEAR_POLICIES = frozenset({"both", "gold", "silver", "silver_and_gold"})


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _normalized_text(value: object) -> str:
    return str(getattr(value, "value", value) or "").strip().lower()


def _is_reprocessing_manifest(manifest: RunManifest) -> bool:
    """Return whether this accepted manifest can reprocess persisted outputs."""
    if manifest.replay_of_run_id or manifest.replay_of_manifest_id:
        return True
    if manifest.run_type in {RunType.BACKFILL, RunType.REBUILD}:
        return True
    launch = manifest.launch_context
    if bool(launch.get("exact_replay")) or bool(launch.get("resume")):
        return True
    return _normalized_text(launch.get("replay_mode")) in _REPLAY_MODES


def _iter_config_roots(manifest: RunManifest) -> tuple[Mapping[str, object], ...]:
    """Return candidate mappings that may own write-mode configuration."""
    roots: list[Mapping[str, object]] = []
    for config in (manifest.runtime_config, manifest.resolved_config):
        mapping = _mapping(config)
        if mapping is None:
            continue
        roots.append(mapping)
        for key in ("pipeline", "table", "storage"):
            nested = _mapping(mapping.get(key))
            if nested is not None:
                roots.append(nested)
    return tuple(roots)


def _iter_sink_modes(manifest: RunManifest) -> tuple[tuple[str, str], ...]:
    """Return enabled ``(layer, mode)`` pairs without exposing sink identity."""
    modes: set[tuple[str, str]] = set()
    for root in _iter_config_roots(manifest):
        sink = _mapping(root.get("sink"))
        if sink is not None:
            for layer in ("silver", "gold"):
                settings = _mapping(sink.get(layer))
                if settings is None or settings.get("enabled") is False:
                    continue
                mode = _normalized_text(settings.get("mode"))
                if mode:
                    modes.add((layer, mode))
        for layer in ("silver", "gold"):
            for key in (f"{layer}_write_mode", f"{layer}_mode"):
                mode = _normalized_text(root.get(key))
                if mode:
                    modes.add((layer, mode))
    return tuple(sorted(modes))


def _declares_append_semantic_sink(manifest: RunManifest) -> bool:
    raw = manifest.launch_context.get("append_mode_semantic_sinks")
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        return False
    return any(isinstance(item, str) and item.strip() for item in raw)


def _has_explicit_clear(manifest: RunManifest) -> bool:
    policy = MedallionPolicy.for_run_type(manifest.run_type)
    if policy.should_clear_silver or policy.should_clear_gold:
        return True
    launch = manifest.launch_context
    if any(
        bool(launch.get(key))
        for key in ("clear_before_run", "clear_outputs", "rebuild")
    ):
        return True
    return _normalized_text(launch.get("clear_policy")) in _CLEAR_POLICIES


def _has_duplicate_risk(
    manifest: RunManifest,
    modes: tuple[tuple[str, str], ...],
) -> bool:
    return _declares_append_semantic_sink(manifest) or any(
        mode == "append" for _layer, mode in modes
    )


def _has_destructive_sink_mode(modes: tuple[tuple[str, str], ...]) -> bool:
    return any(
        (layer == "gold" and mode == "overwrite")
        or (layer == "silver" and mode == "delete")
        for layer, mode in modes
    )


def _is_composite_replace_replay(manifest: RunManifest) -> bool:
    """Return whether composite replay uses replace-style publication."""
    launch = manifest.launch_context
    return _normalized_text(
        launch.get("execution_context")
    ) == "composite" and _normalized_text(launch.get("replay_mode")) in {
        "rebuild",
        "resume",
    }


def _has_overwrite_risk(
    manifest: RunManifest,
    modes: tuple[tuple[str, str], ...],
) -> bool:
    return (
        _has_destructive_sink_mode(modes)
        or _has_explicit_clear(manifest)
        or _is_composite_replace_replay(manifest)
    )


def assess_replay_write_risks(
    manifest: RunManifest,
) -> frozenset[ReplayWriteRiskClassification]:
    """Classify duplicate/overwrite exposure for one accepted replay manifest."""
    if not _is_reprocessing_manifest(manifest):
        return frozenset()

    modes = _iter_sink_modes(manifest)
    risk_checks = (
        (
            ReplayWriteRiskClassification.DUPLICATE,
            _has_duplicate_risk(manifest, modes),
        ),
        (
            ReplayWriteRiskClassification.OVERWRITE,
            _has_overwrite_risk(manifest, modes),
        ),
    )
    return frozenset(risk for risk, detected in risk_checks if detected)


def emit_replay_write_risk_metrics(
    metrics: MetricsPort | None,
    manifest: RunManifest,
) -> None:
    """Publish both bounded series, then increment detected risk series."""
    if metrics is None:
        return
    base_labels = {
        "pipeline": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
    }
    for risk_type in _RISK_TYPES:
        metrics.increment_counter(
            REPLAY_WRITE_RISK_METRIC,
            0,
            {**base_labels, "risk_type": risk_type.value},
        )
    for risk_type in sorted(assess_replay_write_risks(manifest), key=str):
        metrics.increment_counter(
            REPLAY_WRITE_RISK_METRIC,
            1,
            {**base_labels, "risk_type": risk_type.value},
        )


__all__ = [
    "REPLAY_WRITE_RISK_METRIC",
    "ReplayWriteRiskClassification",
    "assess_replay_write_risks",
    "emit_replay_write_risk_metrics",
]
