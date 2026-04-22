"""Shared fixtures and utilities for Silver schema contract tests.

Provides introspection utilities to extract field metadata from Pandera schemas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandera as pa
import pytest

# Import all Silver schemas
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.subcellular_fraction import (
    SubcellularFractionSchema,
)
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.chembl.tissue import TissueSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)

# Backward-compatible aliases (legacy naming in tests/docs).
UniProtProteinSchema = UniprotTargetSchema
UniProtIdMappingSchema = IDMappingSchema

# Registry of all Silver schemas
SILVER_SCHEMAS = {
    # ChEMBL
    "chembl_activity": ActivitySchema,
    "chembl_assay": AssaySchema,
    "chembl_assay_parameters": AssayParametersSchema,
    "chembl_cell_line": CellLineSchema,
    "chembl_compound_record": CompoundRecordSchema,
    "chembl_molecule": MoleculeSchema,
    "chembl_protein_class": ProteinClassificationSchema,
    "chembl_publication": ChemblPublicationSchema,
    "chembl_publication_similarity": PublicationSimilaritySchema,
    "chembl_publication_term": PublicationTermSchema,
    "chembl_subcellular_fraction": SubcellularFractionSchema,
    "chembl_target": TargetSchema,
    "chembl_target_component": TargetComponentSchema,
    "chembl_tissue": TissueSchema,
    # PubChem
    "pubchem_compound": PubchemMoleculeSchema,
    # UniProt
    "uniprot_protein": UniprotTargetSchema,
    "uniprot_idmapping": IDMappingSchema,
    # Publications
    "pubmed_publication": PubMedPublicationSchema,
    "crossref_publication": PublicationEnrichedSchema,
    "openalex_publication": OpenAlexPublicationSchema,
    "semanticscholar_publication": SemanticScholarPublicationSchema,
}

# A small representative set used by regular CI as an initial schema-watch gate.
# The goal is fast feedback across distinct pipeline families without paying the
# cost of treating the entire Silver schema surface as a per-PR blocking lane.
REPRESENTATIVE_SILVER_SCHEMAS = (
    "chembl_activity",
    "pubchem_compound",
    "pubmed_publication",
    "uniprot_protein",
)
ALLOWED_ATTR_DIFFS = {
    "_run_id": {"dtype"},
    "_source_batch_id": {"dtype"},
    "molecule_id": {"dtype"},
    "publication_year": {"required"},
}
ALLOWED_CHECK_DIFFS = {"publication_year", "usan_year"}


@pytest.fixture
def snapshots_dir() -> Path:
    """Get snapshots directory path."""
    return Path(__file__).parent / "snapshots"


def _regex_value_for_check(check: Any) -> object | None:
    for attr_name in ("regex_pattern", "pattern", "regex"):
        if hasattr(check, attr_name):
            return getattr(check, attr_name)

    stats = getattr(check, "statistics", None)
    if isinstance(stats, dict):
        return stats.get("pattern") or stats.get("regex")
    return None


def _check_type_for_check(check: Any) -> str | None:
    if not hasattr(check, "_check_fn"):
        return None

    check_fn_str = str(check._check_fn)
    check_type_markers = (
        ("ge", ("ge", "greater_than_or_equal")),
        ("le", ("le", "less_than_or_equal")),
        ("gt", ("gt",)),
        ("lt", ("lt",)),
        ("isin", ("isin",)),
    )
    for check_type, markers in check_type_markers:
        if any(marker in check_fn_str for marker in markers):
            return check_type
    return None


def _check_metadata(check: Any) -> dict[str, Any]:
    check_meta = {"name": check.name or check.__class__.__name__}
    regex_value = _regex_value_for_check(check)
    if regex_value is not None:
        check_meta["regex"] = str(regex_value)

    check_type = _check_type_for_check(check)
    if check_type is not None:
        check_meta["type"] = check_type
    return check_meta


def _field_metadata(col_name: str, col_schema: Any) -> dict[str, Any]:
    field_meta = {
        "dtype": _normalize_dtype_name(col_name, str(col_schema.dtype)),
        "nullable": col_schema.nullable,
        "unique": col_schema.unique,
        "coerce": col_schema.coerce,
        "required": col_schema.required,
        "description": col_schema.description or "",
        "checks": [],
    }
    if col_schema.checks:
        field_meta["checks"] = [_check_metadata(check) for check in col_schema.checks]
    return field_meta


def extract_field_metadata(schema_class: type[pa.DataFrameModel]) -> dict[str, Any]:
    """Extract field metadata from Pandera schema.

    Returns:
        Dict with field name as key, metadata dict as value.
        Metadata includes: dtype, nullable, checks (regex, range, enum).
    """
    schema_model = schema_class.to_schema()
    return {
        col_name: _field_metadata(col_name, col_schema)
        for col_name, col_schema in schema_model.columns.items()
    }


def _normalize_dtype_name(field_name: str, dtype_name: str) -> str:
    """Normalize only known compatibility edge-cases used in snapshots."""
    normalized = dtype_name.strip()

    # Historical snapshots store this field as int64 while newer Pandera may expose Int64.
    legacy_int64_fields = {
        "black_box_warning",
        "chirality",
        "dosed_ingredient",
        "first_in_class",
        "inorganic_flag",
        "natural_product",
        "polymer_flag",
        "prodrug",
    }
    if field_name in legacy_int64_fields and normalized == "Int64":
        return "int64"

    if normalized == "boolean":
        return "bool"

    return normalized


def save_snapshot(
    schema_name: str, snapshot_data: dict[str, Any], snapshots_dir: Path
) -> None:
    """Save schema snapshot to JSON file."""
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshots_dir / f"{schema_name}_schema.json"

    with snapshot_path.open("w") as f:
        json.dump(snapshot_data, f, indent=2, sort_keys=True)


def load_snapshot(schema_name: str, snapshots_dir: Path) -> dict[str, Any] | None:
    """Load schema snapshot from JSON file."""
    snapshot_path = snapshots_dir / f"{schema_name}_schema.json"

    if not snapshot_path.exists():
        return None

    with snapshot_path.open() as f:
        return json.load(f)


def _update_or_create_snapshot(
    *,
    schema_name: str,
    current_metadata: dict[str, Any],
    snapshot: dict[str, Any] | None,
    snapshots_dir: Path,
    update_snapshots: bool,
) -> bool:
    if snapshot is None or update_snapshots:
        save_snapshot(schema_name, current_metadata, snapshots_dir)
        if snapshot is None:
            pytest.skip(f"Created initial snapshot for {schema_name}")
        pytest.skip(f"Updated snapshot for {schema_name} (UPDATE_SNAPSHOTS=1)")
    return False


def _assert_matching_field_sets(
    schema_name: str,
    *,
    current_fields: set[str],
    snapshot_fields: set[str],
) -> None:
    added_fields = current_fields - snapshot_fields
    if added_fields:
        pytest.fail(
            f"{schema_name}: New fields detected: {sorted(added_fields)}\n"
            "If intentional, run: UPDATE_SNAPSHOTS=1 pytest ..."
        )

    removed_fields = snapshot_fields - current_fields
    if removed_fields:
        pytest.fail(
            f"{schema_name}: Fields removed: {sorted(removed_fields)}\n"
            "This is a BREAKING CHANGE. Update downstream consumers first.\n"
            "Then run: UPDATE_SNAPSHOTS=1 pytest ..."
        )


def _assert_field_attributes_match(
    schema_name: str,
    field_name: str,
    *,
    current_field: dict[str, Any],
    snapshot_field: dict[str, Any],
) -> None:
    for attr in ["dtype", "nullable", "required"]:
        if field_name in ALLOWED_ATTR_DIFFS and attr in ALLOWED_ATTR_DIFFS[field_name]:
            continue
        if current_field.get(attr) != snapshot_field.get(attr):
            pytest.fail(
                f"{schema_name}.{field_name}: {attr} changed\n"
                f"  Expected: {snapshot_field.get(attr)}\n"
                f"  Got:      {current_field.get(attr)}\n"
                "If intentional, run: UPDATE_SNAPSHOTS=1 pytest ..."
            )


def _assert_field_checks_match(
    schema_name: str,
    field_name: str,
    *,
    current_field: dict[str, Any],
    snapshot_field: dict[str, Any],
) -> None:
    if field_name in ALLOWED_CHECK_DIFFS:
        return

    current_checks = {c["name"] for c in current_field.get("checks", [])}
    snapshot_checks = {c["name"] for c in snapshot_field.get("checks", [])}

    added_checks = current_checks - snapshot_checks
    removed_checks = snapshot_checks - current_checks
    if added_checks or removed_checks:
        pytest.fail(
            f"{schema_name}.{field_name}: Validation checks changed\n"
            f"  Added:   {sorted(added_checks) if added_checks else 'none'}\n"
            f"  Removed: {sorted(removed_checks) if removed_checks else 'none'}\n"
            "If intentional, run: UPDATE_SNAPSHOTS=1 pytest ..."
        )


def assert_schema_matches_snapshot(
    schema_name: str,
    *,
    snapshots_dir: Path,
    update_snapshots: bool = False,
) -> None:
    """Assert that current schema metadata matches the stored snapshot.

    This helper centralizes schema drift diagnostics so the full suite and the
    representative CI subset share exactly the same matching logic.
    """
    schema_class = SILVER_SCHEMAS[schema_name]

    current_metadata = extract_field_metadata(schema_class)
    snapshot = load_snapshot(schema_name, snapshots_dir)
    _update_or_create_snapshot(
        schema_name=schema_name,
        current_metadata=current_metadata,
        snapshot=snapshot,
        snapshots_dir=snapshots_dir,
        update_snapshots=update_snapshots,
    )
    assert snapshot is not None

    current_fields = set(current_metadata.keys())
    snapshot_fields = set(snapshot.keys())
    _assert_matching_field_sets(
        schema_name,
        current_fields=current_fields,
        snapshot_fields=snapshot_fields,
    )

    for field_name in current_fields:
        current_field = current_metadata[field_name]
        snapshot_field = snapshot[field_name]
        _assert_field_attributes_match(
            schema_name,
            field_name,
            current_field=current_field,
            snapshot_field=snapshot_field,
        )
        _assert_field_checks_match(
            schema_name,
            field_name,
            current_field=current_field,
            snapshot_field=snapshot_field,
        )
