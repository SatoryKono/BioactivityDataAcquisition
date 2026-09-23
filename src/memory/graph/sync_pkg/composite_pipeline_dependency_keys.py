"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.composite_seed_pipeline_name import (
    _composite_dependency_pipeline_keys,
    _composite_seed_pipeline_name,
)
from memory.graph.sync_pkg.empty_normalization_evidence_payload import (
    _empty_normalization_evidence_payload,
    _finalize_normalization_evidence_defaults,
)

__all__ = [
    "_build_normalization_pipeline_evidence",
    "_composite_pipeline_dependency_keys",
]


def _composite_pipeline_dependency_keys(
    composite_payload: object,
    pipeline_nodes: dict[str, NodeKey],
) -> tuple[NodeKey, ...]:
    if not isinstance(composite_payload, dict):
        return ()
    keys: list[NodeKey] = []
    seed_pipeline = _composite_seed_pipeline_name(composite_payload.get("seed"))
    if seed_pipeline is not None and seed_pipeline in pipeline_nodes:
        keys.append(pipeline_nodes[seed_pipeline])
    keys.extend(
        _composite_dependency_pipeline_keys(
            composite_payload.get("dependencies"), pipeline_nodes
        )
    )
    return tuple(keys)


def _build_normalization_pipeline_evidence() -> dict[str, dict[str, JsonValue]]:
    try:
        from bioetl.domain.normalization.profiles.registry import (
            NORMALIZATION_PROFILE_REGISTRY,
            resolve_normalization_profile_module_path,
        )
    except (AttributeError, ImportError):
        return {}

    evidence: dict[str, dict[str, JsonValue]] = {}
    for (provider, entity), profile in NORMALIZATION_PROFILE_REGISTRY.items():
        pipeline_name = f"{provider}_{entity}"
        payload = _empty_normalization_evidence_payload()
        payload["normalization_profile_registered"] = True
        payload["normalization_profile_module_path"] = (
            resolve_normalization_profile_module_path(provider, entity)
        )
        payload["profile_field_count"] = len(profile.field_rules)
        evidence[pipeline_name] = payload
    _finalize_normalization_evidence_defaults(evidence)
    return evidence
