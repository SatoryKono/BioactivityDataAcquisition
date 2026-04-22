"""Tests for provider-wide enum registry helpers."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.domain.config.enum_loader import (
    get_chembl_enum,
    get_chembl_enum_set,
    get_enum_set,
    get_provider_enum,
    get_provider_enum_config,
    load_provider_enums,
)


class FakeEnumLoader:
    """In-memory enum loader used to keep domain tests I/O-free."""

    def __init__(self) -> None:
        self.enums: dict[str, dict[str, Any]] = {
            "chembl": {
                "activity": {
                    "standard_relations": ["=", "<", ">"],
                },
            },
            "uniprot": {
                "protein": {
                    "entry_types": [
                        "UniProtKB reviewed (Swiss-Prot)",
                        "UniProtKB unreviewed (TrEMBL)",
                    ],
                },
            },
        }

    def load_provider_enums(self, provider: str) -> dict[str, object]:
        return self.enums[provider]

    def load_chembl_enums(self) -> dict[str, object]:
        return self.load_provider_enums("chembl")


def test_generic_provider_enum_api_loads_injected_values() -> None:
    loader = FakeEnumLoader()

    assert load_provider_enums(" UniProt ", loader)["protein"]
    assert get_provider_enum_config("uniprot", "protein", "entry_types", loader) == [
        "UniProtKB reviewed (Swiss-Prot)",
        "UniProtKB unreviewed (TrEMBL)",
    ]
    assert get_provider_enum("uniprot", "protein", "entry_types", loader) == [
        "UniProtKB reviewed (Swiss-Prot)",
        "UniProtKB unreviewed (TrEMBL)",
    ]
    assert get_enum_set("uniprot", "protein", "entry_types", loader) == frozenset(
        {
            "UniProtKB reviewed (Swiss-Prot)",
            "UniProtKB unreviewed (TrEMBL)",
        }
    )


def test_chembl_compatibility_helpers_delegate_to_generic_registry() -> None:
    loader = FakeEnumLoader()

    assert get_chembl_enum("activity", "standard_relations", loader) == ["=", "<", ">"]
    assert get_chembl_enum_set(
        "activity",
        "standard_relations",
        loader,
    ) == frozenset({"=", "<", ">"})


def test_missing_enum_keys_raise_actionable_errors() -> None:
    loader = FakeEnumLoader()

    with pytest.raises(
        KeyError,
        match="provider='uniprot', entity='protein', field='missing'",
    ):
        get_provider_enum("uniprot", "protein", "missing", loader)


def test_domain_loader_rejects_direct_io_without_injected_loader() -> None:
    with pytest.raises(
        NotImplementedError, match="Domain layer cannot perform direct I/O"
    ):
        load_provider_enums("chembl")
