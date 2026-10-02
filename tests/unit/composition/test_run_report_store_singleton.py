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
"""Report-store sharing belongs to explicit host lifetimes, not a singleton."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.interfaces.http import _health_server_readiness as readiness
from bioetl.interfaces.http import health_server as server_module
from bioetl.interfaces.http.health_server import (
    HealthServer,
    HealthServerControlPlaneDeps,
)

pytestmark = pytest.mark.unit

import pytest

pytestmark = pytest.mark.unit



def test_standalone_hosts_own_independent_store_lifetimes(monkeypatch) -> None:
    stores = [create_run_report_store(), create_run_report_store()]
    factory = MagicMock(side_effect=stores)
    monkeypatch.setattr(server_module, "create_run_report_store", factory)
    reconcile = MagicMock(return_value={"status": "healthy"})
    monkeypatch.setattr(readiness, "current_metrics_reconciliation_check", reconcile)
    first, second = HealthServer(), HealthServer()
    readiness._current_metrics_check(first)
    readiness._current_metrics_check(first)
    readiness._current_metrics_check(second)
    assert factory.call_count == 2
    assert [call.kwargs["store"] for call in reconcile.call_args_list] == [
        stores[0],
        stores[0],
        stores[1],
    ]
    assert stores[0] is not stores[1]


def test_shared_run_report_store_exposes_port_surface() -> None:
    store = create_run_report_store()

    for method in (
        "mkdir",
        "write_text",
        "read_text",
        "read_identity_text",
        "is_file",
        "is_dir",
        "iterdir",
        "mtime",
        "remove_tree",
    ):
        assert callable(getattr(store, method)), f"missing port method: {method}"


def test_injected_host_store_bypasses_fallback_factory(monkeypatch) -> None:
    store = MagicMock()
    factory = MagicMock(side_effect=AssertionError("unexpected fallback assembly"))
    monkeypatch.setattr(server_module, "create_run_report_store", factory)
    server = HealthServer(
        control_plane=HealthServerControlPlaneDeps(run_report_store=store)
    )
    assert server._run_report_store is store
    factory.assert_not_called()
