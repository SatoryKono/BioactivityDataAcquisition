"""Smoke tests for normalization governance CLI entrypoints."""

from __future__ import annotations

from pathlib import Path

from tests.helpers import assert_cli_succeeded, run_python_cli


def test_docs_cli_generate_pipeline_normalization_matrix_help_smoke() -> None:
    result = run_python_cli(
        "-m",
        "scripts.docs",
        "generate-pipeline-normalization-matrix",
        "--help",
    )

    assert_cli_succeeded(result)
    assert (
        "Generate deterministic normalization field-matrix artifacts" in result.stdout
    )


def test_qa_cli_report_normalization_fallback_inventory_help_smoke() -> None:
    result = run_python_cli(
        "-m",
        "scripts.engineering.qa",
        "report-normalization-fallback-inventory",
        "--help",
    )

    assert_cli_succeeded(result)
    assert (
        "Generate a report-only inventory of fields still using fallback normalization."
        in result.stdout
    )


def test_qa_cli_check_xwalk_missing_backlog_help_smoke() -> None:
    result = run_python_cli(
        "-m",
        "scripts.engineering.qa",
        "check-xwalk-missing-backlog",
        "--help",
    )

    assert_cli_succeeded(result)
    assert (
        "Validate that xwalk MISSING_* markers are tracked in the backlog."
        in result.stdout
    )


def test_docs_cli_generate_pipeline_normalization_matrix_execution_smoke(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "matrix"

    generate = run_python_cli(
        "-m",
        "scripts.docs",
        "generate-pipeline-normalization-matrix",
        "--out-dir",
        str(out_dir),
    )

    assert_cli_succeeded(generate)
    assert (out_dir / "pipeline_normalization_field_matrix.csv").exists()
    assert (out_dir / "pipeline_normalization_field_matrix.md").exists()
    assert (out_dir / "non_chembl_normalization_field_matrix.md").exists()

    check = run_python_cli(
        "-m",
        "scripts.docs",
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

    result = run_python_cli(
        "-m",
        "scripts.engineering.qa",
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
