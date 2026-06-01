from __future__ import annotations

from pathlib import Path

from scripts.engineering.qa.report_dashboard_query_duplicates import (
    QueryUse,
    _render_markdown,
    build_exact_duplicate_groups,
    build_near_duplicate_groups,
    evaluate_governance,
)
from tests.helpers.cli_process import assert_cli_succeeded, run_python_cli


def test_build_exact_duplicate_groups_collects_cross_panel_reuse() -> None:
    query_uses = (
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Monitor: Score",
            target_ref="target[1]",
            expression='sum(metric_a{pipeline=~"$pipeline"})',
        ),
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Track: Score",
            target_ref="target[1]",
            expression='sum(metric_a{pipeline=~"$pipeline"})',
        ),
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track: Other",
            target_ref="target[1]",
            expression="sum(metric_b)",
        ),
    )

    groups = build_exact_duplicate_groups(query_uses)

    assert len(groups) == 1
    assert groups[0].scope == "single_dashboard_multi_panel"
    assert groups[0].dashboards == ("bioetl-dq-v2.json",)
    assert groups[0].panel_refs == (
        "bioetl-dq-v2.json :: Monitor: Score",
        "bioetl-dq-v2.json :: Track: Score",
    )


def test_build_near_duplicate_groups_excludes_single_panel_triplets_by_default() -> (
    None
):
    query_uses = (
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track Latency p50/p95/p99",
            target_ref="target[1]",
            expression="histogram_quantile(0.50, sum by (le) (rate(bioetl_latency_bucket[$__rate_interval])))",
        ),
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track Latency p50/p95/p99",
            target_ref="target[2]",
            expression="histogram_quantile(0.95, sum by (le) (rate(bioetl_latency_bucket[$__rate_interval])))",
        ),
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track Latency p50/p95/p99",
            target_ref="target[3]",
            expression="histogram_quantile(0.99, sum by (le) (rate(bioetl_latency_bucket[$__rate_interval])))",
        ),
    )

    default_groups = build_near_duplicate_groups(query_uses)
    all_groups = build_near_duplicate_groups(query_uses, include_single_panel=True)

    assert default_groups == ()
    assert len(all_groups) == 1
    assert all_groups[0].scope == "single_panel_multi_target"


def test_build_near_duplicate_groups_surfaces_cross_panel_stage_variants() -> None:
    query_uses = (
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Track Bronze",
            target_ref="target[1]",
            expression=(
                "round(sum(increase(bioetl_records_processed_total"
                '{pipeline=~"$pipeline",stage="bronze"}[$__range])) or vector(0))'
            ),
        ),
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Track Gold",
            target_ref="target[1]",
            expression=(
                "round(sum(increase(bioetl_records_processed_total"
                '{pipeline=~"$pipeline",stage="gold"}[$__range])) or vector(0))'
            ),
        ),
    )

    groups = build_near_duplicate_groups(query_uses)

    assert len(groups) == 1
    assert groups[0].scope == "single_dashboard_multi_panel"
    assert groups[0].metrics == ("bioetl_records_processed_total",)
    assert len(groups[0].distinct_expressions) == 2


def test_render_markdown_includes_exact_and_near_sections() -> None:
    query_uses = (
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Monitor: Score",
            target_ref="target[1]",
            expression="sum(metric_a)",
        ),
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Track: Score",
            target_ref="target[1]",
            expression="sum(metric_a)",
        ),
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track Bronze",
            target_ref="target[1]",
            expression='sum(metric_b{stage="bronze"})',
        ),
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track Gold",
            target_ref="target[1]",
            expression='sum(metric_b{stage="gold"})',
        ),
    )

    markdown = _render_markdown(
        exact_duplicates=build_exact_duplicate_groups(query_uses),
        near_duplicates=build_near_duplicate_groups(query_uses),
        include_single_panel=False,
    )

    assert "# Dashboard Query Duplicate Report" in markdown
    assert "## Exact Duplicate Groups" in markdown
    assert "## Near-Duplicate Families" in markdown
    assert "single_dashboard_multi_panel" in markdown


def test_evaluate_governance_allows_reviewed_exact_duplicate(tmp_path: Path) -> None:
    query_uses = (
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Monitor: Score",
            target_ref="target[1]",
            expression="sum(metric_a)",
        ),
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Track: Score",
            target_ref="target[1]",
            expression="sum(metric_a)",
        ),
    )
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        """
version: 1
exact_duplicates:
  allowed_groups:
    - id: reviewed
      panel_refs:
        - "bioetl-dq-v2.json :: Monitor: Score"
        - "bioetl-dq-v2.json :: Track: Score"
near_duplicates:
  max_count: 0
""",
        encoding="utf-8",
    )

    violations = evaluate_governance(
        exact_duplicates=build_exact_duplicate_groups(query_uses),
        near_duplicates=(),
        allowlist_path=allowlist,
    )

    assert violations == ()


def test_evaluate_governance_flags_unreviewed_exact_duplicate(tmp_path: Path) -> None:
    query_uses = (
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Monitor: Score",
            target_ref="target[1]",
            expression="sum(metric_a)",
        ),
        QueryUse(
            dashboard="bioetl-dq-v2.json",
            panel_title="Track: Score",
            target_ref="target[1]",
            expression="sum(metric_a)",
        ),
    )
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "version: 1\nnear_duplicates:\n  max_count: 0\n",
        encoding="utf-8",
    )

    violations = evaluate_governance(
        exact_duplicates=build_exact_duplicate_groups(query_uses),
        near_duplicates=(),
        allowlist_path=allowlist,
    )

    assert len(violations) == 1
    assert violations[0].kind == "unreviewed_exact_duplicate"


def test_evaluate_governance_flags_near_duplicate_budget(tmp_path: Path) -> None:
    query_uses = (
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track Bronze",
            target_ref="target[1]",
            expression='sum(metric_b{stage="bronze"})',
        ),
        QueryUse(
            dashboard="bioetl-runtime.json",
            panel_title="Track Gold",
            target_ref="target[1]",
            expression='sum(metric_b{stage="gold"})',
        ),
    )
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "version: 1\nnear_duplicates:\n  max_count: 0\n",
        encoding="utf-8",
    )

    violations = evaluate_governance(
        exact_duplicates=(),
        near_duplicates=build_near_duplicate_groups(query_uses),
        allowlist_path=allowlist,
    )

    assert len(violations) == 1
    assert violations[0].kind == "near_duplicate_budget_exceeded"


def test_qa_cli_report_dashboard_query_duplicates_help_smoke() -> None:
    result = run_python_cli(
        "-m",
        "scripts.engineering.qa",
        "report-dashboard-query-duplicates",
        "--help",
    )

    assert_cli_succeeded(result)
    assert "exact and near-duplicate dashboard PromQL" in result.stdout


def test_qa_cli_report_dashboard_query_duplicates_check_passes_current_allowlist() -> (
    None
):
    result = run_python_cli(
        "-m",
        "scripts.engineering.qa",
        "report-dashboard-query-duplicates",
        "--check",
        "--include-single-panel-near",
    )

    assert_cli_succeeded(result)
