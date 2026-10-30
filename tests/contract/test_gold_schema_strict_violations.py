# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Strict Gold schema violation matrix driven by the snapshot registry."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pandera as pa
import pytest

import bioetl.domain.contracts.gold as gold_contracts
from bioetl.domain.contracts.gold import ChEMBLAssayGoldSchema
from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema
from tests.contract.schemas._schema_row_helpers import minimal_schema_dataframe

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


GOLD_SCHEMA_CASES = [
    getattr(gold_contracts, export_name)
    for export_name in gold_contracts.__all__
    if export_name.endswith("GoldSchema")
]


def _minimal_valid_gold_df(schema_cls: type[Any]) -> pd.DataFrame:
    """Build a valid row while honoring schema-specific enum and regex checks."""
    frame = minimal_schema_dataframe(schema_cls)
    schema_name = schema_cls.__name__

    if "_lookup_method" in frame.columns:
        frame["_lookup_method"] = "direct"

    if schema_name == "ChEMBLProteinClassGoldSchema":
        frame["protein_class_id"] = 1.0
    elif schema_name == "ChEMBLPublicationSimilarityGoldSchema":
        frame["doc_1"] = 1.0
        frame["doc_2"] = 2.0
    elif schema_name == "ChEMBLSubcellularFractionGoldSchema":
        frame["entity_id"] = "a" * 16
    elif schema_name == "ChEMBLTargetGoldSchema":
        frame["species_group_flag"] = pd.Series([False], dtype="bool")
    elif schema_name == "ChEMBLTargetProteinClassificationGoldSchema":
        frame["classification_status"] = "resolved"
    elif schema_name == "ChEMBLTissueGoldSchema":
        frame["tissue_id"] = "CHEMBL1"
    elif schema_name == "CrossRefPublicationGoldSchema":
        frame["doi"] = "10.1000/test"

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


@pytest.mark.parametrize("schema_cls", GOLD_SCHEMA_CASES, ids=lambda cls: cls.__name__)
def test_strict_gold_schema_minimal_row_validates(schema_cls: type[Any]) -> None:
    validated = schema_cls.validate(_minimal_valid_gold_df(schema_cls))
    assert not validated.empty


@pytest.mark.parametrize("schema_cls", GOLD_SCHEMA_CASES, ids=lambda cls: cls.__name__)
def test_strict_gold_schema_rejects_unknown_columns(
    schema_cls: type[Any],
) -> None:
    df = _minimal_valid_gold_df(schema_cls)
    polluted = df.copy()
    polluted["__unexpected_column__"] = "blocked"
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        schema_cls.validate(polluted)


@pytest.mark.parametrize("schema_cls", GOLD_SCHEMA_CASES, ids=lambda cls: cls.__name__)
def test_strict_gold_schema_rejects_null_required_entity_id(
    schema_cls: type[Any],
) -> None:
    df = _minimal_valid_gold_df(schema_cls)
    df.loc[0, "entity_id"] = None
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        schema_cls.validate(df)


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
