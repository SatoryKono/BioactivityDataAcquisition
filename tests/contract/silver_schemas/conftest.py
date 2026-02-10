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
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.pubchem.compound import PubChemCompoundSchema
from bioetl.domain.schemas.uniprot.protein import UniProtProteinSchema
from bioetl.domain.schemas.uniprot.idmapping import UniProtIdMappingSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)

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
    "chembl_target": TargetSchema,
    "chembl_target_component": TargetComponentSchema,
    # PubChem
    "pubchem_compound": PubChemCompoundSchema,
    # UniProt
    "uniprot_protein": UniProtProteinSchema,
    "uniprot_idmapping": UniProtIdMappingSchema,
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
            "dtype": str(col_schema.dtype),
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
                if hasattr(check, "regex_pattern"):
                    check_meta["regex"] = str(check.regex_pattern)
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
