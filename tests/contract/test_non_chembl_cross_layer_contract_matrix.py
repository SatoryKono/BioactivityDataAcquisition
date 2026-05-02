"""Cross-layer contract matrix guards for non-ChEMBL provider surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandera.pandas as pa
import pyarrow as pa_arrow
import yaml

from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema
from bioetl.domain.contracts.gold.publications_crossref import (
    CrossRefPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_openalex import (
    OpenAlexPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_pubmed import PubMedPublicationGoldSchema
from bioetl.domain.contracts.gold.publications_semanticscholar import (
    SemanticScholarPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.uniprot import (
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.domain.normalization.chemical_standardization_contract import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
)
from bioetl.domain.normalization.profiles.pubchem_compound import (
    PUBCHEM_COMPOUND_PROFILE,
)
from bioetl.domain.normalization.structured_payload_policies import (
    StructuredPayloadSemanticPolicy,
    semantic_sensitive_structured_payload_policies,
    structured_payload_policy,
)
from scripts.docs.generate_pipeline_normalization_field_matrix import (
    ENTITY_DOMAIN_SCHEMA_REGISTRY,
    ENTITY_SILVER_SCHEMA_REGISTRY,
    build_field_matrix_rows,
)

FIXTURE_PATH = Path("tests/fixtures/normalization/non_chembl_observed_values.yaml")

GOLD_SCHEMA_REGISTRY: dict[str, type[pa.DataFrameModel]] = {
    "crossref_publication": CrossRefPublicationGoldSchema,
    "openalex_publication": OpenAlexPublicationGoldSchema,
    "pubchem_compound": PubChemCompoundGoldSchema,
    "pubmed_publication": PubMedPublicationGoldSchema,
    "semanticscholar_publication": SemanticScholarPublicationGoldSchema,
    "uniprot_idmapping": UniProtIDMappingGoldSchema,
    "uniprot_protein": UniProtProteinGoldSchema,
}


def _load_fixture() -> dict[str, Any]:
    payload = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _entity_config_path(pipeline_name: str) -> Path:
    provider, entity = pipeline_name.split("_", maxsplit=1)
    return Path("configs/entities") / provider / f"{entity}.yaml"


def _config_fields(path: Path) -> set[str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = payload["schema"]
    fields: set[str] = set()
    for group in schema["column_groups"]:
        fields.update(group.get("fields", ()))
    return fields


def _config_allowed_values(path: Path, field_name: str) -> set[str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    validations = payload["quality"]["entity_field_validations"]
    for rule in validations:
        if rule.get("field") == field_name:
            return {str(value) for value in rule.get("allowed_values", ())}
    raise AssertionError(f"{path}:{field_name} missing enum validation")


def _arrow_fields(schema: pa_arrow.Schema) -> set[str]:
    return set(schema.names)


def _pandera_fields(schema: type[pa.DataFrameModel]) -> set[str]:
    return set(schema.to_schema().columns)


def test_non_chembl_observed_value_fixture_has_cross_layer_field_coverage() -> None:
    fixture = _load_fixture()
    matrix_rows = {
        (row["pipeline_name"], row["field_name"]) for row in build_field_matrix_rows()
    }

    for pipeline_name, spec in fixture["pipelines"].items():
        config_fields = _config_fields(_entity_config_path(pipeline_name))
        silver_fields = _arrow_fields(ENTITY_SILVER_SCHEMA_REGISTRY[pipeline_name])
        domain_fields = _pandera_fields(ENTITY_DOMAIN_SCHEMA_REGISTRY[pipeline_name])
        gold_fields = _pandera_fields(GOLD_SCHEMA_REGISTRY[pipeline_name])
        checked_fields = {
            spec["primary_key"],
            *spec.get("observed_values", {}),
            *spec.get("structured_json_shapes", {}),
        }

        for field_name in checked_fields:
            assert field_name in config_fields, f"{pipeline_name}.{field_name}: config"
            assert field_name in silver_fields, f"{pipeline_name}.{field_name}: Silver"
            assert field_name in domain_fields, f"{pipeline_name}.{field_name}: domain"
            assert field_name in gold_fields, f"{pipeline_name}.{field_name}: Gold"
            assert (pipeline_name, field_name) in matrix_rows, (
                f"{pipeline_name}.{field_name}: generated matrix"
            )


def test_uniprot_protein_matrix_uses_canonical_taxonomy_and_gene_fields() -> None:
    config_fields = _config_fields(Path("configs/entities/uniprot/protein.yaml"))
    silver_fields = _arrow_fields(ENTITY_SILVER_SCHEMA_REGISTRY["uniprot_protein"])
    domain_fields = _pandera_fields(ENTITY_DOMAIN_SCHEMA_REGISTRY["uniprot_protein"])
    gold_fields = _pandera_fields(UniProtProteinGoldSchema)
    matrix_rows = {
        row["field_name"]
        for row in build_field_matrix_rows()
        if row["pipeline_name"] == "uniprot_protein"
    }

    for field_name in (
        "taxonomy_id",
        "gene_primary",
        "gene_synonyms",
        "gene_orf_names",
    ):
        assert field_name in config_fields
        assert field_name in silver_fields
        assert field_name in domain_fields
        assert field_name in gold_fields
        assert field_name in matrix_rows

    for legacy_field in ("organism_id", "gene_names"):
        assert legacy_field not in config_fields
        assert legacy_field not in silver_fields
        assert legacy_field not in domain_fields
        assert legacy_field not in gold_fields
        assert legacy_field not in matrix_rows


def test_structured_payload_observed_shapes_match_policy_registry() -> None:
    fixture = _load_fixture()

    for pipeline_name, spec in fixture["pipelines"].items():
        provider, entity = pipeline_name.split("_", maxsplit=1)
        for field_name, shape in spec.get("structured_json_shapes", {}).items():
            policy = structured_payload_policy(f"{provider}.{entity}", field_name)

            assert policy is not None, f"{pipeline_name}.{field_name}: policy"
            assert (
                shape["semantic_policy"]
                == StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM
            )
            assert shape["semantic_policy"] == policy.semantic_policy
            assert shape["collection_semantics"] == policy.collection_semantics
            assert shape["raw_sidecar_field"] == policy.raw_sidecar_field
            assert shape["canonical_sidecar_field"] == policy.canonical_sidecar_field


def test_pubchem_standardization_status_vocab_is_cross_layer_canonical() -> None:
    fixture = _load_fixture()
    fixture_values = set(
        fixture["pipelines"]["pubchem_compound"]["observed_values"][
            "chemical_standardization_status"
        ]
    )
    config_path = Path("configs/entities/pubchem/compound.yaml")
    config_values = _config_allowed_values(
        config_path,
        "chemical_standardization_status",
    )
    policy_version_values = _config_allowed_values(
        config_path,
        "chemical_standardization_policy_version",
    )
    status_rule = PUBCHEM_COMPOUND_PROFILE.rule_for("chemical_standardization_status")
    policy_rule = PUBCHEM_COMPOUND_PROFILE.rule_for(
        "chemical_standardization_policy_version"
    )

    assert fixture_values == set(CHEMICAL_STANDARDIZATION_STATUSES)
    assert config_values == set(CHEMICAL_STANDARDIZATION_STATUSES)
    assert policy_version_values == {CHEMICAL_STANDARDIZATION_POLICY_VERSION}

    assert status_rule is not None
    for value in CHEMICAL_STANDARDIZATION_STATUSES:
        assert status_rule.apply(f" {value.upper()} ") == value
    assert status_rule.apply("unchanged") is None
    assert status_rule.apply("failed") is None

    assert policy_rule is not None
    assert policy_rule.apply(CHEMICAL_STANDARDIZATION_POLICY_VERSION.upper()) == (
        CHEMICAL_STANDARDIZATION_POLICY_VERSION
    )


def test_structured_payload_sidecar_fields_are_not_in_current_cross_layer_surfaces() -> (
    None
):
    matrix_rows = {
        (row["pipeline_name"], row["field_name"]) for row in build_field_matrix_rows()
    }

    for policy in semantic_sensitive_structured_payload_policies():
        pipeline_name = policy.profile_name.replace(".", "_")
        config_fields = _config_fields(_entity_config_path(pipeline_name))
        silver_fields = _arrow_fields(ENTITY_SILVER_SCHEMA_REGISTRY[pipeline_name])
        domain_fields = _pandera_fields(ENTITY_DOMAIN_SCHEMA_REGISTRY[pipeline_name])
        gold_fields = _pandera_fields(GOLD_SCHEMA_REGISTRY[pipeline_name])

        for sidecar_field in (
            policy.raw_sidecar_field,
            policy.canonical_sidecar_field,
        ):
            assert sidecar_field not in config_fields
            assert sidecar_field not in silver_fields
            assert sidecar_field not in domain_fields
            assert sidecar_field not in gold_fields
            assert (pipeline_name, sidecar_field) not in matrix_rows


def test_target_composite_excludes_no_legacy_uniprot_aliases() -> None:
    target_config = yaml.safe_load(
        Path("configs/composites/target.yaml").read_text(encoding="utf-8")
    )
    excludes = set(
        target_config["composite"]["merge"]["field_selection"]["exclude_fields"]
    )

    assert "uniprot.protein.organism_id" not in excludes
    assert "uniprot.protein.gene_names" not in excludes
    assert "uniprot.protein.features_json" in excludes
