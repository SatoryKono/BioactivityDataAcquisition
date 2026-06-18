"""Gold schema snapshot registry helpers."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
from typing import Any, cast

from bioetl.domain.contracts import gold as gold_contracts

ROOT = Path(__file__).resolve().parents[2]
GOLD_SNAPSHOT_REGISTRY_PATH = (
    ROOT / "tests" / "fixtures" / "golden" / "gold" / "schema_registry.v1.json"
)
DEFAULT_CONTRACT_VERSION = "1.0.0"
ENTITY_CONTRACT_VERSIONS: dict[str, str] = {
    "chembl_target": "3.0.0",
    "chembl_target_protein_classification": "2.2.0",
}
_ALLOWED_TYPE_NAMES = frozenset({"bool", "float64", "int64", "str"})

_DQ_SENSITIVE_OUTPUTS: dict[str, dict[str, Any]] = {
    "chembl_activity_dq_bundle": {
        "entity": "chembl_activity",
        "snapshot_path": (
            "tests/fixtures/golden/gold/chembl_activity_dq_bundle_v1.json"
        ),
        "required_columns": [
            "entity_id",
            "activity_id",
            "_dq_warn",
            "_dq_error",
            "_index",
            "standard_type",
            "standard_units",
            "target_id",
        ],
        "purpose": (
            "Bounded ChEMBL activity output bundle for DQ- and unit-sensitive "
            "downstream checks."
        ),
    },
    "chembl_assay_dq_bundle": {
        "entity": "chembl_assay",
        "snapshot_path": "tests/fixtures/golden/gold/chembl_assay_dq_bundle_v1.json",
        "required_columns": [
            "entity_id",
            "assay_id",
            "assay_type",
            "confidence_score",
            "_dq_warn",
            "_dq_error",
            "_index",
        ],
        "purpose": (
            "Bounded ChEMBL assay output bundle for DQ-sensitive assay "
            "identity, type, and confidence checks."
        ),
    },
    "composite_molecule_dq_bundle": {
        "entity": "composite_molecule",
        "snapshot_path": (
            "tests/fixtures/golden/gold/composite_molecule_dq_bundle_v1.json"
        ),
        "required_columns": [
            "entity_id",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_source_providers",
            "_enrichment_status",
        ],
        "purpose": (
            "Bounded composite molecule output bundle for persisted DQ and "
            "enrichment provenance."
        ),
    },
    "composite_publication_dq_bundle": {
        "entity": "composite_publication",
        "snapshot_path": (
            "tests/fixtures/golden/gold/composite_publication_dq_bundle_v1.json"
        ),
        "required_columns": [
            "entity_id",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_source",
            "_lookup_method",
            "_original_id",
            "_source_providers",
            "_enrichment_status",
        ],
        "purpose": (
            "Bounded composite publication output bundle for DQ flags and "
            "source-resolution provenance."
        ),
    },
    "pubchem_compound_dq_bundle": {
        "entity": "pubchem_compound",
        "snapshot_path": (
            "tests/fixtures/golden/gold/pubchem_compound_dq_bundle_v1.json"
        ),
        "required_columns": [
            "entity_id",
            "molecule_id",
            "canonical_smiles",
            "molecular_formula",
            "molecular_weight",
            "chemical_standardization_status",
            "_dq_warn",
            "_dq_error",
            "_index",
        ],
        "purpose": (
            "Bounded PubChem compound output bundle for DQ- and "
            "chemical-standardization-sensitive Gold checks."
        ),
    },
    "pubmed_publication_dq_bundle": {
        "entity": "pubmed_publication",
        "snapshot_path": (
            "tests/fixtures/golden/gold/pubmed_publication_dq_bundle_v1.json"
        ),
        "required_columns": [
            "entity_id",
            "pmid",
            "title",
            "publication_year",
            "_source",
            "_lookup_method",
            "_original_id",
            "_dq_warn",
            "_dq_error",
            "_index",
        ],
        "purpose": (
            "Bounded strict Gold publication output bundle for DQ-sensitive "
            "publication inspection paths."
        ),
    },
}


def _camel_to_snake(name: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def _class_to_entity(schema_name: str) -> str:
    base = schema_name.removesuffix("GoldSchema")
    normalized = (
        base.replace("ChEMBL", "Chembl")
        .replace("PubChem", "Pubchem")
        .replace("PubMed", "Pubmed")
        .replace("UniProt", "Uniprot")
        .replace("IDMapping", "Idmapping")
        .replace("OpenAlex", "Openalex")
        .replace("CrossRef", "Crossref")
        .replace("SemanticScholar", "Semanticscholar")
    )
    entity = _camel_to_snake(normalized)
    return {
        "chembl_document": "chembl_publication",
        "chembl_document_similarity": "chembl_publication_similarity",
        "chembl_document_term": "chembl_publication_term",
    }.get(entity, entity)


def _gold_schema_classes() -> dict[str, type[Any]]:
    schema_classes: dict[str, type[Any]] = {}
    for export_name in gold_contracts.__all__:
        export_obj = getattr(gold_contracts, export_name)
        if not isinstance(export_name, str) or not export_name.endswith("GoldSchema"):
            continue
        schema_classes[_class_to_entity(export_name)] = cast(type[Any], export_obj)
    return dict(sorted(schema_classes.items()))


def _published_contract_path(entity: str) -> str:
    version = ENTITY_CONTRACT_VERSIONS.get(entity, DEFAULT_CONTRACT_VERSION)
    major_minor = ".".join(version.split(".")[:2])
    return f"docs/04-reference/contracts/gold/{entity}_v{major_minor}.json"


def _canonical_dtype_name(dtype: object) -> str:
    rendered = str(dtype).strip().lower()
    return {
        "boolean": "bool",
        "string": "str",
    }.get(rendered, rendered)


def _field_snapshot(schema_cls: type[Any]) -> dict[str, dict[str, Any]]:
    schema = schema_cls.to_schema()
    fields: dict[str, dict[str, Any]] = {}
    for field_name, column in schema.columns.items():
        fields[field_name] = {
            "dtype": _canonical_dtype_name(column.dtype),
            "nullable": bool(column.nullable),
            "description": column.description or "",
        }
    return dict(sorted(fields.items()))


def build_gold_schema_snapshot_registry() -> dict[str, Any]:
    entities: dict[str, Any] = {}
    for entity, schema_cls in _gold_schema_classes().items():
        strict = bool(getattr(getattr(schema_cls, "Config", None), "strict", False))
        entities[entity] = {
            "contract_version": ENTITY_CONTRACT_VERSIONS.get(
                entity,
                DEFAULT_CONTRACT_VERSION,
            ),
            "schema_class": schema_cls.__name__,
            "published_contract_path": _published_contract_path(entity),
            "strict": strict,
            "fields": _field_snapshot(schema_cls),
        }

    return {
        "surface": "gold_schema_snapshots",
        "version": 1,
        "contract_version": DEFAULT_CONTRACT_VERSION,
        "entities": entities,
        "dq_sensitive_outputs": _DQ_SENSITIVE_OUTPUTS,
    }


def load_gold_schema_snapshot_registry() -> dict[str, Any]:
    with GOLD_SNAPSHOT_REGISTRY_PATH.open(encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


def save_gold_schema_snapshot_registry(snapshot: Mapping[str, Any]) -> None:
    GOLD_SNAPSHOT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GOLD_SNAPSHOT_REGISTRY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")


def gold_schema_entities() -> dict[str, type[Any]]:
    return _gold_schema_classes()


def assert_gold_schema_snapshot_registry_shape(snapshot: Mapping[str, Any]) -> None:
    assert snapshot.get("surface") == "gold_schema_snapshots"
    assert snapshot.get("version") == 1
    assert snapshot.get("contract_version") == DEFAULT_CONTRACT_VERSION

    entities = snapshot.get("entities")
    assert isinstance(entities, dict) and entities
    for entity, entry in entities.items():
        assert isinstance(entity, str) and entity
        assert isinstance(entry, dict)
        assert (
            isinstance(entry.get("contract_version"), str) and entry["contract_version"]
        )
        assert isinstance(entry.get("schema_class"), str) and entry["schema_class"]
        assert isinstance(entry.get("published_contract_path"), str)
        assert isinstance(entry.get("strict"), bool)
        fields = entry.get("fields")
        assert isinstance(fields, dict) and fields
        for field_name, field_meta in fields.items():
            assert isinstance(field_name, str) and field_name
            assert isinstance(field_meta, dict)
            assert field_meta.get("dtype") in _ALLOWED_TYPE_NAMES
            assert isinstance(field_meta.get("nullable"), bool)
            assert isinstance(field_meta.get("description"), str)

    dq_sensitive_outputs = snapshot.get("dq_sensitive_outputs")
    assert isinstance(dq_sensitive_outputs, dict) and dq_sensitive_outputs
    for snapshot_name, output_meta in dq_sensitive_outputs.items():
        assert isinstance(snapshot_name, str) and snapshot_name
        assert isinstance(output_meta, dict)
        assert output_meta.get("entity") in entities
        assert isinstance(output_meta.get("snapshot_path"), str)
        required_columns = output_meta.get("required_columns")
        assert isinstance(required_columns, list) and required_columns
        assert all(isinstance(column, str) and column for column in required_columns)
        assert isinstance(output_meta.get("purpose"), str) and output_meta["purpose"]


def assert_gold_schema_entity_matches_snapshot(
    entity: str,
    *,
    update_snapshots: bool = False,
) -> None:
    import pytest

    actual_registry = build_gold_schema_snapshot_registry()
    actual_entity = actual_registry["entities"][entity]
    stored_registry = load_gold_schema_snapshot_registry()
    stored_entities = cast(dict[str, Any], stored_registry.get("entities", {}))

    if update_snapshots:
        updated_registry = dict(stored_registry)
        updated_entities = dict(stored_entities)
        updated_entities[entity] = actual_entity
        updated_registry["entities"] = updated_entities
        updated_registry["dq_sensitive_outputs"] = actual_registry[
            "dq_sensitive_outputs"
        ]
        save_gold_schema_snapshot_registry(updated_registry)
        pytest.skip(f"Updated Gold schema snapshot for {entity}")

    if entity not in stored_entities:
        pytest.fail(
            f"Gold schema snapshot registry is missing entity {entity!r}. "
            "Run with UPDATE_SNAPSHOTS=1 to refresh the registry."
        )

    expected_entity = stored_entities[entity]
    if actual_entity == expected_entity:
        return

    expected_fields = cast(dict[str, Any], expected_entity["fields"])
    actual_fields = cast(dict[str, Any], actual_entity["fields"])
    added_fields = sorted(set(actual_fields) - set(expected_fields))
    removed_fields = sorted(set(expected_fields) - set(actual_fields))
    changed_fields = sorted(
        field_name
        for field_name in actual_fields.keys() & expected_fields.keys()
        if actual_fields[field_name] != expected_fields[field_name]
    )

    lines = [f"{entity}: Gold schema snapshot drift detected"]
    if expected_entity.get("strict") != actual_entity.get("strict"):
        lines.append(
            f"  strict: expected {expected_entity.get('strict')!r}, "
            f"got {actual_entity.get('strict')!r}"
        )
    if added_fields:
        lines.append("  added_fields: " + ", ".join(added_fields))
    if removed_fields:
        lines.append("  removed_fields: " + ", ".join(removed_fields))
    if changed_fields:
        lines.append("  changed_fields: " + ", ".join(changed_fields))
    lines.append(
        "If intentional, run: UPDATE_SNAPSHOTS=1 "
        "pytest tests/contract/test_gold_schema_snapshot_registry.py"
    )
    pytest.fail("\n".join(lines))
