from __future__ import annotations

import pytest

from scripts.engineering.qa import __main__ as qa_router
from tests.helpers import assert_cli_succeeded, run_main_in_process, run_python_cli


pytestmark = pytest.mark.unit


def test_qa_cli_report_dashboard_promql_scope_help_smoke() -> None:
    spec = qa_router.COMMAND_SPECS["report-dashboard-promql-scope"]
    assert spec.runner == "module"
    assert spec.target == "scripts.engineering.qa.report_dashboard_promql_scope"

    result = run_main_in_process(
        qa_router.main,
        "report-dashboard-promql-scope",
        "--help",
    )

    assert_cli_succeeded(result)
    assert "PromQL scope coverage" in result.stdout


def test_qa_cli_report_dashboard_promql_scope_check_passes_current_dashboards() -> (
    None
):
    result = run_python_cli(
        "-m",
        "scripts.engineering.qa",
        "report-dashboard-promql-scope",
        "--check",
        timeout=180,
    )

    assert_cli_succeeded(result)
