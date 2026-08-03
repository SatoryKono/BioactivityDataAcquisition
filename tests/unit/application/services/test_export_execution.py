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
"""Unit tests for governed export execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import bioetl.application.services.export_execution as export_execution
from bioetl.application.services.export_models import ExportOptions

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _Field:
    name: str


class _Table:
    def __init__(self, columns: tuple[str, ...], *, rows: int = 3) -> None:
        self.schema = tuple(_Field(name) for name in columns)
        self.num_rows = rows
        self.selected_columns: tuple[str, ...] | None = None

    def select(self, columns: list[str]) -> _Table:
        selected = _Table(tuple(columns), rows=self.num_rows)
        selected.selected_columns = tuple(columns)
        return selected


def test_build_audit_ref_is_stable_and_includes_governance_material() -> None:
    options = ExportOptions(
        format="csv",
        requester="analyst@example.test",
        role="viewer",
        filters_hash="sha256:filters",
        run_ids=("run-2", "run-1"),
        code_revision="abc123",
        expires_at="2026-07-01T00:00:00Z",
    )

    payload = export_execution.build_audit_ref_payload(
        table_name="activity",
        layer="gold",
        options=options,
        row_count=7,
        output_columns=("activity_id", "standard_value"),
        redacted_columns=("raw_payload",),
    )
    first = export_execution.build_audit_ref(
        table_name="activity",
        layer="gold",
        options=options,
        row_count=7,
        output_columns=("activity_id", "standard_value"),
        redacted_columns=("raw_payload",),
    )
    second = export_execution.build_audit_ref(
        table_name="activity",
        layer="gold",
        options=options,
        row_count=7,
        output_columns=("activity_id", "standard_value"),
        redacted_columns=("raw_payload",),
    )

    assert payload["requester"] == "analyst@example.test"
    assert payload["run_ids"] == ("run-2", "run-1")
    assert first == second
    assert first.startswith("export-audit:")
    assert len(first.removeprefix("export-audit:")) == 24


def test_apply_redaction_policy_removes_sensitive_columns_for_viewer() -> None:
    table = _Table(("id", "raw_payload", "access_token", "standard_value"))

    redacted, redacted_columns = export_execution.apply_redaction_policy(
        table=table,
        options=ExportOptions(role="viewer"),
    )

    assert tuple(field.name for field in redacted.schema) == ("id", "standard_value")
    assert redacted_columns == ("raw_payload", "access_token")


def test_apply_redaction_policy_allows_privileged_roles_and_blocks_raw_viewer() -> None:
    table = _Table(("id", "raw_payload"))

    unredacted, redacted_columns = export_execution.apply_redaction_policy(
        table=table,
        options=ExportOptions(role="exporter", redaction_profile="none"),
    )

    assert unredacted is table
    assert redacted_columns == ()
    with pytest.raises(PermissionError, match="cannot export raw sensitive fields"):
        export_execution.apply_redaction_policy(
            table=table,
            options=ExportOptions(role="viewer", redaction_profile="none"),
        )


def test_create_results_preserve_control_plane_export_metadata() -> None:
    options = ExportOptions(
        format="tsv",
        expires_at="2026-07-01T00:00:00Z",
        redaction_profile="default",
    )

    success = export_execution.create_success_result(
        table_name="activity",
        layer="silver",
        options=options,
        output_path=Path("exports/activity.tsv"),
        row_count=11,
        manifest_paths=(Path("exports/activity.manifest.json"),),
        audit_ref="export-audit:abc",
        redacted_columns=("raw_payload",),
    )
    missing = export_execution.create_missing_table_result(
        table_name="missing",
        layer="gold",
        options=options,
        table_path=Path("gold/missing"),
    )
    failed = export_execution.create_failed_result(
        table_name="activity",
        layer="silver",
        options=options,
        error="boom",
    )

    assert success.success is True
    assert success.checksum_manifest_path == Path("exports/activity.manifest.json")
    assert success.redacted_columns == ("raw_payload",)
    assert missing.success is False
    assert missing.audit_ref is not None
    assert failed.error == "boom"
    assert failed.audit_ref is not None


def test_get_layer_base_path_accepts_only_medallion_export_layers() -> None:
    assert export_execution.get_layer_base_path(
        layer="silver",
        silver_path=Path("silver"),
        gold_path=Path("gold"),
    ) == Path("silver")
    assert export_execution.get_layer_base_path(
        layer="gold",
        silver_path=Path("silver"),
        gold_path=Path("gold"),
    ) == Path("gold")
    with pytest.raises(ValueError, match="Invalid layer"):
        export_execution.get_layer_base_path(
            layer="bronze",
            silver_path=Path("silver"),
            gold_path=Path("gold"),
        )


def test_write_export_manifests_if_enabled_delegates_with_deterministic_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_write_export_sidecar_manifests(**kwargs: object) -> tuple[Path, ...]:
        calls.append(kwargs)
        return (Path("exports/activity.manifest.json"),)

    monkeypatch.setattr(
        export_execution,
        "write_export_sidecar_manifests",
        fake_write_export_sidecar_manifests,
    )
    options = ExportOptions(
        include_manifests=True,
        manifest_generated_at="2026-06-30T00:00:00Z",
        allow_nondeterministic_manifest_timestamp=False,
        run_ids=("run-1",),
        code_revision="abc123",
        requester="analyst@example.test",
        role="investigator",
    )

    paths = export_execution.write_export_manifests_if_enabled(
        writer=MagicMock(),
        table=_Table(("id",)),
        table_name="activity",
        layer="gold",
        options=options,
        output_path=Path("exports/activity.csv"),
        row_count=1,
        audit_ref="export-audit:abc",
        redacted_columns=(),
    )
    disabled = export_execution.write_export_manifests_if_enabled(
        writer=MagicMock(),
        table=_Table(("id",)),
        table_name="activity",
        layer="gold",
        options=ExportOptions(include_manifests=False),
        output_path=Path("exports/activity.csv"),
        row_count=1,
        audit_ref="export-audit:abc",
        redacted_columns=(),
    )

    assert paths == (Path("exports/activity.manifest.json"),)
    assert disabled == ()
    assert calls[0]["timestamp_opts"] == ("2026-06-30T00:00:00Z", False, None)
    assert calls[0]["run_ids"] == ("run-1",)
    assert calls[0]["access"] == (
        "analyst@example.test",
        "investigator",
        None,
        None,
        "default",
        "export-audit:abc",
    )


async def test_export_existing_table_redacts_writes_and_logs_manifest_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = _Table(("id", "raw_payload"), rows=2)
    reader = SimpleNamespace(read_table=AsyncMock(return_value=table))
    writer = MagicMock()
    writer.write_export.return_value = Path("exports/activity.csv")
    logger = MagicMock()
    manifest_paths = (Path("exports/activity.manifest.json"),)
    monkeypatch.setattr(
        export_execution,
        "write_export_sidecar_manifests",
        MagicMock(return_value=manifest_paths),
    )

    result = await export_execution.export_existing_table(
        reader=reader,
        writer=writer,
        logger=logger,
        export_path=Path("exports"),
        table_name="activity",
        layer="gold",
        options=ExportOptions(
            format="csv",
            include_manifests=True,
            role="viewer",
            manifest_generated_at="2026-06-30T00:00:00Z",
            allow_nondeterministic_manifest_timestamp=False,
        ),
        table_path=Path("gold/activity"),
    )

    reader.read_table.assert_awaited_once_with(
        "gold/activity",
        columns=None,
        limit=None,
    )
    writer.write_export.assert_called_once()
    assert tuple(
        field.name for field in writer.write_export.call_args.kwargs["table"].schema
    ) == ("id",)
    assert result.success is True
    assert result.row_count == 2
    assert result.manifest_paths == manifest_paths
    assert result.redacted_columns == ("raw_payload",)
    assert result.audit_ref is not None
    assert logger.info.call_count == 2
