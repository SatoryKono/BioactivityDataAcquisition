"""Live diagnostics traverse bounded predecessor identities even on corrupt input."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.interfaces.http._selected_run_live import _manifest_ids_for_ledger

pytestmark = pytest.mark.unit


def test_cycle_does_not_repeat_predecessor_reads_forever():
    current = SimpleNamespace(manifest_id="current", predecessor_manifest_id="before")
    before = SimpleNamespace(manifest_id="before", predecessor_manifest_id="current")
    store = {"current": current, "before": before}
    getter = Mock(side_effect=store.get)
    assert _manifest_ids_for_ledger(SimpleNamespace(get=getter), current) == {
        "current",
        "before",
    }
    assert getter.call_count == 2


def test_missing_predecessor_lookup_keeps_only_proven_current_identity():
    current = SimpleNamespace(manifest_id="current", predecessor_manifest_id="before")
    assert _manifest_ids_for_ledger(object(), current) == {"current"}
