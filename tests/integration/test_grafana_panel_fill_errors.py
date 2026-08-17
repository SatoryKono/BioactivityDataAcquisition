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
"""Live Grafana fill: every data panel must load without gateway/query errors."""

from __future__ import annotations

import os

import pytest

from scripts.ops.observability.grafana.check_dashboard_panel_fill import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    FillConfig,
    grafana_is_reachable,
    run_panel_fill_check,
)

pytestmark = pytest.mark.integration


def _fill_config() -> FillConfig:
    base = (
        os.getenv("GRAFANA_BASE_URL", "").strip()
        or os.getenv("GRAFANA_URL", "").strip()
        or "http://127.0.0.1:3000"
    )
    return FillConfig(
        grafana_base_url=base.rstrip("/"),
        grafana_username=os.getenv("GRAFANA_USERNAME", "admin").strip() or "admin",
        grafana_password=os.getenv("GRAFANA_PASSWORD", "").strip(),
        pipeline=os.getenv("BIOETL_PANEL_FILL_PIPELINE", "chembl_target"),
        run_type=os.getenv("BIOETL_PANEL_FILL_RUN_TYPE", "incremental"),
        run_id=os.getenv("BIOETL_PANEL_FILL_RUN_ID", "-"),
        workflow=os.getenv("BIOETL_PANEL_FILL_WORKFLOW", "All"),
        range_hours=24,
        request_timeout_seconds=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        output_path=None,
    )


def test_every_dashboard_panel_fill_has_no_gateway_or_query_error() -> None:
    """Each queryable panel must fill without 502/503/504/505 or query error.

    Valid empty / No data / UNKNOWN is allowed. Grafana must already be running;
    this test does not start docker-compose.monitoring.yml.
    """
    config = _fill_config()
    if not grafana_is_reachable(config):
        pytest.skip(f"Grafana is not reachable at {config.grafana_base_url}/api/health")

    results = run_panel_fill_check(config)
    assert results, "expected at least one queryable shipped panel"
    errors = [result for result in results if result.verdict.kind == "fill_error"]
    formatted = "\n".join(
        f"{result.dashboard_uid}#{result.panel_id} {result.title}: "
        f"{result.verdict.reason}"
        for result in errors
    )
    assert not errors, (
        "panel fill returned gateway/query errors "
        f"({len(errors)} of {len(results)}):\n{formatted}"
    )
