"""Shared minimal row builders for schema contract tests."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pandera.pandas as ppa

from bioetl.domain.normalization.chemical_standardization_contract import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
)

ETL_SYSTEM_ROW: dict[str, Any] = {
    "entity_id": "entity:test-1",
    "content_hash": "a" * 64,
    "_run_id": "00000000-0000-4000-8000-000000000001",
    "_run_type": "incremental",
    "_source_batch_id": None,
    "_ingestion_ts": "2026-01-01T00:00:00+00:00",
    "_index": 0,
    "_dq_warn": False,
    "_dq_error": False,
}

# Valid defaults for columns with regex or domain checks beyond dtype.
COLUMN_DEFAULTS: dict[str, Any] = {
    **ETL_SYSTEM_ROW,
    "accession": "P00742",
    "entry_name": "TRY1_HUMAN",
    "sequence": "MALL",
    "sequence_length": 4,
    "reviewed": True,
    "molecule_id": "CID2244",
    "target_id": "CHEMBL204",
    "uniprot_accession": "P00742",
    "mapping_status": "found",
    "feature_count": 0,
}


def dataframe_from_row(row: dict[str, Any]) -> pd.DataFrame:
    """Return a one-row DataFrame from a column mapping."""
    return pd.DataFrame([row])


def pubchem_identity_row(**overrides: Any) -> dict[str, Any]:
    """Minimal valid PubChem identity shard row."""
    row = {
        **ETL_SYSTEM_ROW,
        "entity_id": "pubchem:2244",
        "molecule_id": "2244",
    }
    row.update(overrides)
    return row


def uniprot_core_row(**overrides: Any) -> dict[str, Any]:
    """Minimal valid UniProt core shard row."""
    row = {
        **ETL_SYSTEM_ROW,
        "entity_id": "uniprot:P00742",
        "accession": "P00742",
        "entry_name": "TRY1_HUMAN",
        "sequence": "MALL",
        "sequence_length": 4,
        "reviewed": True,
    }
    row.update(overrides)
    return row


def minimal_schema_dataframe(schema_cls: type[ppa.DataFrameModel]) -> pd.DataFrame:
    """Build a one-row dataframe that satisfies every column on a Pandera schema."""
    row: dict[str, Any] = {}
    for column_name, column in schema_cls.to_schema().columns.items():
        if column_name in COLUMN_DEFAULTS:
            row[column_name] = COLUMN_DEFAULTS[column_name]
            continue
        dtype_name = str(column.dtype).lower()
        if not column.nullable:
            if dtype_name == "bool":
                row[column_name] = False
            elif "int" in dtype_name:
                row[column_name] = 1
            elif dtype_name == "float64":
                row[column_name] = 0.0
            else:
                row[column_name] = f"value-{column_name}"
        else:
            row[column_name] = None
    frame = pd.DataFrame([row])
    for column_name, column in schema_cls.to_schema().columns.items():
        dtype_name = str(column.dtype).lower()
        if column_name not in frame.columns:
            continue
        if "int" in dtype_name:
            if column.nullable:
                frame[column_name] = pd.Series([row[column_name]], dtype="Int64")
            else:
                frame[column_name] = pd.Series([row[column_name]], dtype="int64")
        elif dtype_name == "bool":
            if column.nullable:
                frame[column_name] = pd.Series([row[column_name]], dtype="boolean")
            else:
                frame[column_name] = pd.Series([row[column_name]], dtype="bool")
        elif column.nullable and "float" in dtype_name:
            frame[column_name] = pd.Series([float("nan")], dtype="float64")
        elif column.nullable and "int" in dtype_name:
            frame[column_name] = pd.Series([pd.NA], dtype="Int64")
    return frame


_VALID_INCHI_KEY = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
_VALID_INCHI = "InChI=1S/C2H4O2/c1-2(3)4/h1H3,(H,3,4)"


def pubchem_identity_valid_dataframe() -> pd.DataFrame:
    """One-row dataframe exercising PubChem identity shard checks."""
    status = next(iter(CHEMICAL_STANDARDIZATION_STATUSES))
    return dataframe_from_row(
        pubchem_identity_row(
            canonical_smiles="CC(=O)O",
            isomeric_smiles="CC(=O)O",
            inchi=_VALID_INCHI,
            inchi_key=_VALID_INCHI_KEY,
            standardized_canonical_smiles="CC(=O)O",
            standardized_isomeric_smiles="CC(=O)O",
            standardized_inchi=_VALID_INCHI,
            standardized_inchi_key=_VALID_INCHI_KEY,
            structure_parent_key="parent-key",
            chemical_standardization_status=status,
            chemical_standardization_warnings="[]",
            chemical_standardization_policy_version=(
                CHEMICAL_STANDARDIZATION_POLICY_VERSION
            ),
            molecular_formula="C2H4O2",
            iupac_name="acetic acid",
        )
    )


def pubchem_shard_checks_dataframe(
    schema_cls: type[ppa.DataFrameModel],
) -> pd.DataFrame:
    """Build a one-row dataframe with non-null values for every shard column."""
    row: dict[str, Any] = {}
    for column_name, column in schema_cls.to_schema().columns.items():
        dtype_name = str(column.dtype).lower()
        if "float" in dtype_name:
            row[column_name] = 1.0
        elif "int" in dtype_name:
            row[column_name] = 1
        else:
            row[column_name] = None
    frame = pd.DataFrame([row])
    for column_name, column in schema_cls.to_schema().columns.items():
        dtype_name = str(column.dtype).lower()
        if "float" in dtype_name:
            frame[column_name] = pd.Series([row[column_name]], dtype="float64")
        elif "int" in dtype_name:
            frame[column_name] = pd.Series([row[column_name]], dtype="Int64")
    return frame


def id_mapping_row(**overrides: Any) -> dict[str, Any]:
    """Minimal valid UniProt ID mapping row."""
    row = {
        **ETL_SYSTEM_ROW,
        "entity_id": "idmapping:CHEMBL204",
        "target_id": "CHEMBL204",
        "uniprot_accession": "P00742",
        "mapping_status": "found",
    }
    row.update(overrides)
    return row
