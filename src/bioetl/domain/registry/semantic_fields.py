"""Semantic field registry types and lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SemanticFieldCluster",
    "SemanticFieldRegistry",
]

def _build_registry_indexes(
    clusters: tuple[SemanticFieldCluster, ...],
) -> tuple[
    dict[str, SemanticFieldCluster],
    dict[str, SemanticFieldCluster],
    dict[str, SemanticFieldCluster],
    dict[str, SemanticFieldCluster],
]:
    by_cluster_id: dict[str, SemanticFieldCluster] = {}
    by_canonical_name: dict[str, SemanticFieldCluster] = {}
    by_legacy_name: dict[str, SemanticFieldCluster] = {}
    by_raw_provider_name: dict[str, SemanticFieldCluster] = {}

    for cluster in clusters:
        _register_cluster_id(by_cluster_id, cluster)
        _register_canonical_name(by_canonical_name, cluster)
        _register_legacy_names(by_legacy_name, cluster)
        _register_raw_provider_names(by_raw_provider_name, cluster)

    return (
        by_cluster_id,
        by_canonical_name,
        by_legacy_name,
        by_raw_provider_name,
    )
@dataclass(frozen=True, slots=True)
class SemanticFieldCluster:
    """One semantic field cluster with canonical and legacy naming metadata."""

    cluster_id: str
    semantic_name: str
    canonical_name: str
    legacy_names: tuple[str, ...]
    raw_provider_names: tuple[str, ...]
    pipelines: tuple[str, ...]
    affected_paths: tuple[str, ...]
    migration_status: str
    notes: str


def _register_cluster_id(
    registry: dict[str, SemanticFieldCluster],
    cluster: SemanticFieldCluster,
) -> None:
    key = cluster.cluster_id.lower()
    if key in registry:
        raise ValueError(f"duplicate cluster_id: {cluster.cluster_id}")
    registry[key] = cluster


def _register_canonical_name(
    registry: dict[str, SemanticFieldCluster],
    cluster: SemanticFieldCluster,
) -> None:
    key = cluster.canonical_name.lower()
    if key in registry:
        raise ValueError(f"duplicate canonical_name: {cluster.canonical_name}")
    registry[key] = cluster


def _register_legacy_names(
    registry: dict[str, SemanticFieldCluster],
    cluster: SemanticFieldCluster,
) -> None:
    for legacy_name in cluster.legacy_names:
        key = legacy_name.lower()
        if key in registry:
            raise ValueError(f"duplicate legacy_name: {legacy_name}")
        registry[key] = cluster


def _register_raw_provider_names(
    registry: dict[str, SemanticFieldCluster],
    cluster: SemanticFieldCluster,
) -> None:
    for raw_provider_name in cluster.raw_provider_names:
        key = raw_provider_name.lower()
        existing = registry.get(key)
        if existing is not None and existing.cluster_id != cluster.cluster_id:
            raise ValueError(f"duplicate raw_provider_name: {raw_provider_name}")
        registry[key] = cluster


class SemanticFieldRegistry:
    """Lookup surface for canonical semantic field clusters."""

    def __init__(self, clusters: tuple[SemanticFieldCluster, ...]) -> None:
        self._clusters = clusters
        (
            self._by_cluster_id,
            self._by_canonical_name,
            self._by_legacy_name,
            self._by_raw_provider_name,
        ) = _build_registry_indexes(clusters)

    @property
    def clusters(self) -> tuple[SemanticFieldCluster, ...]:
        """All registered semantic field clusters."""
        return self._clusters

    def get_by_cluster_id(self, cluster_id: str) -> SemanticFieldCluster | None:
        """Return cluster by cluster ID."""
        return self._by_cluster_id.get(cluster_id.lower())

    def get_by_canonical_name(self, canonical_name: str) -> SemanticFieldCluster | None:
        """Return cluster by canonical field name."""
        return self._by_canonical_name.get(canonical_name.lower())

    def get_by_legacy_name(self, legacy_name: str) -> SemanticFieldCluster | None:
        """Return cluster by legacy field name."""
        return self._by_legacy_name.get(legacy_name.lower())

    def get_by_raw_provider_name(
        self, raw_provider_name: str
    ) -> SemanticFieldCluster | None:
        """Return cluster by provider-native field name."""
        return self._by_raw_provider_name.get(raw_provider_name.lower())
