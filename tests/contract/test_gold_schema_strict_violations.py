"""Strict Gold schema violation matrix driven by the snapshot registry."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.contracts.gold import ChEMBLAssayGoldSchema
from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema
from tests.contract.schemas._schema_row_helpers import minimal_schema_dataframe

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def _minimal_strict_gold_row(schema_cls: type[Any]) -> dict[str, Any]:
    """Build one nullable-aware row covering every strict Gold schema column."""
    row: dict[str, Any] = {}
    for column_name, column in schema_cls.to_schema().columns.items():
        if not column.nullable:
            if column.dtype == "bool":
                row[column_name] = False
            elif column.dtype == "int64":
                row[column_name] = 0
            elif column.dtype == "float64":
                row[column_name] = 0.0
            else:
                row[column_name] = f"value-{column_name}"
        else:
            row[column_name] = None
    return row


def _strict_gold_dataframe(schema_cls: type[Any], row: dict[str, Any]) -> pd.DataFrame:
    """Materialize a strict-schema dataframe with stable dtypes for validation."""
    frame = pd.DataFrame([row])
    for column_name, column in schema_cls.to_schema().columns.items():
        if column_name not in frame.columns:
            continue
        if column.dtype == "int64":
            frame[column_name] = frame[column_name].astype("int64")
        elif column.dtype == "bool":
            frame[column_name] = frame[column_name].astype("bool")
    return frame


def _minimal_pubchem_gold_df() -> pd.DataFrame:
    frame = minimal_schema_dataframe(PubChemCompoundGoldSchema)
    frame.loc[0, "entity_id"] = "pubchem_compound:2244"
    frame.loc[0, "molecule_id"] = "CID2244"
    frame.loc[0, "content_hash"] = "a" * 64
    frame.loc[0, "canonical_smiles"] = "CC(=O)OC1=CC=CC=C1C(=O)O"
    frame.loc[0, "chemical_standardization_status"] = "standardized"
    return frame


def _minimal_chembl_assay_gold_df() -> pd.DataFrame:
    frame = minimal_schema_dataframe(ChEMBLAssayGoldSchema)
    frame.loc[0, "entity_id"] = "chembl_assay:CHEMBL1234"
    frame.loc[0, "assay_id"] = "CHEMBL1234"
    frame.loc[0, "content_hash"] = "a" * 64
    frame.loc[0, "confidence_score"] = 9.0
    return frame


@pytest.mark.parametrize(
    ("entity", "schema_cls"),
    [
        ("pubchem_compound", PubChemCompoundGoldSchema),
    ],
)
def test_strict_gold_schema_rejects_unknown_columns(
    entity: str,  # noqa: ARG001 - keeps parametrized ids aligned with registry entity.
    schema_cls: type[Any],
) -> None:
    df = _minimal_pubchem_gold_df()
    polluted = df.copy()
    polluted["__unexpected_column__"] = "blocked"
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        schema_cls.validate(polluted)


def test_pubchem_gold_strict_minimal_row_validates() -> None:
    validated = PubChemCompoundGoldSchema.validate(_minimal_pubchem_gold_df())
    assert validated["molecule_id"].iloc[0] == "CID2244"


def test_pubchem_gold_strict_rejects_null_required_molecule_id() -> None:
    df = _minimal_pubchem_gold_df()
    df.loc[0, "molecule_id"] = None
    with pytest.raises(pa.errors.SchemaError):
        PubChemCompoundGoldSchema.validate(df)


def test_pubchem_gold_strict_rejects_null_required_entity_id() -> None:
    df = _minimal_pubchem_gold_df()
    df.loc[0, "entity_id"] = None
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        PubChemCompoundGoldSchema.validate(df)


def test_chembl_assay_gold_strict_minimal_row_validates() -> None:
    validated = ChEMBLAssayGoldSchema.validate(_minimal_chembl_assay_gold_df())
    assert validated["assay_id"].iloc[0] == "CHEMBL1234"


def test_chembl_assay_gold_rejects_invalid_content_hash() -> None:
    df = _minimal_chembl_assay_gold_df()
    df.loc[0, "content_hash"] = "not-a-sha256"
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        ChEMBLAssayGoldSchema.validate(df)


def test_chembl_assay_gold_rejects_out_of_range_confidence_score() -> None:
    df = _minimal_chembl_assay_gold_df()
    df.loc[0, "confidence_score"] = -1.0
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        ChEMBLAssayGoldSchema.validate(df)
