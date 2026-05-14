"""Loader for the canonical semantic field registry JSON asset."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.domain.registry.semantic_fields import (
    SemanticFieldCluster,
    SemanticFieldRegistry,
)


def _read_string_list(payload: object, *, field_name: str) -> tuple[str, ...]:
    """Read a JSON list field as a tuple of non-empty strings."""
    if payload is None:
        return ()
    if not isinstance(payload, list):
        raise ValueError(f"{field_name} must be a list of strings")
    values: list[str] = []
    for item in payload:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} must contain non-empty strings")
        values.append(item)
    return tuple(values)


class SemanticFieldRegistryLoader:
    """Load semantic field clusters from ``configs/field_registry`` JSON."""

    def __init__(self, configs_root: Path) -> None:
        self._registry_path = (
            configs_root / "field_registry" / "canonical_registry.json"
        )

    def load(self) -> SemanticFieldRegistry:
        """Load the canonical semantic field registry."""
        payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        raw_clusters = payload.get("clusters")
        if not isinstance(raw_clusters, list):
            raise ValueError("clusters must be a list")

        clusters: list[SemanticFieldCluster] = []
        for raw_cluster in raw_clusters:
            if not isinstance(raw_cluster, dict):
                raise ValueError("cluster entries must be objects")
            cluster = SemanticFieldCluster(
                cluster_id=_require_string(raw_cluster, "cluster_id"),
                semantic_name=_require_string(raw_cluster, "semantic_name"),
                canonical_name=_require_string(raw_cluster, "canonical_name"),
                legacy_names=_read_string_list(
                    raw_cluster.get("legacy_names"),
                    field_name="legacy_names",
                ),
                raw_provider_names=_read_string_list(
                    raw_cluster.get("raw_provider_names"),
                    field_name="raw_provider_names",
                ),
                pipelines=_read_string_list(
                    raw_cluster.get("pipelines"),
                    field_name="pipelines",
                ),
                affected_paths=_read_string_list(
                    raw_cluster.get("affected_paths"),
                    field_name="affected_paths",
                ),
                migration_status=_require_string(raw_cluster, "migration_status"),
                notes=_require_string(raw_cluster, "notes"),
            )
            clusters.append(cluster)
        return SemanticFieldRegistry(tuple(clusters))


def _require_string(payload: dict[str, object], field_name: str) -> str:
    """Read one required non-empty string field."""
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value
