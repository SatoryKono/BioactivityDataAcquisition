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


@pytest.fixture
def snapshots_dir() -> Path:
    """Get snapshots directory path."""
    return Path(__file__).parent / "snapshots"


def extract_field_metadata(schema_class: type[pa.DataFrameModel]) -> dict[str, Any]:
    """Extract field metadata from Pandera schema.

    Returns:
        Dict with field name as key, metadata dict as value.
        Metadata includes: dtype, nullable, checks (regex, range, enum).
    """
    fields = {}

    # Get schema columns
    schema_model = schema_class.to_schema()

    for col_name, col_schema in schema_model.columns.items():
        field_meta = {
            "dtype": _normalize_dtype_name(col_name, str(col_schema.dtype)),
            "nullable": col_schema.nullable,
            "unique": col_schema.unique,
            "coerce": col_schema.coerce,
            "required": col_schema.required,
            "description": col_schema.description or "",
            "checks": [],
        }

        # Extract validation checks
        if col_schema.checks:
            for check in col_schema.checks:
                check_meta = {
                    "name": check.name or check.__class__.__name__,
                }

                # Extract check parameters
                regex_value = None
                if hasattr(check, "regex_pattern"):
                    regex_value = check.regex_pattern
                elif hasattr(check, "pattern"):
                    regex_value = check.pattern
                elif hasattr(check, "regex"):
                    regex_value = check.regex
                elif hasattr(check, "statistics"):
                    stats = getattr(check, "statistics", None)
                    if isinstance(stats, dict):
                        regex_value = stats.get("pattern") or stats.get("regex")

                if regex_value is not None:
                    check_meta["regex"] = str(regex_value)
                if hasattr(check, "_check_fn"):
                    # Extract range checks (ge, le, gt, lt)
                    check_fn_str = str(check._check_fn)
                    if "ge" in check_fn_str or "greater_than_or_equal" in check_fn_str:
                        check_meta["type"] = "ge"
                    elif "le" in check_fn_str or "less_than_or_equal" in check_fn_str:
                        check_meta["type"] = "le"
                    elif "gt" in check_fn_str:
                        check_meta["type"] = "gt"
                    elif "lt" in check_fn_str:
                        check_meta["type"] = "lt"
                    elif "isin" in check_fn_str:
                        check_meta["type"] = "isin"

                field_meta["checks"].append(check_meta)

        fields[col_name] = field_meta

    return fields


def _normalize_dtype_name(field_name: str, dtype_name: str) -> str:
    """Normalize only known compatibility edge-cases used in snapshots."""
    normalized = dtype_name.strip()

    # Historical snapshots store this field as int64 while newer Pandera may expose Int64.
    if field_name == "dosed_ingredient" and normalized == "Int64":
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
