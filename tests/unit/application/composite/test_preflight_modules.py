"""Unit tests for preflight modules — types, rules, reporting, orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.composite._preflight_orchestration import (
    PreflightSchemaOrchestrationMixin,
)
from bioetl.application.composite._preflight_reporting import (
    PreflightValidationReportingMixin,
)
from bioetl.application.composite.preflight_validator import CompositePreflightValidator
from bioetl.application.composite._preflight_types import (
    FieldInfo,
    PreflightValidationError,
    PreflightValidationResult,
    SchemaFields,
    ValidationIssue,
)


# ---------------------------------------------------------------------------
# _preflight_types
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPreflightTypes:
    """Test preflight shared type dataclasses."""

    def test_field_info_creation(self) -> None:
        fi = FieldInfo(name="doi", dtype="str", nullable=True, source="chembl")
        assert fi.name == "doi"
        assert fi.source == "chembl"

    def test_validation_issue_default_severity(self) -> None:
        issue = ValidationIssue(
            field="doi",
            source="chembl",
            issue_type="missing_field",
            message="not found",
        )
        assert issue.severity == "error"

    def test_validation_issue_warning_severity(self) -> None:
        issue = ValidationIssue(
            field="doi",
            source="chembl",
            issue_type="missing_field",
            message="not found",
            severity="warning",
        )
        assert issue.severity == "warning"

    def test_preflight_result_errors_filter(self) -> None:
        result = PreflightValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    field="a", source="s", issue_type="t", message="m", severity="error"
                ),
                ValidationIssue(
                    field="b",
                    source="s",
                    issue_type="t",
                    message="m",
                    severity="warning",
                ),
            ],
        )
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_preflight_validation_error_message(self) -> None:
        result = PreflightValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    field="doi", source="x", issue_type="type_mismatch", message="bad"
                ),
            ],
        )
        error = PreflightValidationError(result)
        assert "1 error(s)" in str(error)
        assert error.result is result


# ---------------------------------------------------------------------------
# preflight_validator rule helpers
# ---------------------------------------------------------------------------


def _make_validator() -> CompositePreflightValidator:
    return CompositePreflightValidator(MagicMock())


@pytest.mark.unit
class TestPreflightRules:
    """Test canonical validator rule checks."""

    def test_get_valid_sources_from_config(self) -> None:
        validator = _make_validator()
        config = MagicMock()
        config.seed.pipeline = "chembl_compound"
        enricher = MagicMock()
        enricher.pipeline = "crossref_publication"
        config.enrichers = [enricher]

        sources = validator._get_valid_sources(config)

        assert "seed" in sources
        assert "chembl" in sources
        assert "crossref" in sources

    def test_validate_field_priority_unknown_source(self) -> None:
        validator = _make_validator()
        issues, resolved = validator._validate_field_priority(
            "doi",
            ("unknown_provider",),
            frozenset({"seed", "chembl"}),
            {},
        )
        assert any(i.issue_type == "unknown_source" for i in issues)
        assert resolved is None

    def test_validate_field_priority_missing_field(self) -> None:
        validator = _make_validator()
        source_fields: dict[str, SchemaFields] = {"chembl": {}}
        issues, _ = validator._validate_field_priority(
            "nonexistent",
            ("chembl",),
            frozenset({"seed", "chembl"}),
            source_fields,
        )
        assert any(i.issue_type == "missing_field" for i in issues)

    def test_validate_field_priority_resolves_first_available(self) -> None:
        validator = _make_validator()
        source_fields: dict[str, SchemaFields] = {
            "chembl": {
                "doi": FieldInfo(
                    name="doi", dtype="str", nullable=True, source="chembl"
                )
            },
        }
        _, resolved = validator._validate_field_priority(
            "doi",
            ("chembl",),
            frozenset({"seed", "chembl"}),
            source_fields,
        )
        assert resolved == "chembl"

    def test_check_type_compatibility_compatible(self) -> None:
        validator = _make_validator()
        result = validator._check_type_compatibility(
            "field", {"chembl": "str", "crossref": "String"}
        )
        assert result is None

    def test_check_type_compatibility_incompatible(self) -> None:
        validator = _make_validator()
        result = validator._check_type_compatibility(
            "field", {"chembl": "str", "crossref": "int"}
        )
        assert result is not None
        assert result.issue_type == "type_mismatch"

    def test_dtype_in_group(self) -> None:
        validator = _make_validator()
        group = frozenset({"str", "object", "String"})
        assert validator._dtype_in_group("str", group) is True
        assert validator._dtype_in_group("String", group) is True
        assert validator._dtype_in_group("int", group) is False


# ---------------------------------------------------------------------------
# _preflight_reporting
# ---------------------------------------------------------------------------


def _make_reporting_mixin() -> PreflightValidationReportingMixin:
    mixin = PreflightValidationReportingMixin.__new__(PreflightValidationReportingMixin)
    mixin._logger = MagicMock()
    return mixin


@pytest.mark.unit
class TestPreflightReporting:
    """Test PreflightValidationReportingMixin logging helpers."""

    def test_log_schema_loading_summary(self) -> None:
        mixin = _make_reporting_mixin()
        source_fields = {
            "chembl": {"doi": FieldInfo("doi", "str", True, "chembl")},
        }
        mixin._log_schema_loading_summary(source_fields)
        mixin._logger.debug.assert_called_once()

    def test_log_validation_result_pass(self) -> None:
        mixin = _make_reporting_mixin()
        config = MagicMock()
        config.name = "pub_enriched"
        result = PreflightValidationResult(
            is_valid=True, resolved_fields={"doi": "chembl"}
        )

        mixin._log_validation_result(
            is_valid=True, config=config, result=result, field_priorities_count=1
        )

        mixin._logger.info.assert_called_once()

    def test_log_validation_result_fail(self) -> None:
        mixin = _make_reporting_mixin()
        config = MagicMock()
        config.name = "pub_enriched"
        result = PreflightValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    field="doi", source="x", issue_type="missing", message="gone"
                ),
            ],
        )

        mixin._log_validation_result(
            is_valid=False, config=config, result=result, field_priorities_count=1
        )

        mixin._logger.error.assert_called_once()

    def test_log_resolved_field_sources_empty(self) -> None:
        mixin = _make_reporting_mixin()
        result = PreflightValidationResult(is_valid=True)

        mixin.log_resolved_field_sources(result, "pub")

        mixin._logger.info.assert_not_called()

    def test_log_resolved_field_sources_populated(self) -> None:
        mixin = _make_reporting_mixin()
        result = PreflightValidationResult(
            is_valid=True, resolved_fields={"doi": "chembl", "title": "crossref"}
        )

        mixin.log_resolved_field_sources(result, "pub")

        assert mixin._logger.info.call_count == 1
        assert mixin._logger.debug.call_count == 2


# ---------------------------------------------------------------------------
# _preflight_orchestration
# ---------------------------------------------------------------------------


def _make_orchestration_mixin() -> PreflightSchemaOrchestrationMixin:
    mixin = PreflightSchemaOrchestrationMixin.__new__(PreflightSchemaOrchestrationMixin)
    mixin._logger = MagicMock()
    # Reset class-level registry to avoid cross-test pollution
    PreflightSchemaOrchestrationMixin._SCHEMA_REGISTRY = None
    return mixin


@pytest.mark.unit
class TestPreflightOrchestration:
    """Test PreflightSchemaOrchestrationMixin schema extraction."""

    def test_simplify_dtype_known_types(self) -> None:
        mixin = _make_orchestration_mixin()
        assert mixin._simplify_dtype("Int64") == "int"
        assert mixin._simplify_dtype("Float64") == "float"
        assert mixin._simplify_dtype("string") == "str"
        assert mixin._simplify_dtype("boolean") == "bool"

    def test_simplify_dtype_strips_prefix(self) -> None:
        mixin = _make_orchestration_mixin()
        assert mixin._simplify_dtype("pandas.Int64Dtype()") == "int"

    def test_extract_dtype_from_annotation_series(self) -> None:
        mixin = _make_orchestration_mixin()
        assert mixin._extract_dtype_from_annotation("Series[Int64]") == "int"

    def test_extract_dtype_from_annotation_plain(self) -> None:
        mixin = _make_orchestration_mixin()
        assert mixin._extract_dtype_from_annotation("float64") == "float"

    def test_load_pipeline_schema_fields_no_underscore(self) -> None:
        mixin = _make_orchestration_mixin()
        result = mixin._load_pipeline_schema_fields("nounderscore")
        assert result is None

    def test_extract_fields_from_annotations_skips_private(self) -> None:
        mixin = _make_orchestration_mixin()

        class FakeSchema:
            __annotations__ = {
                "doi": "Series[str]",
                "title": "Series[str]",
                "_internal": "int",
                "_source": "str",
            }

        # FakeSchema has no __mro__ beyond object, so walk it manually
        fields = mixin._extract_fields_from_annotations(FakeSchema, "test")

        # _internal should be skipped, but _source is whitelisted
        assert "doi" in fields
        assert "title" in fields
        assert "_internal" not in fields
        assert "_source" in fields
