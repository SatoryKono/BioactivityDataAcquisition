"""Additional contract-registry loader edge cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config import contract_registry_loader as loader


pytestmark = pytest.mark.unit


def test_try_load_contract_registry_payload_returns_none_for_non_mapping_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        loader,
        "load_contract_registry_payload",
        lambda _path=None: (_ for _ in ()).throw(ValueError("bad root")),
    )

    assert (
        loader.try_load_contract_registry_payload(
            Path("configs/base/contract_registry.yaml")
        )
        is None
    )


def test_try_load_contract_registry_entries_returns_empty_dict_for_malformed_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        loader,
        "load_contract_registry_entries",
        lambda _path=None: (_ for _ in ()).throw(ValueError("bad entry")),
    )

    assert (
        loader.try_load_contract_registry_entries(
            Path("configs/base/contract_registry.yaml")
        )
        == {}
    )
