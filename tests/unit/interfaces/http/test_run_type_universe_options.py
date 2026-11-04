"""Unit tests for Prometheus-universe run_type filter-options supplement."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.interfaces.http import _run_type_universe_options as module


def test_supplement_adds_telemetry_only_run_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "collect_prometheus_run_types",
        lambda **_: frozenset({"backfill", "incremental"}),
    )
    payload = module.supplement_prometheus_run_type_options(
        {"items": [{"text": "backfill", "value": "backfill"}]},
        prometheus_base_url="http://localhost:9090",
        deadline=module.time.monotonic() + 20.0,
        response_shape="options",
        pipelines=("chembl_assay",),
    )
    values = {item["value"] for item in payload["items"]}
    assert values == {"backfill", "incremental"}


def test_supplement_fail_open_when_prometheus_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module,
        "collect_prometheus_run_types",
        lambda **_: frozenset(),
    )
    original = {"items": ["backfill"]}
    payload = module.supplement_prometheus_run_type_options(
        original,
        prometheus_base_url="http://localhost:9090",
        deadline=module.time.monotonic() + 20.0,
        response_shape="list",
    )
    assert payload["items"] == ["backfill"]


def test_universe_query_escapes_promql_pipeline_regex() -> None:
    assert module._universe_query(("a-b.c",)) == (
        'count by (run_type) (bioetl_overview_pipeline_run_type_universe{pipeline=~"a\\\\-b\\\\.c"}) or '
        'count by (run_type) (bioetl_control_plane_run_type_universe{pipeline=~"a\\\\-b\\\\.c"})'
    )


def test_collect_prometheus_run_types_parses_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(
        *, prometheus_base_url: str, query: str, timeout_seconds: float
    ) -> dict[str, Any]:
        assert timeout_seconds > 0
        assert "bioetl_overview_pipeline_run_type_universe" in query
        assert 'pipeline=~"chembl_assay"' in query
        return {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"run_type": "incremental"},
                        "value": [1, "1"],
                    },
                    {
                        "metric": {"run_type": "backfill"},
                        "value": [1, "1"],
                    },
                ],
            },
        }

    monkeypatch.setattr(module, "_fetch_prometheus_query_payload", fake_fetch)
    monkeypatch.setattr(
        module,
        "_candidate_prometheus_base_urls",
        lambda url: (url,),
    )
    values = module.collect_prometheus_run_types(
        prometheus_base_url="http://localhost:9090",
        deadline=module.time.monotonic() + 20.0,
        pipelines=("chembl_assay",),
    )
    assert values == frozenset({"incremental", "backfill"})


def test_collect_prometheus_run_types_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(
        *, prometheus_base_url: str, query: str, timeout_seconds: float
    ) -> dict[str, Any]:
        assert timeout_seconds > 0
        raise RuntimeError("down")

    monkeypatch.setattr(module, "_fetch_prometheus_query_payload", boom)
    monkeypatch.setattr(
        module,
        "_candidate_prometheus_base_urls",
        lambda url: (url,),
    )
    assert (
        module.collect_prometheus_run_types(
            prometheus_base_url="http://localhost:9090",
            deadline=module.time.monotonic() + 20.0,
        )
        == frozenset()
    )


def test_collect_prometheus_run_types_stops_fallback_after_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # t=10.0 usable=12.5-10-1.0=1.5; after fail t=12.0 usable=12.5-12-1.0=-0.5 → stop
    moments = iter((10.0, 12.0))
    timeouts: list[float] = []
    monkeypatch.setattr(module.time, "monotonic", lambda: next(moments))
    monkeypatch.setattr(
        module,
        "_candidate_prometheus_base_urls",
        lambda _: ("http://primary", "http://fallback"),
    )

    def fail_primary(
        *, prometheus_base_url: str, query: str, timeout_seconds: float
    ) -> dict[str, Any]:
        timeouts.append(timeout_seconds)
        raise RuntimeError("primary unavailable")

    monkeypatch.setattr(module, "_fetch_prometheus_query_payload", fail_primary)
    values = module.collect_prometheus_run_types(
        prometheus_base_url="http://primary",
        deadline=12.5,
    )

    assert values == frozenset()
    assert timeouts == [1.5]


def test_collect_prometheus_run_types_caps_timeout_below_outer_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prom must not consume the full filter-options remaining deadline."""
    timeouts: list[float] = []
    monkeypatch.setattr(module.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(
        module,
        "_candidate_prometheus_base_urls",
        lambda _: ("http://primary",),
    )

    def capture(
        *, prometheus_base_url: str, query: str, timeout_seconds: float
    ) -> dict[str, Any]:
        timeouts.append(timeout_seconds)
        raise RuntimeError("slow")

    monkeypatch.setattr(module, "_fetch_prometheus_query_payload", capture)
    # Outer filter-options deadline still has 20s left; Prom must stay capped.
    assert (
        module.collect_prometheus_run_types(
            prometheus_base_url="http://primary",
            deadline=120.0,
        )
        == frozenset()
    )
    assert timeouts == [module.PROMETHEUS_QUERY_TIMEOUT_SECONDS]


def test_collect_prometheus_run_types_skips_when_only_return_reserve_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False
    monkeypatch.setattr(module.time, "monotonic", lambda: 19.5)
    monkeypatch.setattr(
        module,
        "_candidate_prometheus_base_urls",
        lambda _: ("http://primary",),
    )

    def boom(
        *, prometheus_base_url: str, query: str, timeout_seconds: float
    ) -> dict[str, Any]:
        nonlocal called
        called = True
        raise RuntimeError("should not run")

    monkeypatch.setattr(module, "_fetch_prometheus_query_payload", boom)
    # Outer deadline at t=20; only the return reserve remains → skip Prom.
    assert (
        module.collect_prometheus_run_types(
            prometheus_base_url="http://primary",
            deadline=20.0,
        )
        == frozenset()
    )
    assert called is False
