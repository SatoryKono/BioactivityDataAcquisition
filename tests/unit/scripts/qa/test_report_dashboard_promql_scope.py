from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa import __main__ as qa_router
from tests.helpers import assert_cli_succeeded, run_main_in_process


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


def test_qa_cli_report_dashboard_promql_scope_check_passes_current_dashboards(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "dashboard-promql-scope-matrix.csv"
    result = run_main_in_process(
        qa_router.main,
        "report-dashboard-promql-scope",
        "--check",
        "--output",
        str(output_path),
    )

    assert_cli_succeeded(result)
    assert output_path.is_file()
