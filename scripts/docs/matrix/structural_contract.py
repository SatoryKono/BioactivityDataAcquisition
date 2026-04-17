#!/usr/bin/env python3
"""Shared runtime export helpers for ChEMBL matrix structural policy sync."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from bioetl.application.core.base_transformer._structural_policy_contracts import (
    resolve_field_contracts,
    resolve_pandera_schema,
)
from bioetl.application.core.base_transformer.field_policy import FieldPolicyResolver
from bioetl.composition.factories.pipeline._registry_manifest_chembl import (
    CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.infrastructure.config.domain_config_resolver import (
    load_domain_pipeline_config,
)

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_EXPORT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/generated/chembl_matrix_structural_contract_v1.json"
)
CHEMBL_SOURCE_DB: Final[str] = "ChEMBL"
BUSINESS_TYPED_FIELDS: Final[frozenset[str]] = frozenset(
    {"integer", "float", "boolean"}
)
STRUCTURAL_PRESENCE_GUARD: Final[str] = "structural_presence_guard"
STRUCTURAL_TYPE_GUARD: Final[str] = "structural_type_guard"
STRUCTURAL_PRESENCE_VALIDATION: Final[str] = "structural:presence_required"
STRUCTURAL_TYPE_STRICT_VALIDATION: Final[str] = "structural:type_strict"
STRUCTURAL_TYPE_TO_NULL_WARN_VALIDATION: Final[str] = "structural:type_to_null_warn"
STRUCTURAL_OPTIONAL_NONNULLABLE_VALIDATION: Final[str] = (
    "structural:type_proposed_null_warn_error_then_quarantine"
)
STRUCTURAL_CUSTOM_EMPTY_SEMANTICS_VALIDATION: Final[str] = (
    "structural:custom_empty_semantics"
)
STRUCTURAL_NO_STRING_COERCION_VALIDATION: Final[str] = "structural:no_string_coercion"
STRUCTURAL_BOOLEAN_VOCABULARY_VALIDATION: Final[str] = (
    "structural:boolean_vocabulary_override"
)
SET_NULL_AND_WARN: Final[str] = "set_null_and_warn"
QUARANTINE_FILTER_REJECTION: Final[str] = "quarantine_filter_rejection"
PROPOSE_NULL_WARN_ERROR_THEN_QUARANTINE: Final[str] = (
    "propose_null_warn_error_then_quarantine"
)
INVALID_TYPE_TO_NULL: Final[str] = "invalid_type_to_null"
PROPOSED_NULL_THEN_QUARANTINE: Final[str] = "proposed_null_then_quarantine"
QUARANTINE: Final[str] = "quarantine"
NOT_APPLICABLE: Final[str] = "not_applicable"
DEFAULT_REQUIRED_LABEL: Final[str] = "filters, schema"


@dataclass(frozen=True, slots=True)
class StructuralWorkbookSemantics:
    """Canonical structural workbook tokens derived from runtime contract."""

    silver_filter_tokens: tuple[str, ...]
    silver_validation_tokens: tuple[str, ...]
    silver_normalisation_tokens: tuple[str, ...]
    validation_fail_action_prefixes: tuple[str, ...]
    filter_fail_sink: str


@dataclass(frozen=True, slots=True)
class MatrixStructuralContractRow:
    """One export row binding runtime structural contract to workbook keys."""

    source_db: str
    source_table: str
    pipeline: str
    silver_column: str
    logical_type: str
    physical_type: str
    nullable: bool
    optional: bool
    optionality_sources: tuple[str, ...]
    empty_as_missing: bool | None
    coercion_policy: str
    boolean_true_values: tuple[str, ...]
    boolean_false_values: tuple[str, ...]
    is_framework_field: bool
    silver_filter_tokens: tuple[str, ...]
    silver_validation_tokens: tuple[str, ...]
    silver_normalisation_tokens: tuple[str, ...]
    validation_fail_action_prefixes: tuple[str, ...]
    filter_fail_sink: str


def chembl_pipeline_names() -> list[str]:
    """Return registered ChEMBL entity pipeline names in stable order."""
    return sorted({config.pipeline_name for config in CHEMBL_PIPELINE_CONFIGS})


def contract_lookup_key(
    source_db: str, source_table: str, silver_column: str
) -> tuple[str, str, str]:
    """Normalize workbook/export row identity for lookups."""
    return (
        source_db.strip().lower(),
        source_table.strip().lower(),
        silver_column.strip().lower(),
    )


def resolve_required_display(current_required: str, *, optional: bool) -> str:
    """Resolve workbook Required display without erasing richer non-optional labels."""
    if optional:
        return "optional"
    normalized = current_required.strip().lower()
    if normalized and normalized != "optional":
        return current_required
    return DEFAULT_REQUIRED_LABEL


def build_structural_workbook_semantics(
    *,
    logical_type: str,
    nullable: bool,
    optional: bool,
    empty_as_missing: bool | None,
    coercion_policy: str,
    boolean_true_values: tuple[str, ...],
    boolean_false_values: tuple[str, ...],
    is_framework_field: bool,
) -> StructuralWorkbookSemantics:
    """Map runtime structural contract to canonical workbook token overlays."""
    if is_framework_field or logical_type == "unknown":
        return StructuralWorkbookSemantics(
            silver_filter_tokens=(),
            silver_validation_tokens=(),
            silver_normalisation_tokens=(),
            validation_fail_action_prefixes=(),
            filter_fail_sink=NOT_APPLICABLE,
        )

    overlay_validation_tokens: list[str] = []
    if empty_as_missing is not None:
        overlay_validation_tokens.append(STRUCTURAL_CUSTOM_EMPTY_SEMANTICS_VALIDATION)
    if coercion_policy == "no_string_coercion":
        overlay_validation_tokens.append(STRUCTURAL_NO_STRING_COERCION_VALIDATION)
    if boolean_true_values or boolean_false_values:
        overlay_validation_tokens.append(STRUCTURAL_BOOLEAN_VOCABULARY_VALIDATION)

    if not optional and not nullable:
        filter_tokens: tuple[str, ...] = (STRUCTURAL_PRESENCE_GUARD,)
        validation_tokens: tuple[str, ...] = (STRUCTURAL_PRESENCE_VALIDATION,)
        if logical_type in BUSINESS_TYPED_FIELDS:
            filter_tokens = (STRUCTURAL_PRESENCE_GUARD, STRUCTURAL_TYPE_GUARD)
            validation_tokens = (
                STRUCTURAL_PRESENCE_VALIDATION,
                STRUCTURAL_TYPE_STRICT_VALIDATION,
            )
        return StructuralWorkbookSemantics(
            silver_filter_tokens=filter_tokens,
            silver_validation_tokens=(
                *validation_tokens,
                *overlay_validation_tokens,
            ),
            silver_normalisation_tokens=(),
            validation_fail_action_prefixes=(QUARANTINE_FILTER_REJECTION,),
            filter_fail_sink=QUARANTINE,
        )

    if logical_type in BUSINESS_TYPED_FIELDS and nullable:
        return StructuralWorkbookSemantics(
            silver_filter_tokens=(STRUCTURAL_TYPE_GUARD,),
            silver_validation_tokens=(
                STRUCTURAL_TYPE_TO_NULL_WARN_VALIDATION,
                *overlay_validation_tokens,
            ),
            silver_normalisation_tokens=(INVALID_TYPE_TO_NULL,),
            validation_fail_action_prefixes=(SET_NULL_AND_WARN,),
            filter_fail_sink=NOT_APPLICABLE,
        )

    if logical_type in BUSINESS_TYPED_FIELDS and optional and not nullable:
        return StructuralWorkbookSemantics(
            silver_filter_tokens=(STRUCTURAL_TYPE_GUARD,),
            silver_validation_tokens=(
                STRUCTURAL_OPTIONAL_NONNULLABLE_VALIDATION,
                *overlay_validation_tokens,
            ),
            silver_normalisation_tokens=(PROPOSED_NULL_THEN_QUARANTINE,),
            validation_fail_action_prefixes=(PROPOSE_NULL_WARN_ERROR_THEN_QUARANTINE,),
            filter_fail_sink=QUARANTINE,
        )

    return StructuralWorkbookSemantics(
        silver_filter_tokens=(),
        silver_validation_tokens=tuple(overlay_validation_tokens),
        silver_normalisation_tokens=(),
        validation_fail_action_prefixes=(),
        filter_fail_sink=NOT_APPLICABLE,
    )


def build_runtime_contract_rows() -> list[MatrixStructuralContractRow]:
    """Build canonical workbook structural contract rows from current runtime config."""
    pipeline_names = chembl_pipeline_names()
    rows: list[MatrixStructuralContractRow] = []
    for pipeline_name in pipeline_names:
        domain_config = load_domain_pipeline_config(pipeline_name)
        source_table = domain_config.entity_type
        schema_builder = next(
            config.pandera_silver_schema
            for config in CHEMBL_PIPELINE_CONFIGS
            if config.pipeline_name == pipeline_name
        )
        schema = resolve_pandera_schema(schema_builder)
        if schema is None:
            continue
        field_policy_resolver = FieldPolicyResolver.from_domain_config(domain_config)
        for contract in resolve_field_contracts(
            schema=schema,
            field_policy_resolver=field_policy_resolver,
        ):
            semantics = build_structural_workbook_semantics(
                logical_type=contract.logical_type,
                nullable=contract.nullable,
                optional=contract.optional,
                empty_as_missing=contract.empty_as_missing,
                coercion_policy=contract.coercion_policy,
                boolean_true_values=contract.boolean_true_values,
                boolean_false_values=contract.boolean_false_values,
                is_framework_field=contract.is_system_field,
            )
            rows.append(
                MatrixStructuralContractRow(
                    source_db=CHEMBL_SOURCE_DB,
                    source_table=source_table,
                    pipeline=pipeline_name,
                    silver_column=contract.field_name,
                    logical_type=contract.logical_type,
                    physical_type=contract.physical_type,
                    nullable=contract.nullable,
                    optional=contract.optional,
                    optionality_sources=tuple(
                        str(source) for source in contract.optional_sources
                    ),
                    empty_as_missing=contract.empty_as_missing,
                    coercion_policy=contract.coercion_policy,
                    boolean_true_values=contract.boolean_true_values,
                    boolean_false_values=contract.boolean_false_values,
                    is_framework_field=contract.is_system_field,
                    silver_filter_tokens=semantics.silver_filter_tokens,
                    silver_validation_tokens=semantics.silver_validation_tokens,
                    silver_normalisation_tokens=semantics.silver_normalisation_tokens,
                    validation_fail_action_prefixes=semantics.validation_fail_action_prefixes,
                    filter_fail_sink=semantics.filter_fail_sink,
                )
            )

    rows.sort(
        key=lambda row: (
            row.source_db.lower(),
            row.source_table.lower(),
            row.silver_column.lower(),
        )
    )
    return rows


def index_runtime_contract_rows(
    rows: list[MatrixStructuralContractRow],
) -> dict[tuple[str, str, str], MatrixStructuralContractRow]:
    """Build workbook lookup index for runtime contract rows."""
    return {
        contract_lookup_key(row.source_db, row.source_table, row.silver_column): row
        for row in rows
    }


def serialize_runtime_contract_rows(
    rows: list[MatrixStructuralContractRow],
) -> list[dict[str, object]]:
    """Serialize runtime contract rows to JSON-friendly dictionaries."""
    return [asdict(row) for row in rows]


def write_runtime_contract_export(
    path: Path = DEFAULT_CONTRACT_EXPORT,
) -> list[MatrixStructuralContractRow]:
    """Build and persist the canonical ChEMBL runtime structural contract export."""
    rows = build_runtime_contract_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "rows": serialize_runtime_contract_rows(rows),
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return rows


def load_runtime_contract_export(
    path: Path = DEFAULT_CONTRACT_EXPORT,
) -> list[MatrixStructuralContractRow]:
    """Load the persisted runtime structural contract export."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_rows = payload.get("rows", [])
    rows: list[MatrixStructuralContractRow] = []
    for raw_row in raw_rows:
        rows.append(
            MatrixStructuralContractRow(
                source_db=str(raw_row["source_db"]),
                source_table=str(raw_row["source_table"]),
                pipeline=str(raw_row["pipeline"]),
                silver_column=str(raw_row["silver_column"]),
                logical_type=str(raw_row["logical_type"]),
                physical_type=str(raw_row["physical_type"]),
                nullable=bool(raw_row["nullable"]),
                optional=bool(raw_row["optional"]),
                optionality_sources=tuple(
                    str(source) for source in raw_row["optionality_sources"]
                ),
                empty_as_missing=raw_row.get("empty_as_missing"),
                coercion_policy=str(raw_row.get("coercion_policy", "default")),
                boolean_true_values=tuple(
                    str(token) for token in raw_row.get("boolean_true_values", [])
                ),
                boolean_false_values=tuple(
                    str(token) for token in raw_row.get("boolean_false_values", [])
                ),
                is_framework_field=bool(raw_row["is_framework_field"]),
                silver_filter_tokens=tuple(
                    str(token) for token in raw_row["silver_filter_tokens"]
                ),
                silver_validation_tokens=tuple(
                    str(token) for token in raw_row["silver_validation_tokens"]
                ),
                silver_normalisation_tokens=tuple(
                    str(token) for token in raw_row["silver_normalisation_tokens"]
                ),
                validation_fail_action_prefixes=tuple(
                    str(token) for token in raw_row["validation_fail_action_prefixes"]
                ),
                filter_fail_sink=str(raw_row["filter_fail_sink"]),
            )
        )
    return rows


__all__ = [
    "BUSINESS_TYPED_FIELDS",
    "CHEMBL_SOURCE_DB",
    "DEFAULT_CONTRACT_EXPORT",
    "DEFAULT_REQUIRED_LABEL",
    "INVALID_TYPE_TO_NULL",
    "NOT_APPLICABLE",
    "PROPOSED_NULL_THEN_QUARANTINE",
    "QUARANTINE",
    "QUARANTINE_FILTER_REJECTION",
    "SET_NULL_AND_WARN",
    "STRUCTURAL_BOOLEAN_VOCABULARY_VALIDATION",
    "STRUCTURAL_CUSTOM_EMPTY_SEMANTICS_VALIDATION",
    "STRUCTURAL_NO_STRING_COERCION_VALIDATION",
    "MatrixStructuralContractRow",
    "StructuralWorkbookSemantics",
    "build_runtime_contract_rows",
    "build_structural_workbook_semantics",
    "chembl_pipeline_names",
    "contract_lookup_key",
    "index_runtime_contract_rows",
    "load_runtime_contract_export",
    "resolve_required_display",
    "serialize_runtime_contract_rows",
    "write_runtime_contract_export",
]
