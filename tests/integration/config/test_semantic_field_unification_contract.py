"""Contract checks for canonical semantic field unification surfaces."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from bioetl.domain.mapping.molecule_fields import MOLECULE_FIELD_MAPPING
from bioetl.domain.mapping.publication_fields import PUBLICATION_FIELD_MAPPING
from bioetl.domain.registry.field_aliases import MOLECULE_FIELD_ALIASES
from bioetl.domain.registry.semantic_fields import SemanticFieldRegistry
from bioetl.infrastructure.config.semantic_field_registry_loader import (
    SemanticFieldRegistryLoader,
)

GENERIC_LEXICAL_COLLISIONS = frozenset(
    {"type", "value", "score", "description", "relation", "source"}
)
PUBLICATION_GOLD_CONTRACTS = (
    "docs/04-reference/contracts/gold/chembl_publication_v1.0.json",
    "docs/04-reference/contracts/gold/crossref_publication_v1.0.json",
    "docs/04-reference/contracts/gold/openalex_publication_v1.0.json",
    "docs/04-reference/contracts/gold/pubmed_publication_v1.0.json",
    "docs/04-reference/contracts/gold/semanticscholar_publication_v1.0.json",
)
PUBLICATION_TITLE_REQUIRED_GOLD_CONTRACTS = (
    *PUBLICATION_GOLD_CONTRACTS,
    "docs/04-reference/contracts/gold/composite_publication_v1.0.json",
)
PUBLICATION_CONFIGS = (
    "configs/entities/chembl/publication.yaml",
    "configs/entities/crossref/publication.yaml",
    "configs/entities/openalex/publication.yaml",
    "configs/entities/pubmed/publication.yaml",
    "configs/entities/semanticscholar/publication.yaml",
)


def _load_yaml(path: str) -> dict[str, object]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _field_validations(
    config: dict[str, object], field: str
) -> list[dict[str, object]]:
    quality = config["quality"]
    assert isinstance(quality, dict)
    validations = quality["entity_field_validations"]
    assert isinstance(validations, list)
    return [
        validation
        for validation in validations
        if isinstance(validation, dict) and validation.get("field") == field
    ]
def _assert_alias_resolves_to_canonical(
    registry: SemanticFieldRegistry,
    *,
    raw_name: str,
    canonical_name: str,
) -> None:
    canonical_cluster = registry.get_by_canonical_name(canonical_name)
    assert canonical_cluster is not None, canonical_name
    if raw_name == canonical_name:
        return
    alias_cluster = registry.get_by_legacy_name(raw_name)
    if alias_cluster is None:
        alias_cluster = registry.get_by_raw_provider_name(raw_name)
    assert alias_cluster == canonical_cluster, (raw_name, canonical_name)


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


def test_input_filters_map_legacy_provider_columns_to_canonical_runtime_fields() -> (
    None
):
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

    assay_keys = {item["field"] for item in assay["quality"]["key_nullability"]}
    molecule_keys = {item["field"] for item in molecule["quality"]["key_nullability"]}
    pubmed_keys = {item["field"] for item in pubmed["quality"]["key_nullability"]}

    assert "assay_id" in assay_keys
    assert "assay_chembl_id" not in assay_keys
    assert "molecule_id" in molecule_keys
    assert "molecule_chembl_id" not in molecule_keys
    assert "pmid" in pubmed_keys
    assert "pubmed_id" not in pubmed_keys


def test_publication_field_mapping_clusters_are_registry_backed() -> None:
    registry = SemanticFieldRegistryLoader(Path("configs")).load()
    checked_mappings = 0

    for mapping in PUBLICATION_FIELD_MAPPING.values():
        for raw_name, canonical_name in mapping.items():
            _assert_alias_resolves_to_canonical(
                registry,
                raw_name=raw_name,
                canonical_name=canonical_name,
            )
            checked_mappings += 1

    assert checked_mappings > 0


def test_molecule_mapping_and_alias_clusters_are_registry_backed() -> None:
    registry = SemanticFieldRegistryLoader(Path("configs")).load()

    for mapping in MOLECULE_FIELD_MAPPING.values():
        for raw_name, canonical_name in mapping.items():
            _assert_alias_resolves_to_canonical(
                registry,
                raw_name=raw_name,
                canonical_name=canonical_name,
            )

    for field_alias in MOLECULE_FIELD_ALIASES:
        assert registry.get_by_canonical_name(field_alias.canonical_name) is not None
        for raw_name in field_alias.provider_aliases.values():
            _assert_alias_resolves_to_canonical(
                registry,
                raw_name=raw_name,
                canonical_name=field_alias.canonical_name,
            )


def test_generic_lexical_collisions_are_not_canonicalized() -> None:
    registry = SemanticFieldRegistryLoader(Path("configs")).load()

    for field_name in GENERIC_LEXICAL_COLLISIONS:
        assert registry.get_by_canonical_name(field_name) is None


def test_publication_year_gold_nullable_number_compatibility_is_documented() -> None:
    silver_source = Path(
        "src/bioetl/domain/schemas/common/publication_base.py"
    ).read_text(encoding="utf-8")
    gold_source = Path(
        "src/bioetl/domain/contracts/gold/_publication_common_schema.py"
    ).read_text(encoding="utf-8")
    gold_docs = Path("docs/04-reference/contracts/gold-schemas.md").read_text(
        encoding="utf-8"
    )

    assert "publication_year: Series[pd.Int64Dtype]" in silver_source
    assert "publication_year: Series[float]" in gold_source
    assert "coerce=True" in gold_source
    assert "Publication Nullable Integer Compatibility" in gold_docs

    for contract_path in PUBLICATION_GOLD_CONTRACTS:
        payload = _load_json(contract_path)
        properties = payload["properties"]
        assert isinstance(properties, dict)
        publication_year = properties["publication_year"]
        assert isinstance(publication_year, dict)
        assert publication_year["type"] == ["number", "null"]
        assert publication_year["nullable"] is True


def test_publication_title_requiredness_is_aligned_across_gold_and_dq() -> None:
    for contract_path in PUBLICATION_TITLE_REQUIRED_GOLD_CONTRACTS:
        contract = _load_json(contract_path)
        properties = contract["properties"]
        required = contract["required"]
        assert isinstance(properties, dict)
        assert isinstance(required, list)
        assert "title" in properties, contract_path
        assert "title" in required, contract_path
        title = properties["title"]
        assert isinstance(title, dict)
        assert title["nullable"] is False

    for config_path in PUBLICATION_CONFIGS:
        config = _load_yaml(config_path)
        validations = _field_validations(config, "title")
        by_type = {
            str(validation.get("type")): validation for validation in validations
        }
        assert {"max_length", "not_null", "pattern"} <= set(by_type), config_path
        for validation_type in ("max_length", "not_null", "pattern"):
            assert by_type[validation_type]["nullable"] is False, config_path
            assert by_type[validation_type].get("severity", "error") == "error"


def test_publication_identifier_dq_rules_use_canonical_patterns() -> None:
    expected_patterns = {
        "doi": r"^10\.\d{4,}/\S+$",
        "pmid": r"^[1-9]\d{0,9}$",
        "pmc_id": r"^PMC\d+$",
    }
    for config_path in PUBLICATION_CONFIGS:
        config = _load_yaml(config_path)
        for field, pattern in expected_patterns.items():
            validations = _field_validations(config, field)
            if not validations and config_path.endswith("chembl/publication.yaml"):
                validations = _field_validations(config, f"publication_{field}")
            assert any(
                validation.get("type") == "pattern"
                and validation.get("pattern") == pattern
                for validation in validations
            ), (config_path, field)

    chembl = _load_yaml("configs/entities/chembl/publication.yaml")
    publication_pmid_rules = _field_validations(chembl, "publication_pmid")
    assert any(
        rule.get("type") == "pattern"
        and rule.get("pattern") == expected_patterns["pmid"]
        for rule in publication_pmid_rules
    )
