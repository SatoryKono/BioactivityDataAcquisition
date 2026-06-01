"""Tests for the canonical semantic field registry loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.infrastructure.config.semantic_field_registry_loader import (
    SemanticFieldRegistryLoader,
)


pytestmark = pytest.mark.unit

def _write_registry(tmp_path: Path, clusters: list[dict[str, object]]) -> None:
    registry_dir = tmp_path / "field_registry"
    registry_dir.mkdir(parents=True)
    payload = {"version": "1.0.0", "clusters": clusters}
    (registry_dir / "canonical_registry.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_loader_reads_registry_and_supports_lookups(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "cluster_id": "pubmed_identifier",
                "semantic_name": "PubMed publication identifier",
                "canonical_name": "pmid",
                "legacy_names": ["pubmed_id"],
                "raw_provider_names": ["pubmed_id"],
                "pipelines": ["pubmed_publication", "composite_publication"],
                "affected_paths": ["configs/entities/pubmed/publication.yaml"],
                "migration_status": "canonical_internal_with_legacy_input_filter",
                "notes": "Normalized runtime uses pmid.",
            }
        ],
    )

    registry = SemanticFieldRegistryLoader(tmp_path).load()

    cluster = registry.get_by_canonical_name("pmid")
    assert cluster is not None
    assert cluster.cluster_id == "pubmed_identifier"
    assert registry.get_by_legacy_name("pubmed_id") == cluster
    assert registry.get_by_raw_provider_name("pubmed_id") == cluster
    assert registry.get_by_cluster_id("pubmed_identifier") == cluster


def test_loader_rejects_duplicate_legacy_names(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "cluster_id": "pubmed_identifier",
                "semantic_name": "PubMed publication identifier",
                "canonical_name": "pmid",
                "legacy_names": ["pubmed_id"],
                "raw_provider_names": ["pubmed_id"],
                "pipelines": ["pubmed_publication"],
                "affected_paths": ["configs/entities/pubmed/publication.yaml"],
                "migration_status": "canonical_internal_with_legacy_input_filter",
                "notes": "Normalized runtime uses pmid.",
            },
            {
                "cluster_id": "other_identifier",
                "semantic_name": "Duplicate alias test",
                "canonical_name": "other_id",
                "legacy_names": ["pubmed_id"],
                "raw_provider_names": ["pubmed_id"],
                "pipelines": ["other_pipeline"],
                "affected_paths": ["configs/entities/example.yaml"],
                "migration_status": "manual_review",
                "notes": "Should fail duplicate legacy alias validation.",
            },
        ],
    )

    with pytest.raises(ValueError, match="duplicate legacy_name"):
        SemanticFieldRegistryLoader(tmp_path).load()


def test_loader_rejects_duplicate_raw_provider_names(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "cluster_id": "first_identifier",
                "semantic_name": "First identifier",
                "canonical_name": "first_id",
                "legacy_names": [],
                "raw_provider_names": ["source_id"],
                "pipelines": ["first_pipeline"],
                "affected_paths": ["configs/entities/example.yaml"],
                "migration_status": "manual_review",
                "notes": "First raw provider owner.",
            },
            {
                "cluster_id": "second_identifier",
                "semantic_name": "Second identifier",
                "canonical_name": "second_id",
                "legacy_names": [],
                "raw_provider_names": ["source_id"],
                "pipelines": ["second_pipeline"],
                "affected_paths": ["configs/entities/example.yaml"],
                "migration_status": "manual_review",
                "notes": "Should fail duplicate raw provider validation.",
            },
        ],
    )

    with pytest.raises(ValueError, match="duplicate raw_provider_name"):
        SemanticFieldRegistryLoader(tmp_path).load()
