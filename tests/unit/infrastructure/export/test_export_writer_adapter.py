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
"""Tests for ExportWriterAdapter."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from bioetl.infrastructure.export import ExportWriterAdapter


pytestmark = pytest.mark.unit


@pytest.fixture
def table() -> pa.Table:
    return pa.Table.from_pydict({"col1": ["a", "b"], "col2": [1, 2]})


def test_write_export_creates_csv_file(
    table: pa.Table,
    tmp_path: Path,
) -> None:
    adapter = ExportWriterAdapter()

    output_path = Path(
        adapter.write_export(
            table=table,
            table_name="chembl.activity",
            layer="silver",
            fmt="csv",
            output_dir=str(tmp_path / "exports"),
        )
    )

    assert output_path.exists()
    assert output_path.name == "silver_chembl_activity.csv"


def test_write_export_rejects_unsupported_format(
    table: pa.Table,
    tmp_path: Path,
) -> None:
    adapter = ExportWriterAdapter()

    with pytest.raises(ValueError, match="Unsupported format"):
        adapter.write_export(
            table=table,
            table_name="chembl.activity",
            layer="silver",
            fmt="json",
            output_dir=str(tmp_path / "exports"),
        )


def test_write_manifest_creates_stable_json(tmp_path: Path) -> None:
    adapter = ExportWriterAdapter()

    output_path = Path(
        adapter.write_manifest(
            manifest_name="silver_chembl_activity.provenance-manifest",
            payload={"b": 2, "a": 1},
            output_dir=str(tmp_path / "exports"),
        )
    )

    assert output_path.name == "silver_chembl_activity.provenance-manifest.json"
    assert output_path.read_text(encoding="utf-8") == '{\n  "a": 1,\n  "b": 2\n}\n'


def test_fingerprint_file_returns_sha256_and_size(tmp_path: Path) -> None:
    adapter = ExportWriterAdapter()
    output_path = tmp_path / "exports" / "data.csv"
    output_path.parent.mkdir()
    output_path.write_text("export", encoding="utf-8")

    fingerprint = adapter.fingerprint_file(path=str(output_path))

    assert fingerprint.path == str(output_path)
    assert fingerprint.size_bytes == 6
    assert fingerprint.sha256 == (
        "d46aee08cc49f6d1eb41800c1d6bab4506c960c700cff0efffe490d7cb1de5e3"
    )
