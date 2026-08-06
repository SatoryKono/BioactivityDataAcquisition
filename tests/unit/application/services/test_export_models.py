# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Direct unit tests for export service models."""

from __future__ import annotations

import pytest

from bioetl.application.services.export_lineage.export_models import (
    ColumnInfo,
    ExportOptions,
    ExportResult,
    TableInfo,
    TablePreview,
)
from tests.helpers.synthetic_paths import synthetic_test_root

TEST_ROOT = synthetic_test_root("export-models")
ACTIVITY_CSV_PATH = TEST_ROOT / "activity.csv"
SILVER_ACTIVITY_PATH = TEST_ROOT / "silver" / "activity"


@pytest.mark.unit
class TestExportResult:
    def test_success_is_true_without_error(self) -> None:
        result = ExportResult(
            table_name="silver.activity",
            layer="silver",
            format="csv",
            output_path=ACTIVITY_CSV_PATH,
            row_count=10,
        )

        assert result.success is True

    def test_success_is_false_when_error_present(self) -> None:
        result = ExportResult(
            table_name="silver.activity",
            layer="silver",
            format="xlsx",
            output_path=None,
            row_count=0,
            error="write failed",
        )

        assert result.success is False


@pytest.mark.unit
class TestExportOptionsAndTableModels:
    def test_export_options_defaults_are_stable(self) -> None:
        options = ExportOptions()

        assert options.format == "csv"
        assert options.output_path is None
        assert options.limit is None
        assert options.columns is None
        assert options.include_manifests is True
        assert options.manifest_strict is False
        assert options.manifest_generated_at is None
        assert options.allow_nondeterministic_manifest_timestamp is False
        assert options.run_ids == ()
        assert options.code_revision is None
        assert options.requester is None
        assert options.role == "viewer"
        assert options.filters_hash is None
        assert options.expires_at is None
        assert options.redaction_profile == "default"

    def test_export_result_carries_governance_metadata(self) -> None:
        result = ExportResult(
            table_name="silver.activity",
            layer="silver",
            format="csv",
            output_path=ACTIVITY_CSV_PATH,
            row_count=10,
            audit_ref="export-audit:abc",
            checksum_manifest_path=TEST_ROOT / "activity.checksums-manifest.json",
            expires_at="2026-07-01T00:00:00Z",
            redaction_profile="default",
            redacted_columns=("raw_payload",),
        )

        assert result.audit_ref == "export-audit:abc"
        assert result.checksum_manifest_path is not None
        assert result.expires_at == "2026-07-01T00:00:00Z"
        assert result.redaction_profile == "default"
        assert result.redacted_columns == ("raw_payload",)

    def test_preview_and_table_info_preserve_payload(self) -> None:
        preview = TablePreview(
            table_name="silver.activity",
            layer="silver",
            row_count=2,
            columns=(ColumnInfo(name="id", type="int64", nullable=False),),
            sample_rows=({"id": 1}, {"id": 2}),
        )
        table_info = TableInfo(
            name="silver.activity",
            layer="silver",
            path=SILVER_ACTIVITY_PATH,
        )

        assert preview.columns[0].name == "id"
        assert preview.sample_rows[1]["id"] == 2
        assert table_info.path == SILVER_ACTIVITY_PATH
