#!/usr/bin/env python3
"""Generate Gold JSON contracts from Pandera DataFrameModel schemas.

Usage:
    python -m scripts.schema generate-contracts
"""

from __future__ import annotations

import argparse
import inspect
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlunsplit

from bioetl.domain.contracts import gold as gold_contracts
from bioetl.domain.contracts.gold.chembl_target_classification import (
    ChEMBLTargetGoldSchemaV31,
    ChEMBLTargetGoldSchemaV32,
    target_v31_schema_hash,
    target_v32_schema_hash,
)
from bioetl.domain.contracts.gold.composite_bioassay import (
    COMPOSITE_TARGET_GOLD_VERSION,
)
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v32_normalization_profile,
)
from bioetl.domain.normalization.profiles import (
    resolve_normalization_profile_identity,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_VERSION = "1.0.0"
ENTITY_CONTRACT_VERSIONS: dict[str, str] = {
    "chembl_assay_parameters": "2.0.0",
    "chembl_publication_similarity": "2.0.0",
    "chembl_target": "3.0.0",
    "chembl_target_protein_classification": "2.2.0",
    "composite_target": COMPOSITE_TARGET_GOLD_VERSION,
}


def _detail_logical_contract() -> dict[str, dict[str, str]]:
    """Logical array and struct annotations copied onto the 3.2.0 contract."""
    string_set = {
        "x-bioetl-logical-type": "set<string>",
        "x-bioetl-serialization": "canonical-json-string",
        "x-bioetl-order": "lexicographic",
        "x-bioetl-null": "not-computed",
        "x-bioetl-empty": "[]",
        "x-bioetl-content-hash": "include",
    }
    scalar = {
        "x-bioetl-null": "not-computed",
        "x-bioetl-content-hash": "include",
    }
    contract = {
        "iuphar_type_raw": {"x-bioetl-logical-type": "string", **scalar},
        "iuphar_source_completeness": {
            "x-bioetl-logical-type": "enum",
            "x-bioetl-enum": "family_only|source_unavailable|typed|unannotated",
            **scalar,
        },
        "iuphar_family_paths": {
            "x-bioetl-logical-type": (
                "set<struct<family_id:string,root_to_leaf:list<string>>>"
            ),
            "x-bioetl-serialization": "canonical-json-string",
            "x-bioetl-order": "family_id,root_to_leaf",
            "x-bioetl-path-order": "root-to-leaf",
            "x-bioetl-null": "not-computed",
            "x-bioetl-empty": "[]",
            "x-bioetl-content-hash": "include",
        },
        "local_status": {
            "x-bioetl-logical-type": "enum",
            "x-bioetl-enum": "candidate_only|conflicting|not_supported|supported",
            **scalar,
        },
        "classification_evidence_refs": {
            "x-bioetl-logical-type": (
                "struct<local_evidence_ids:set<string>,match_evidence_ids:set<string>>"
            ),
            "x-bioetl-serialization": "canonical-json-string",
            "x-bioetl-order": "lexicographic-members",
            "x-bioetl-null": "not-computed",
            "x-bioetl-empty": '{"local_evidence_ids":[],"match_evidence_ids":[]}',
            "x-bioetl-content-hash": "include",
        },
    }
    for name in (
        "iuphar_family_ids",
        "iuphar_subclasses",
        "local_subclasses",
        "local_rule_ids",
        "effective_subclasses",
        "conflict_codes",
    ):
        contract[name] = dict(string_set)
    return contract


JSON_SCHEMA_DRAFT7_URI = urlunsplit(
    ("http", "json-schema.org", "/draft-07/schema", "", "")
)
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "04-reference" / "contracts" / "gold"

SEMANTIC_INTEGER_TYPE_OVERRIDES: frozenset[tuple[str, str]] = frozenset(
    {
        ("composite_activity", "record_id"),
        ("composite_activity", "src_id"),
        ("composite_activity", "taxonomy_id"),
        ("composite_assay", "src_id"),
        ("composite_publication", "src_id"),
        ("composite_target", "taxonomy_id"),
    }
)
ENTITY_NAME_OVERRIDES: dict[str, str] = {
    "chembl_document": "chembl_publication",
    "chembl_document_similarity": "chembl_publication_similarity",
    "chembl_document_term": "chembl_publication_term",
}
RETAINED_LEGACY_CONTRACT_FILENAMES: frozenset[str] = frozenset(
    {
        "chembl_assay_parameters_v1.0.json",
        "chembl_publication_similarity_v1.0.json",
        "composite_target_v1.0.json",
    }
)


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
    return ENTITY_NAME_OVERRIDES.get(entity, entity)


def _filename_from_version(entity: str, version: str) -> str:
    major_minor = ".".join(version.split(".")[:2])
    return f"{entity}_v{major_minor}.json"


def _contract_version_for_entity(entity: str) -> str:
    return ENTITY_CONTRACT_VERSIONS.get(entity, DEFAULT_CONTRACT_VERSION)


def _normalize_export_field_name(column_name: str) -> str:
    if column_name.endswith("_chembl_id"):
        return column_name.replace("_chembl_id", "_id")
    return column_name


def _map_dtype_to_json_type(dtype_value: Any) -> str:
    dtype_str = str(dtype_value).lower()
    if dtype_str in {"str", "string[pyarrow]"}:
        return "string"
    if dtype_str == "float64":
        return "number"
    if dtype_str == "int64":
        return "integer"
    if dtype_str in {"bool", "boolean"}:
        return "boolean"
    return "object"


def _build_property_schema(
    column: Any,
    json_schema_property: dict[str, Any],
    *,
    semantic_integer: bool = False,
) -> dict[str, Any]:
    base_type = "integer" if semantic_integer else _map_dtype_to_json_type(column.dtype)
    json_type: str | list[str]
    if column.nullable:
        json_type = [base_type, "null"]
    else:
        json_type = base_type

    return {
        "type": json_type,
        "nullable": bool(column.nullable),
        "description": column.description
        or json_schema_property.get("description")
        or "",
    }


def _build_contract(
    schema_cls: type[Any],
    entity: str,
    version: str,
) -> dict[str, Any]:
    schema = schema_cls.to_schema()
    json_schema = schema_cls.to_json_schema()

    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for column_name, column in schema.columns.items():
        property_from_json_schema = json_schema.get("properties", {}).get(
            column_name, {}
        )
        export_name = _normalize_export_field_name(column_name)
        properties[export_name] = _build_property_schema(
            column,
            property_from_json_schema,
            semantic_integer=(entity, export_name) in SEMANTIC_INTEGER_TYPE_OVERRIDES,
        )
        if not column.nullable:
            required.append(export_name)

    provider, entity_type = entity.split("_", maxsplit=1)
    profile_identity = resolve_normalization_profile_identity(provider, entity_type)
    contract_payload: dict[str, Any] = {
        "$schema": f"{JSON_SCHEMA_DRAFT7_URI}#",
        "$version": version,
        "title": f"{schema_cls.__name__} Contract",
        "description": (
            f"Gold layer data contract for {entity}. "
            f"Auto-generated from Pandera schema {schema_cls.__name__}."
        ),
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }
    if profile_identity is not None:
        contract_payload["normalization_profile"] = {
            "ref": profile_identity.profile_name,
            "version": profile_identity.profile_version,
            "hash": profile_identity.profile_hash,
        }
    if entity == "chembl_publication_similarity":
        public_pair = {
            "required": ["publication_id1", "publication_id2"],
            "properties": {
                name: {"type": "string", "pattern": "^CHEMBL[1-9][0-9]*$"}
                for name in ("publication_id1", "publication_id2")
            },
        }
        # Draft 7 can express completeness, but not inequality between fields.
        # Silver/Gold dataframe validation also rejects self-pairs.
        contract_payload["anyOf"] = [
            public_pair,
            {
                "required": ["doc_1", "doc_2"],
                "properties": {
                    "doc_1": {"type": "integer", "minimum": 1},
                    "doc_2": {"type": "integer", "minimum": 1},
                    "publication_id1": {"type": "null"},
                    "publication_id2": {"type": "null"},
                },
            },
        ]
    return contract_payload


def _remove_stale_contracts(active_filenames: set[str]) -> None:
    retained_filenames = active_filenames | RETAINED_LEGACY_CONTRACT_FILENAMES
    for contract_path in sorted(CONTRACTS_DIR.glob("*.json")):
        if contract_path.name in retained_filenames:
            continue
        contract_path.unlink()
        print(f"Removed stale contract {contract_path}")


def _active_contract_filenames(schema_classes: list[type[Any]]) -> set[str]:
    filenames: set[str] = set()
    for schema_cls in schema_classes:
        entity = _class_to_entity(schema_cls.__name__)
        filenames.add(
            _filename_from_version(entity, _contract_version_for_entity(entity))
        )
    return filenames


def _schema_classes() -> list[type[Any]]:
    schema_classes: list[type[Any]] = []
    for export_name in gold_contracts.__all__:
        export_obj = getattr(gold_contracts, export_name)
        if inspect.isclass(export_obj) and export_name.endswith("GoldSchema"):
            schema_classes.append(export_obj)
    schema_classes.sort(key=lambda cls: cls.__name__)
    return schema_classes


def _expected_artifacts() -> dict[Path, str]:
    schema_classes = _schema_classes()
    artifacts: dict[Path, str] = {}

    for schema_cls in schema_classes:
        entity = _class_to_entity(schema_cls.__name__)
        contract_version = _contract_version_for_entity(entity)
        filename = _filename_from_version(entity, contract_version)
        output_path = CONTRACTS_DIR / filename

        current_contract = _build_contract(schema_cls, entity, contract_version)
        if entity == "composite_target":
            profile_hash = current_contract["properties"]["target_class_profile_sha256"]
            profile_hash["pattern"] = "^[0-9a-f]{64}$"
        artifacts[output_path] = (
            json.dumps(current_contract, indent=2, ensure_ascii=False) + "\n"
        )

    # The active V30 export remains byte-for-byte stable while V31 is opt-in.
    target_v31 = _build_contract(ChEMBLTargetGoldSchemaV31, "chembl_target", "3.1.0")
    profile_hash = target_v31["properties"]["target_class_profile_sha256"]
    profile_hash["pattern"] = "^[0-9a-f]{64}$"
    target_v31["x-bioetl-schema-sha256"] = target_v31_schema_hash()
    artifacts[CONTRACTS_DIR / "chembl_target_v3.1.json"] = (
        json.dumps(target_v31, indent=2, ensure_ascii=False) + "\n"
    )
    # V32 is selected only by an explicit table contract. V30 and V31 stay stable.
    target_v32 = _build_contract(ChEMBLTargetGoldSchemaV32, "chembl_target", "3.2.0")
    profile_hash_v32 = target_v32["properties"]["target_class_profile_sha256"]
    profile_hash_v32["pattern"] = "^[0-9a-f]{64}$"
    for name, annotation in _detail_logical_contract().items():
        target_v32["properties"][name].update(annotation)
    detail_profile = target_v32_normalization_profile().identity
    target_v32["normalization_profile"] = {
        "ref": detail_profile.profile_name,
        "version": detail_profile.profile_version,
        "hash": detail_profile.profile_hash,
    }
    target_v32["x-bioetl-schema-sha256"] = target_v32_schema_hash()
    target_v32["x-bioetl-physical-contract"] = "3.2.0"
    target_v32["x-bioetl-computational-contract"] = "independent"
    artifacts[CONTRACTS_DIR / "chembl_target_v3.2.json"] = (
        json.dumps(target_v32, indent=2, ensure_ascii=False) + "\n"
    )

    return artifacts


def _stale_artifacts(expected: dict[Path, str]) -> list[Path]:
    stale = [
        path
        for path, content in expected.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    active_contracts = {path.name for path in expected if path.parent == CONTRACTS_DIR}
    stale.extend(
        path
        for path in sorted(CONTRACTS_DIR.glob("*.json"))
        if path.name not in active_contracts
        and path.name not in RETAINED_LEGACY_CONTRACT_FILENAMES
    )
    return sorted(set(stale))


def generate_contracts(*, check: bool = False) -> int:
    expected = _expected_artifacts()
    stale = _stale_artifacts(expected)
    if check:
        if stale:
            for path in stale:
                print(f"Stale generated artifact: {path}")
            return 1
        print("Gold contract artifacts are current")
        return 0

    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    _remove_stale_contracts(
        {path.name for path in expected if path.parent == CONTRACTS_DIR}
    )
    for output_path, content in expected.items():
        output_path.write_text(content, encoding="utf-8")
        print(f"Generated {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for schema router compatibility."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated contracts are stale without writing files.",
    )
    args = parser.parse_args(argv)
    return generate_contracts(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
