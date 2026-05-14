"""Semantic field registry types and lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SemanticFieldCluster",
    "SemanticFieldRegistry",
]


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


class SemanticFieldRegistry:
    """Lookup surface for canonical semantic field clusters."""

    def __init__(self, clusters: tuple[SemanticFieldCluster, ...]) -> None:
        self._clusters = clusters
        self._by_cluster_id: dict[str, SemanticFieldCluster] = {}
        self._by_canonical_name: dict[str, SemanticFieldCluster] = {}
        self._by_legacy_name: dict[str, SemanticFieldCluster] = {}

        for cluster in clusters:
            cluster_id = cluster.cluster_id.lower()
            canonical_name = cluster.canonical_name.lower()
            if cluster_id in self._by_cluster_id:
                raise ValueError(f"duplicate cluster_id: {cluster.cluster_id}")
            if canonical_name in self._by_canonical_name:
                raise ValueError(f"duplicate canonical_name: {cluster.canonical_name}")
            self._by_cluster_id[cluster_id] = cluster
            self._by_canonical_name[canonical_name] = cluster
            for legacy_name in cluster.legacy_names:
                key = legacy_name.lower()
                if key in self._by_legacy_name:
                    raise ValueError(f"duplicate legacy_name: {legacy_name}")
                self._by_legacy_name[key] = cluster

    @property
    def clusters(self) -> tuple[SemanticFieldCluster, ...]:
        """All registered semantic field clusters."""
        return self._clusters

    def get_by_cluster_id(self, cluster_id: str) -> SemanticFieldCluster | None:
        """Return cluster by cluster ID."""
        return self._by_cluster_id.get(cluster_id.lower())

    def get_by_canonical_name(
        self, canonical_name: str
    ) -> SemanticFieldCluster | None:
        """Return cluster by canonical field name."""
        return self._by_canonical_name.get(canonical_name.lower())

    def get_by_legacy_name(self, legacy_name: str) -> SemanticFieldCluster | None:
        """Return cluster by legacy field name."""
        return self._by_legacy_name.get(legacy_name.lower())
