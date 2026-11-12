"""Incomplete scope and unavailable evidence never become valid zero counts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, sentinel
import pytest
from bioetl.interfaces.http import _control_plane_selector_payloads as selector
from bioetl.interfaces.http import _processed_records_report as accounting
from bioetl.interfaces.http import _selected_run_unavailable as unavailable
from bioetl.interfaces.http import control_plane_selector_context as context

pytestmark = pytest.mark.unit


def test_pipeline_without_provider_entity_separator_has_unknown_scope():
    assert selector._provider_entity_from_pipeline("unstructured") == (
        selector.UNKNOWN_SCOPE,
        selector.UNKNOWN_SCOPE,
    )


@pytest.mark.parametrize(
    "entries", [(), (SimpleNamespace(run_id="first"), SimpleNamespace(run_id="second"))]
)
def test_absent_or_mixed_run_ledger_does_not_overwrite_metric_counts(entries):
    values = {"fixture_count": 17}
    accounting.fill_report_accounting(
        values,
        report={},
        ledger_entries=entries,
        pipeline="chembl_activity",
        run_type=None,
    )
    assert values == {"fixture_count": 17}


def test_read_context_without_replay_verifier_returns_unknown():
    port = unavailable._ContextManifestPort(lambda run_id: sentinel.manifest, None)
    assert port.verify_replay_objects(sentinel.manifest) is None
    assert port.get_by_run_id("run") is sentinel.manifest


@pytest.mark.parametrize("error", [OSError, TypeError, ValueError])
def test_resolver_failure_is_an_error_payload_without_fallback_context(error):
    resolver = SimpleNamespace(
        resolve=Mock(side_effect=error("synthetic identity refusal"))
    )
    payload, read_context = unavailable.resolve_selected_run(
        resolver, pipeline="chembl_activity", run_id="run"
    )
    assert read_context is None
    assert payload["verdict"] == "ERROR"
    assert payload["execution_state"] == "UNKNOWN"


def test_invalid_option_items_are_not_replaced_by_an_empty_catalog_label():
    payload = {"items": "malformed"}
    assert context.finalize_run_id_empty_catalog_label(payload) is payload
