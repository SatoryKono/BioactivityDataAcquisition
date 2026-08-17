# pyright: reportArgumentType=false

"""Focused tests for CR-FULL 20260816 freeze-catalog residuals (#8888)."""

from __future__ import annotations

import pytest

from bioetl.domain.immutability import FrozenDict, FrozenList
from bioetl.domain.pubchem_standardization_catalog import (
    PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES,
    PUBCHEM_STANDARDIZATION_ENUM_CATALOG,
)
from bioetl.domain.run_reports.reason_catalog import (
    ReasonCatalog,
    ReasonCatalogEntry,
    default_reason_catalog,
)

pytestmark = pytest.mark.unit


def test_frozen_list_constructor_deep_freezes_nested_values() -> None:
    nested = [{"k": [1]}]
    frozen = FrozenList(nested)
    nested[0]["k"].append(2)
    nested[0]["extra"] = 3
    assert list(frozen[0]["k"]) == [1]
    assert "extra" not in frozen[0]
    with pytest.raises(TypeError):
        frozen[0]["k"] = [9]


def test_frozen_dict_constructor_deep_freezes_nested_values() -> None:
    nested: dict[str, object] = {"child": {"n": 1}, "items": ["a"]}
    frozen = FrozenDict(nested)
    nested["child"]["n"] = 9
    nested["items"].append("b")
    assert frozen["child"]["n"] == 1
    assert list(frozen["items"]) == ["a"]
    with pytest.raises(TypeError):
        frozen["child"]["n"] = 2


def test_pubchem_standardization_catalog_is_immutable() -> None:
    assert (
        PUBCHEM_STANDARDIZATION_ENUM_CATALOG["chemical_standardization_statuses"]
        == PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES
    )
    assert PUBCHEM_STANDARDIZATION_ENUM_CATALOG[
        "chemical_standardization_policy_versions"
    ] == (PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION,)
    with pytest.raises(TypeError):
        PUBCHEM_STANDARDIZATION_ENUM_CATALOG["chemical_standardization_statuses"] = ()


def test_default_reason_catalog_entries_reject_mutation() -> None:
    catalog = default_reason_catalog()
    assert catalog.entries
    with pytest.raises(TypeError):
        catalog.entries["NEW_CODE"] = ReasonCatalogEntry(
            code="NEW_CODE",
            family="system",
            default_outcome="other",
            layer="silver",
        )
    rebuilt = ReasonCatalog(version=catalog.version, entries=dict(catalog.entries))
    assert rebuilt.entries == catalog.entries
    with pytest.raises(TypeError):
        rebuilt.entries["NEW_CODE"] = next(iter(catalog.entries.values()))
