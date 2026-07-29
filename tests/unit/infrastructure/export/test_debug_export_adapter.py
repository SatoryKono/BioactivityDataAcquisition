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
"""Unit tests for persisted debug export audit packs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.application.services.debug_export_service import DebugExportPack
from bioetl.infrastructure.export.debug_export_adapter import DebugExportAdapter

pytestmark = pytest.mark.unit


def _build_pack(*, root: Path, created_at: datetime) -> DebugExportPack:
    run_id = "00000000-0000-0000-0000-000000000321"
    rows = tuple(
        {
            "run_id": run_id,
            "workflow_id": "standalone",
            "pipeline_id": "chembl_activity",
            "provider_id": "chembl",
            "stage": "silver",
            "record_index": index,
            "source_record_id": f"ACT-{index}",
            "primary_key": f"ACT-{index}",
            "payload_hash": f"hash-{index}",
            "input_payload_hash": f"input-{index}",
            "output_payload_hash": f"output-{index}",
            "status": "included",
            "reason_code": "",
            "reason_message": "",
            "rule_id": "",
            "rule_layer": "",
            "failed_field": "",
            "failed_value": "",
            "expected_constraint": "",
            "action": "include",
            "created_at": created_at.isoformat(),
            "raw_payload": "{}",
            "normalized_payload": "{}",
        }
        for index in range(5)
    )
    return DebugExportPack(
        run_id=run_id,
        pipeline_id="chembl_activity",
        provider_id="chembl",
        workflow_id="standalone",
        manifest_id=None,
        status="success",
        output_root=str(root),
        formats=("csv", "xlsx"),
        include_bom=False,
        max_rows_per_sheet=3,
        created_at=created_at,
        tables={
            "bronze_index": (),
            "silver_full": rows,
            "silver_rejected": (),
            "silver_quarantine": (),
            "gold_full": (),
            "gold_rejected": (),
            "dq_summary": (),
            "lineage": (),
            "reason_dictionary": (),
        },
        reason_dictionary=(),
    )


def test_debug_export_adapter_writes_deterministic_hash_and_split_workbook(
    tmp_path: Path,
) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    adapter = DebugExportAdapter()
    created_at_1 = datetime(2026, 6, 2, 10, 0, 0, tzinfo=UTC)
    created_at_2 = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)

    result_1 = adapter.write_pack(
        pack=_build_pack(root=tmp_path, created_at=created_at_1)
    )
    result_2 = adapter.write_pack(
        pack=_build_pack(root=tmp_path, created_at=created_at_2)
    )

    assert result_1.debug_export_hash == result_2.debug_export_hash
    root_path = Path(result_1.root_path)
    assert (root_path / "manifest.json").exists()
    assert (root_path / "silver_full.csv").exists()
    assert (root_path / "silver_full.schema.json").exists()
    workbook = openpyxl.load_workbook(root_path / "debug_export.xlsx", read_only=True)
    assert "silver_full_0001" in workbook.sheetnames
    assert "silver_full_0002" in workbook.sheetnames


def test_debug_export_adapter_skips_xlsx_when_openpyxl_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = DebugExportAdapter()

    def _raise_missing(*args: object, **kwargs: object) -> None:
        raise ModuleNotFoundError("No module named 'openpyxl'", name="openpyxl")

    monkeypatch.setattr(adapter, "_write_xlsx", _raise_missing)

    result = adapter.write_pack(
        pack=_build_pack(
            root=tmp_path,
            created_at=datetime(2026, 6, 2, 10, 0, 0, tzinfo=UTC),
        )
    )

    root_path = Path(result.root_path)
    assert (root_path / "manifest.json").exists()
    assert (root_path / "silver_full.csv").exists()
    assert not (root_path / "debug_export.xlsx").exists()
