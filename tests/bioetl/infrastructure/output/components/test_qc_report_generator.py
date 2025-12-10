"""Tests for QcReportGenerator component."""

import pandas as pd
import pytest

from bioetl.infrastructure.output.components.qc_report_generator import (
    QcReportGenerator,
)


@pytest.fixture
def generator():
    """Create QcReportGenerator instance."""
    return QcReportGenerator()


def test_build_quality_report_basic(generator):
    """Test basic quality report generation."""
    df = pd.DataFrame({
        "col_a": [1, 2, 3],
        "col_b": [None, 2, 3],
        "col_c": [1, 1, 1],
    })

    report = generator.build_quality_report(df, min_coverage=0.8)

    assert len(report) == 3
    assert "column" in report.columns
    assert "null_count" in report.columns
    assert "non_null_count" in report.columns
    assert "coverage" in report.columns
    assert "coverage_ok" in report.columns


def test_build_quality_report_coverage_calculation(generator):
    """Test coverage calculation."""
    df = pd.DataFrame({
        "full": [1, 2, 3, 4],
        "partial": [1, None, 3, None],
    })

    report = generator.build_quality_report(df, min_coverage=0.8)
    report = report.set_index("column")

    assert report.loc["full", "coverage"] == 1.0
    assert report.loc["partial", "coverage"] == 0.5


def test_build_quality_report_coverage_ok_flag(generator):
    """Test coverage_ok flag based on threshold."""
    df = pd.DataFrame({
        "high": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "low": [1, None, None, None, None, None, None, None, None, None],
    })

    report = generator.build_quality_report(df, min_coverage=0.5)
    report = report.set_index("column")

    assert report.loc["high", "coverage_ok"] == True  # noqa: E712
    assert report.loc["low", "coverage_ok"] == False  # noqa: E712


def test_build_quality_report_sorted_by_column(generator):
    """Test that report is sorted by column name."""
    df = pd.DataFrame({
        "zebra": [1],
        "alpha": [2],
        "middle": [3],
    })

    report = generator.build_quality_report(df, min_coverage=0.8)

    assert list(report["column"]) == ["alpha", "middle", "zebra"]


def test_build_quality_report_empty_dataframe(generator):
    """Test quality report for empty DataFrame."""
    df = pd.DataFrame({"a": [], "b": []})

    report = generator.build_quality_report(df, min_coverage=0.8)

    assert len(report) == 2


def test_build_correlation_report_numeric_columns(generator):
    """Test correlation report with numeric columns."""
    df = pd.DataFrame({
        "a": [1, 2, 3, 4, 5],
        "b": [2, 4, 6, 8, 10],  # Perfect correlation with a
        "c": [5, 4, 3, 2, 1],  # Negative correlation with a
    })

    report = generator.build_correlation_report(df)

    assert "column" in report.columns
    assert "a" in report.columns
    assert "b" in report.columns
    assert "c" in report.columns


def test_build_correlation_report_sorted_columns(generator):
    """Test that correlation report columns are sorted."""
    df = pd.DataFrame({
        "z": [1, 2],
        "a": [3, 4],
        "m": [5, 6],
    })

    report = generator.build_correlation_report(df)

    # Columns should be sorted (excluding 'column')
    numeric_cols = [c for c in report.columns if c != "column"]
    assert numeric_cols == ["a", "m", "z"]


def test_build_correlation_report_no_numeric_columns(generator):
    """Test correlation report with no numeric columns."""
    df = pd.DataFrame({
        "text_a": ["a", "b", "c"],
        "text_b": ["x", "y", "z"],
    })

    report = generator.build_correlation_report(df)

    assert list(report.columns) == ["column"]
    assert len(report) == 0


def test_build_correlation_report_mixed_types(generator):
    """Test correlation report ignores non-numeric columns."""
    df = pd.DataFrame({
        "numeric": [1, 2, 3],
        "text": ["a", "b", "c"],
        "another_numeric": [4, 5, 6],
    })

    report = generator.build_correlation_report(df)

    # Should only include numeric columns
    assert "numeric" in report.columns
    assert "another_numeric" in report.columns
    assert "text" not in report.columns


def test_build_correlation_report_bool_conversion(generator):
    """Test that boolean columns are converted to int for correlation."""
    df = pd.DataFrame({
        "numeric": [0, 1, 0, 1],
        "boolean": [False, True, False, True],
    })

    report = generator.build_correlation_report(df)

    # Boolean should be converted and correlate perfectly with numeric
    assert "boolean" in report.columns
