"""Unit tests for run-manifest lazy service accessors."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from bioetl.composition import control_plane_api
from bioetl.interfaces.cli.commands import _run_manifest_services as services

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("getter", "composition_getter"),
    [
        (
            services.get_run_manifest_service,
            "get_run_manifest_service",
        ),
        (
            services.get_forensic_run_diff_service,
            "get_forensic_run_diff_service",
        ),
        (
            services.get_historical_replay_corpus_service,
            "get_historical_replay_corpus_service",
        ),
        (
            services.get_historical_replay_closure_service,
            "get_historical_replay_closure_service",
        ),
        (
            services.get_historical_replay_universe_service,
            "get_historical_replay_universe_service",
        ),
    ],
)
def test_lazy_service_getters_delegate_to_composition_api(
    monkeypatch: pytest.MonkeyPatch,
    getter: Callable[[], object],
    composition_getter: str,
) -> None:
    sentinel = object()

    monkeypatch.setattr(control_plane_api, composition_getter, lambda: sentinel)

    assert getter() is sentinel
