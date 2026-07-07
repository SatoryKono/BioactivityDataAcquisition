"""Unit tests for observability trace-link helper branches."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from bioetl.application.services._observability_trace_support import (
    build_trace_ids,
    build_trace_time_window,
    build_trace_urls,
    build_traceql_query,
    normalize_datetime,
    resolve_manifest_provider,
    resolve_manifest_run_type,
    resolve_primary_composite_run_id,
    trace_links_enabled,
)


pytestmark = pytest.mark.unit


def test_trace_links_enabled_rejects_noop_and_missing_tracer() -> None:
    assert trace_links_enabled(None) is False
    assert trace_links_enabled(SimpleNamespace(is_noop=True)) is False
    assert trace_links_enabled(SimpleNamespace(is_noop=False)) is True
    assert trace_links_enabled(object()) is True


def test_build_trace_ids_prefers_normalized_explicit_ids_and_composite_anchor() -> None:
    diagnostics = {
        "trace_ids": [" trace-a ", "", object(), "trace-a", "trace-b"],
        "composite_dossier_projection": {"primary_composite_run_id": " composite-run "},
    }

    trace_ids = build_trace_ids(
        run_id="run-ignored",
        diagnostics=diagnostics,
        trace_links_available=True,
    )

    assert trace_ids == ["trace-a", "trace-b", "composite-run"]


def test_build_trace_ids_falls_back_to_available_generated_ids() -> None:
    diagnostics = {
        "trace_ids": "not-a-list",
        "composite_dossier_projection": {"composite_run_ids": ["composite-only"]},
    }

    assert build_trace_ids(
        run_id="run-a",
        diagnostics=diagnostics,
        trace_links_available=True,
    ) == ["run-a", "composite-only"]
    assert (
        build_trace_ids(
            run_id="run-a",
            diagnostics={},
            trace_links_available=False,
        )
        == []
    )


@pytest.mark.parametrize(
    ("diagnostics", "expected"),
    [
        ({}, None),
        ({"composite_dossier_projection": object()}, None),
        ({"composite_dossier_projection": {"primary_composite_run_id": "  "}}, None),
        (
            {"composite_dossier_projection": {"composite_run_ids": [" only-one "]}},
            "only-one",
        ),
        (
            {"composite_dossier_projection": {"composite_run_ids": ["a", "b"]}},
            None,
        ),
    ],
)
def test_resolve_primary_composite_run_id_handles_projection_variants(
    diagnostics: dict[str, object],
    expected: str | None,
) -> None:
    assert resolve_primary_composite_run_id(diagnostics) == expected


def test_manifest_provider_and_run_type_normalize_optional_manifest_values() -> None:
    assert resolve_manifest_provider(None) is None
    assert (
        resolve_manifest_provider(
            SimpleNamespace(manifest=SimpleNamespace(provider=""))
        )
        is None
    )
    assert (
        resolve_manifest_provider(
            SimpleNamespace(manifest=SimpleNamespace(provider=123))
        )
        == "123"
    )

    assert resolve_manifest_run_type(None) is None
    assert (
        resolve_manifest_run_type(
            SimpleNamespace(
                manifest=SimpleNamespace(run_type=SimpleNamespace(value="workflow"))
            )
        )
        == "workflow"
    )
    assert (
        resolve_manifest_run_type(
            SimpleNamespace(manifest=SimpleNamespace(run_type=""))
        )
        is None
    )


def test_build_traceql_query_uses_only_available_filters() -> None:
    assert (
        build_traceql_query(
            run_id="run-a",
            pipeline_name="chembl_activity",
            provider="chembl",
            run_type="workflow",
            composite_run_id="composite-a",
        )
        == '{ span."bioetl.run_id" = "run-a" && '
        'span."bioetl.pipeline" = "chembl_activity" && '
        'span."bioetl.run_type" = "workflow" && '
        'span."bioetl.provider" = "chembl" && '
        'span."bioetl.composite_run_id" = "composite-a" }'
    )
    assert (
        build_traceql_query(
            run_id="",
            pipeline_name="chembl_activity",
            provider=None,
            run_type=None,
            composite_run_id=None,
        )
        is None
    )


def test_build_trace_urls_returns_empty_when_traceql_cannot_be_built() -> None:
    urls = build_trace_urls(
        run_id="",
        pipeline_name="chembl_activity",
        provider="chembl",
        run_type="workflow",
        composite_run_id=None,
        run_manifest=None,
        audit=SimpleNamespace(entries=[]),
    )

    assert urls == []


def test_build_trace_urls_includes_bounded_time_window_and_encoded_query() -> None:
    manifest_time = datetime(2026, 7, 7, 10, 0, tzinfo=UTC)
    audit_time = manifest_time + timedelta(minutes=20)

    urls = build_trace_urls(
        run_id="run-a",
        pipeline_name="chembl_activity",
        provider="chembl",
        run_type="workflow",
        composite_run_id="composite-a",
        run_manifest=SimpleNamespace(
            manifest=SimpleNamespace(created_at=manifest_time)
        ),
        audit=SimpleNamespace(entries=[SimpleNamespace(timestamp=audit_time)]),
    )

    assert len(urls) == 1
    assert urls[0].startswith("/a/grafana-exploretraces-app/?from=")
    assert "datasource=tempo" in urls[0]
    assert "traceqlSearch" in urls[0]
    assert "bioetl.composite_run_id" in urls[0]


def test_build_trace_time_window_uses_defaults_without_timestamps() -> None:
    assert build_trace_time_window(
        run_manifest=SimpleNamespace(manifest=SimpleNamespace(created_at="invalid")),
        audit=SimpleNamespace(entries=[SimpleNamespace(timestamp=None)]),
    ) == ("now-24h", "now")


def test_normalize_datetime_handles_naive_aware_and_invalid_values() -> None:
    naive = datetime(2026, 7, 7, 12, 30)
    aware = datetime(2026, 7, 7, 15, 30, tzinfo=UTC)

    assert normalize_datetime(None) is None
    assert normalize_datetime(naive) == naive.replace(tzinfo=UTC)
    assert normalize_datetime(aware) == aware
