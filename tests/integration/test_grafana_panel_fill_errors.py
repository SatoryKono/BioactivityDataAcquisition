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
from pathlib import Path

import pytest

from scripts.ops.observability.grafana.check_dashboard_panel_fill import (
    FillConfig,
    grafana_can_query,
    run_panel_fill_check,
)

pytestmark = pytest.mark.integration


def _dotenv_value(name: str) -> str:
    path = Path(".env")
    if not path.is_file():
        return ""
    prefix = f"{name}="
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip().strip('"').strip("'")
    return ""


def _setting(name: str, default: str = "") -> str:
    return os.getenv(name, "").strip() or _dotenv_value(name) or default


def _fill_config() -> FillConfig:
    base = (
        _setting("GRAFANA_BASE_URL")
        or _setting("GRAFANA_URL")
        or "http://127.0.0.1:3000"
    )
    return FillConfig(
        grafana_base_url=base.rstrip("/"),
        grafana_username=_setting("GRAFANA_USERNAME", "admin") or "admin",
        grafana_password=_setting("GRAFANA_PASSWORD"),
        pipeline=_setting("BIOETL_PANEL_FILL_PIPELINE", "chembl_target"),
        run_type=_setting("BIOETL_PANEL_FILL_RUN_TYPE", "incremental"),
        run_id=_setting("BIOETL_PANEL_FILL_RUN_ID", "-"),
        workflow=_setting("BIOETL_PANEL_FILL_WORKFLOW", "All"),
        range_hours=24,
        request_timeout_seconds=8.0,
        output_path=None,
    )


def test_every_dashboard_panel_fill_has_no_gateway_or_query_error() -> None:
    """Each queryable panel must fill without 502/503/504/505 or query error.

    Valid empty / No data / UNKNOWN is allowed. Grafana must already be running;
    this test does not start docker-compose.monitoring.yml.
    """
    config = _fill_config()
    skip_reason = grafana_can_query(config)
    if skip_reason is not None:
        pytest.skip(skip_reason)

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
