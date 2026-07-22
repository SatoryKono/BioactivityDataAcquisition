"""Unit tests for Semantic Scholar contract replay fixture helpers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_load_semanticscholar_replay_payload__delegates_to_replay_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.contract import _semanticscholar_contract_support

    called: dict[str, bool] = {}

    def _fake_load(probe: str) -> str:
        called[probe] = True
        return "ok"

    monkeypatch.setattr(
        _semanticscholar_contract_support,
        "_load_semanticscholar_replay_payload",
        _fake_load,
    )

    assert (
        _semanticscholar_contract_support.load_semanticscholar_replay_payload(
            probe="paper_search_endpoint"
        )
        == "ok"
    )
    assert called == {"paper_search_endpoint": True}


@pytest.mark.parametrize(
    "probe",
    ["paper_batch_lookup_by_doi", "paper_search_endpoint"],
)
def test_load_semanticscholar_replay_payload__returns_registered_probe_payload(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    from tests.contract import _semanticscholar_contract_support

    expected = {"probe": probe}

    monkeypatch.setattr(
        _semanticscholar_contract_support,
        "_load_semanticscholar_replay_payload",
        lambda _probe: expected,
    )

    assert (
        _semanticscholar_contract_support.load_semanticscholar_replay_payload(
            probe=probe
        )
        == expected
    )


def test_load_semanticscholar_replay_payload__forwards_errors_for_unknown_probe() -> None:
    import tests.contract._semanticscholar_contract_support as helper

    with pytest.raises(Exception):
        helper.load_semanticscholar_replay_payload(probe="unknown_probe")
