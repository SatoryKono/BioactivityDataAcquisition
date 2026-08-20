# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Fail-closed pytest wrappers for dashboard QA --check commands (#9205).

These gates prove DASH-QUERY-001, DASH-PERF-001, DASH-META-001, and
DASH-DATA-002 against shipped grafana/dashboards JSON without starting Grafana.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.check_dashboard_performance_budgets import (
    main as performance_budgets_main,
)
from scripts.engineering.qa.report_dashboard_inventory import (
    main as inventory_main,
)
from scripts.engineering.qa.report_dashboard_promql_scope import (
    main as promql_scope_main,
)
from scripts.engineering.qa.report_dashboard_query_duplicates import (
    main as query_duplicates_main,
)
from tests.helpers import assert_cli_succeeded, run_main_in_process

pytestmark = pytest.mark.integration

_TEST_PATH = "tests/integration/test_dashboard_qa_check_gates.py"


def test_query_duplicates_check_passes_shipped_dashboards() -> None:
    """DASH-QUERY-001: unjustified exact PromQL duplicates fail closed."""
    result = run_main_in_process(query_duplicates_main, "--check", "--json")
    assert_cli_succeeded(result)


def test_performance_budgets_pass_shipped_dashboards() -> None:
    """DASH-PERF-001: first-load / expr / HTTP / refresh / panel / nav budgets."""
    result = run_main_in_process(performance_budgets_main)
    assert_cli_succeeded(result)
    assert "OK: all performance budgets within limits" in result.stdout


def test_dashboard_inventory_check_passes_shipped_dashboards() -> None:
    """DASH-META-001: inventory UID/title/tags stay aligned with shipped JSON."""
    result = run_main_in_process(inventory_main, "--check", "--json")
    assert_cli_succeeded(result)


def test_promql_scope_check_rejects_run_id_label_filters(
    tmp_path: Path,
) -> None:
    """DASH-DATA-002: PromQL must not filter on run_id / forbidden tokens."""
    output = tmp_path / "dashboard-promql-scope-matrix.csv"
    result = run_main_in_process(
        promql_scope_main,
        "--check",
        "--output",
        str(output),
    )
    assert_cli_succeeded(result)
    assert output.is_file()


def test_qa_check_gates_are_wired_as_required_dashboard_checks() -> None:
    """Keep the four QA --check wrappers in CI and the pre-push hook."""
    tests_workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    pre_commit = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert _TEST_PATH in tests_workflow
    assert "check-dashboard-qa-check-gates" in pre_commit
    assert _TEST_PATH in pre_commit
