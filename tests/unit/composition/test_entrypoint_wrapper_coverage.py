"""Delegation coverage for retained composition entrypoint wrappers."""

import pytest

from bioetl.composition import composite_api, entrypoints, observability_api

pytestmark = pytest.mark.unit


def test_start_metrics_server_forwards_all_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = object()
    observed: dict[str, object] = {}

    def implementation(**kwargs: object) -> bool:
        observed.update(kwargs)
        return True

    monkeypatch.setattr(observability_api, "start_metrics_server", implementation)

    assert entrypoints.start_metrics_server(
        9100,
        "127.0.0.1",
        fail_fast=True,
        retry_count=5,
        retry_delay=0.25,
        logger=logger,
    )
    assert observed == {
        "port": 9100,
        "addr": "127.0.0.1",
        "fail_fast": True,
        "retry_count": 5,
        "retry_delay": 0.25,
        "logger": logger,
    }


def test_load_pipeline_config_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(composite_api, "load_pipeline_config", lambda name: sentinel)

    assert entrypoints.load_pipeline_config("chembl_activity") is sentinel
