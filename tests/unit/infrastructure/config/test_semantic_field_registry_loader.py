# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
    _write_registry_payload(tmp_path, {"version": "1.0.0", "clusters": clusters})


def _write_registry_payload(tmp_path: Path, payload: dict[str, object]) -> None:
    registry_dir = tmp_path / "field_registry"
    registry_dir.mkdir(parents=True)
    (registry_dir / "canonical_registry.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _valid_cluster(**overrides: object) -> dict[str, object]:
    cluster: dict[str, object] = {
        "cluster_id": "example_identifier",
        "semantic_name": "Example identifier",
        "canonical_name": "example_id",
        "legacy_names": ["legacy_example_id"],
        "raw_provider_names": ["provider_example_id"],
        "pipelines": ["example_pipeline"],
        "affected_paths": ["configs/entities/example.yaml"],
        "migration_status": "manual_review",
        "notes": "Example registry entry.",
    }
    cluster.update(overrides)
    return cluster


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


def test_loader_defaults_missing_list_fields_to_empty_tuples(tmp_path: Path) -> None:
    cluster_payload = _valid_cluster()
    for field_name in (
        "legacy_names",
        "raw_provider_names",
        "pipelines",
        "affected_paths",
    ):
        cluster_payload.pop(field_name)
    _write_registry(tmp_path, [cluster_payload])

    registry = SemanticFieldRegistryLoader(tmp_path).load()

    cluster = registry.get_by_cluster_id("example_identifier")
    assert cluster is not None
    assert cluster.legacy_names == ()
    assert cluster.raw_provider_names == ()
    assert cluster.pipelines == ()
    assert cluster.affected_paths == ()


def test_loader_rejects_non_list_clusters_payload(tmp_path: Path) -> None:
    _write_registry_payload(tmp_path, {"clusters": {"cluster_id": "not-a-list"}})

    with pytest.raises(ValueError, match="clusters must be a list"):
        SemanticFieldRegistryLoader(tmp_path).load()


def test_loader_rejects_non_object_cluster_entry(tmp_path: Path) -> None:
    _write_registry_payload(tmp_path, {"clusters": ["not-an-object"]})

    with pytest.raises(ValueError, match="cluster entries must be objects"):
        SemanticFieldRegistryLoader(tmp_path).load()


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("legacy_names", "legacy_example_id", "legacy_names must be a list"),
        (
            "raw_provider_names",
            [""],
            "raw_provider_names must contain non-empty strings",
        ),
    ],
)
def test_loader_rejects_malformed_string_list_fields(
    field_name: str,
    value: object,
    message: str,
    tmp_path: Path,
) -> None:
    _write_registry(tmp_path, [_valid_cluster(**{field_name: value})])

    with pytest.raises(ValueError, match=message):
        SemanticFieldRegistryLoader(tmp_path).load()


def test_loader_rejects_missing_required_string_field(tmp_path: Path) -> None:
    _write_registry(tmp_path, [_valid_cluster(cluster_id=" ")])

    with pytest.raises(ValueError, match="cluster_id must be a non-empty string"):
        SemanticFieldRegistryLoader(tmp_path).load()
