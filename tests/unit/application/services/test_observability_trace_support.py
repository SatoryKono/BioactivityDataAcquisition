# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for neutral observability trace-identifier helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.workflow._observability_trace_support import (
    _explicit_trace_ids,
    _generated_trace_ids,
    build_trace_ids,
    resolve_primary_composite_run_id,
    trace_identifiers_available,
)


pytestmark = pytest.mark.unit


def test_trace_identifiers_available_rejects_noop_and_missing_tracer() -> None:
    assert trace_identifiers_available(None) is False
    assert trace_identifiers_available(SimpleNamespace(is_noop=True)) is False
    assert trace_identifiers_available(SimpleNamespace(is_noop=False)) is True
    assert trace_identifiers_available(object()) is True


def test_build_trace_ids_prefers_normalized_explicit_ids_and_composite_anchor() -> None:
    diagnostics = {
        "trace_ids": [" trace-a ", "", object(), "trace-a", "trace-b"],
        "composite_dossier_projection": {"primary_composite_run_id": " composite-run "},
    }

    trace_ids = build_trace_ids(
        run_id="run-ignored",
        diagnostics=diagnostics,
        trace_identifiers_available=True,
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
        trace_identifiers_available=True,
    ) == ["run-a", "composite-only"]
    assert (
        build_trace_ids(
            run_id="run-a",
            diagnostics={},
            trace_identifiers_available=False,
        )
        == []
    )


def test_trace_id_helpers_handle_empty_inputs_and_dedupe_generated_ids() -> None:
    assert (
        _explicit_trace_ids(diagnostics={"trace_ids": object()}, composite_run_id=None)
        == []
    )
    assert _explicit_trace_ids(
        diagnostics={"trace_ids": [" run-a ", "run-a"]},
        composite_run_id=None,
    ) == ["run-a"]
    assert _generated_trace_ids(
        run_id="",
        composite_run_id="composite-only",
        trace_identifiers_available=True,
    ) == ["composite-only"]
    assert _generated_trace_ids(
        run_id="same",
        composite_run_id="same",
        trace_identifiers_available=True,
    ) == ["same"]


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
