"""Smoke tests for normalization governance CLI entrypoints."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs import __main__ as docs_router
from scripts.engineering.qa import __main__ as qa_router
from tests.helpers import assert_cli_succeeded, run_main_in_process


pytestmark = pytest.mark.unit


def test_docs_cli_generate_pipeline_normalization_matrix_help_smoke() -> None:
    spec = docs_router.COMMAND_SPECS["generate-pipeline-normalization-matrix"]
    assert spec.runner == "module"
    assert spec.target == "scripts.docs.matrix.generate_pipeline_normalization_matrix"

    result = run_main_in_process(
        docs_router.main,
        "generate-pipeline-normalization-matrix",
        "--help",
    )

    assert_cli_succeeded(result)
    assert (
        "Generate deterministic normalization field-matrix artifacts" in result.stdout
    )


def test_qa_cli_report_normalization_fallback_inventory_help_smoke() -> None:
    spec = qa_router.COMMAND_SPECS["report-normalization-fallback-inventory"]
    assert spec.runner == "module"
    assert (
        spec.target == "scripts.engineering.qa.report_normalization_fallback_inventory"
    )

    result = run_main_in_process(
        qa_router.main,
        "report-normalization-fallback-inventory",
        "--help",
    )

    assert_cli_succeeded(result)
    assert (
        "Generate a report-only inventory of fields still using fallback normalization."
        in result.stdout
    )


def test_qa_cli_check_xwalk_missing_backlog_help_smoke() -> None:
    spec = qa_router.COMMAND_SPECS["check-xwalk-missing-backlog"]
    assert spec.runner == "module"
    assert spec.target == "scripts.engineering.qa.check_xwalk_missing_backlog"

    result = run_main_in_process(
        qa_router.main,
        "check-xwalk-missing-backlog",
        "--help",
    )

    assert_cli_succeeded(result)
    assert (
        "Validate that xwalk MISSING_* markers are tracked in the backlog."
        in result.stdout
    )


@pytest.mark.timeout(300)
def test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "matrix"

    generate = run_main_in_process(
        docs_router.main,
        "generate-pipeline-normalization-matrix",
        "--out-dir",
        str(out_dir),
    )

    assert_cli_succeeded(generate)
    assert (out_dir / "pipeline_normalization_field_matrix.csv").exists()
    assert (out_dir / "pipeline_normalization_field_matrix.md").exists()
    assert (out_dir / "non_chembl_normalization_field_matrix.md").exists()

    check = run_main_in_process(
        docs_router.main,
        "generate-pipeline-normalization-matrix",
        "--out-dir",
        str(out_dir),
        "--check",
    )

    assert_cli_succeeded(check)


def test_qa_cli_report_normalization_fallback_inventory_execution_smoke(
    tmp_path: Path,
) -> None:
    json_out = tmp_path / "fallback.json"
    markdown_out = tmp_path / "fallback.md"

    result = run_main_in_process(
        qa_router.main,
        "report-normalization-fallback-inventory",
        "--limit",
        "5",
        "--json-out",
        str(json_out),
        "--markdown-out",
        str(markdown_out),
    )

    assert_cli_succeeded(result)
    assert json_out.exists()
    assert markdown_out.exists()
