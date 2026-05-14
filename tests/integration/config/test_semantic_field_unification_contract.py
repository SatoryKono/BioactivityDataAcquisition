"""Contract checks for canonical semantic field unification surfaces."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.infrastructure.config.semantic_field_registry_loader import (
    SemanticFieldRegistryLoader,
)


def _load_yaml(path: str) -> dict[str, object]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_registry_contains_expected_semantic_clusters() -> None:
    registry = SemanticFieldRegistryLoader(Path("configs")).load()

    assert registry.get_by_legacy_name("assay_chembl_id") is not None
    assert registry.get_by_legacy_name("molecule_chembl_id") is not None
    assert registry.get_by_legacy_name("pubmed_id") is not None
    assert registry.get_by_legacy_name("pubmed_title") is not None
    assert registry.get_by_legacy_name("openalex_title") is not None
    assert registry.get_by_canonical_name("assay_id") is not None
    assert registry.get_by_canonical_name("molecule_id") is not None
    assert registry.get_by_canonical_name("pmid") is not None
    assert registry.get_by_canonical_name("title") is not None
    assert registry.get_by_canonical_name("doi") is not None


def test_input_filters_map_legacy_provider_columns_to_canonical_runtime_fields() -> None:
    assay = _load_yaml("configs/entities/chembl/assay.yaml")
    molecule = _load_yaml("configs/entities/chembl/molecule.yaml")
    pubmed = _load_yaml("configs/entities/pubmed/publication.yaml")

    assay_filter = assay["filters"]["input_filter"]
    molecule_filter = molecule["filters"]["input_filter"]
    pubmed_filter = pubmed["filters"]["input_filter"]

    assert assay_filter["column_name"] == "assay_chembl_id"
    assert assay_filter["filter_field"] == "assay_id"
    assert molecule_filter["column_name"] == "molecule_chembl_id"
    assert molecule_filter["filter_field"] == "molecule_id"
    assert pubmed_filter["column_name"] == "pubmed_id"
    assert pubmed_filter["filter_field"] == "pmid"
    assert pubmed_filter["fallback_column"] == "title"


def test_composite_publication_join_keys_stay_canonical() -> None:
    publication = _load_yaml("configs/composites/publication.yaml")
    composite = publication["composite"]

    join_policy = composite["normalized_join_key_policy"]["publication_identity"]
    assert join_policy["primary_join_keys"] == ["doi", "pmid"]
    assert join_policy["fallback_join_keys"] == ["title"]

    enricher_join_keys = {
        enricher["pipeline"]: tuple(enricher["join_keys"])
        for enricher in composite["enrichers"]
    }
    assert enricher_join_keys["crossref_publication"] == ("doi", "title")
    assert enricher_join_keys["openalex_publication"] == ("doi", "title")
    assert enricher_join_keys["pubmed_publication"] == ("pmid", "doi")
    assert enricher_join_keys["semanticscholar_publication"] == ("doi", "title")


def test_entity_quality_surfaces_use_canonical_key_fields() -> None:
    assay = _load_yaml("configs/entities/chembl/assay.yaml")
    molecule = _load_yaml("configs/entities/chembl/molecule.yaml")
    pubmed = _load_yaml("configs/entities/pubmed/publication.yaml")

    assay_keys = {
        item["field"] for item in assay["quality"]["key_nullability"]
    }
    molecule_keys = {
        item["field"] for item in molecule["quality"]["key_nullability"]
    }
    pubmed_keys = {
        item["field"] for item in pubmed["quality"]["key_nullability"]
    }

    assert "assay_id" in assay_keys
    assert "assay_chembl_id" not in assay_keys
    assert "molecule_id" in molecule_keys
    assert "molecule_chembl_id" not in molecule_keys
    assert "pmid" in pubmed_keys
    assert "pubmed_id" not in pubmed_keys
