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
"""Unit tests for composite join-key normalization policy helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import polars as pl
import pytest

from bioetl.application.composite.join_key_normalization import (
    iter_configured_join_keys,
    normalize_join_key_dataframe_columns,
    stringify_join_key_value,
    normalize_join_key_text,
    validate_join_key_normalization_policies,
)
from bioetl.composition.bootstrap.runtime.composite import load_composite_config


pytestmark = pytest.mark.repo_backed


@pytest.mark.unit
def test_normalize_join_key_text_applies_trim_and_lowercase_for_doi() -> None:
    assert normalize_join_key_text(" 10.1000/ABC ", key="doi") == "10.1000/abc"


@pytest.mark.unit
def test_normalize_join_key_dataframe_columns_cleans_title_without_lowercase() -> None:
    df = pl.DataFrame({"title": ["  <b>Mixed</b>&nbsp;\tCase\nTitle  "]})

    result = normalize_join_key_dataframe_columns(df=df, join_keys=("title",))

    assert result["title"].to_list() == ["Mixed Case Title"]


@pytest.mark.unit
def test_normalize_join_key_dataframe_columns_covers_supported_mutating_families() -> (
    None
):
    df = pl.DataFrame(
        {
            "doi": [" 10.1000/ABC "],
            "inchi_key": [" bsynrymutxbxsq-uhfffaoysa-n "],
            "pmid": [" PMID:12345 "],
            "pmc_id": [" PMC123 "],
            "target_id": [" chembl0203 "],
            "uniprot_accession": [" p12345 "],
            "title": ["  Mixed\t Case\nTitle  "],
            "canonical_smiles": [" C[C@H](O)C "],
        }
    )

    result = normalize_join_key_dataframe_columns(
        df=df,
        join_keys=(
            "doi",
            "inchi_key",
            "pmid",
            "pmc_id",
            "target_id",
            "uniprot_accession",
            "title",
            "canonical_smiles",
        ),
    )

    assert result.to_dict(as_series=False) == {
        "doi": ["10.1000/abc"],
        "inchi_key": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],
        "pmid": ["12345"],
        "pmc_id": ["pmc123"],
        "target_id": ["CHEMBL203"],
        "uniprot_accession": ["P12345"],
        "title": ["Mixed Case Title"],
        "canonical_smiles": ["C[C@H](O)C"],
    }


@pytest.mark.unit
def test_normalize_join_key_dataframe_columns_preserves_non_mutating_policies() -> None:
    df = pl.DataFrame({"cell_id": [" CHEMBL123 "], "publication_id": [" PUB1 "]})

    result = normalize_join_key_dataframe_columns(
        df=df,
        join_keys=("cell_id", "publication_id"),
    )

    assert result.to_dict(as_series=False) == {
        "cell_id": [" CHEMBL123 "],
        "publication_id": [" PUB1 "],
    }


@pytest.mark.unit
def test_compound_join_key_tuple_normalizes_equivalent_values() -> None:
    tuple_a = (
        stringify_join_key_value(" 10.1000/ABC ", key="doi"),
        stringify_join_key_value("  Mixed\t Case\nTitle  ", key="title"),
    )
    tuple_b = (
        stringify_join_key_value("10.1000/abc", key="doi"),
        stringify_join_key_value("Mixed Case Title", key="title"),
    )

    assert tuple_a == tuple_b == ("10.1000/abc", "Mixed Case Title")


@pytest.mark.unit
def test_validate_join_key_normalization_policies_rejects_unknown_join_key() -> None:
    config = cast(
        Any,
        SimpleNamespace(
            enrichers=(SimpleNamespace(join_keys=("mystery_key",)),),
            dependencies=(),
        ),
    )

    with pytest.raises(ValueError, match="mystery_key"):
        validate_join_key_normalization_policies(config)


@pytest.mark.unit
def test_repo_composite_configs_match_join_key_policy_surface_ratchet() -> None:
    composite_names = tuple(
        path.stem for path in sorted(Path("configs/composites").glob("*.yaml"))
    )
    configured_join_keys = {
        key
        for composite_name in composite_names
        for key in iter_configured_join_keys(load_composite_config(composite_name))
    }

    expected_join_keys = {
        "canonical_smiles",
        "cell_id",
        "doi",
        "inchi_key",
        "molecule_id",
        "pmid",
        "primary_component_id",
        "protein_classification_id",
        "publication_id",
        "target_id",
        "title",
        "tissue_id",
        "uniprot_accession",
    }

    assert configured_join_keys == expected_join_keys


@pytest.mark.unit
def test_repo_composite_configs_all_validate_against_join_key_policies() -> None:
    composite_names = tuple(
        path.stem for path in sorted(Path("configs/composites").glob("*.yaml"))
    )

    for composite_name in composite_names:
        validate_join_key_normalization_policies(load_composite_config(composite_name))
