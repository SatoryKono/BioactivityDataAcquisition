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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for the supported Gold Parquet-to-Delta migration."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml
from deltalake import DeltaTable

from scripts.ops.migrations.active.migrate_gold_parquet_to_delta import (
    migrate_gold_table,
    normalize_metadata_contract,
)

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def _legacy_gold_dataset(root: Path) -> Path:
    source = root / "legacy_gold"
    source.mkdir()
    pq.write_table(
        pa.table({"entity_id": ["a", "b"], "score": [1.0, 2.0]}),
        source / "part-000.parquet",
    )
    (source / "_metadata.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "layer": "gold",
                "runtime": {"started_at_utc": "2026-07-17T08:00:00"},
                "output_ext": {"format": "parquet", "partition_count": 1},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return source


def test_dry_run_inventories_source_without_writing(tmp_path: Path) -> None:
    source = _legacy_gold_dataset(tmp_path)
    target = tmp_path / "delta_gold"

    result = migrate_gold_table(source, target)

    assert result.status == "planned"
    assert result.inventory.row_count == 2
    assert result.inventory.file_count == 1
    assert not target.exists()


def test_apply_preserves_rows_normalizes_metadata_and_is_idempotent(
    tmp_path: Path,
) -> None:
    source = _legacy_gold_dataset(tmp_path)
    target = tmp_path / "delta_gold"

    first = migrate_gold_table(
        source,
        target,
        apply=True,
        assume_naive_utc=True,
    )
    second = migrate_gold_table(
        source,
        target,
        apply=True,
        assume_naive_utc=True,
    )

    assert first.status == "applied"
    assert second.status == "already_applied"
    assert DeltaTable(str(target)).to_pyarrow_dataset().count_rows() == 2
    metadata = yaml.safe_load((target / "_metadata.yaml").read_text(encoding="utf-8"))
    assert metadata["version"] == "1.1"
    assert metadata["output_ext"]["format"] == "delta"
    assert metadata["runtime"] == {"started_at_utc": "2026-07-17T08:00:00Z"}


def test_naive_metadata_requires_explicit_operator_decision() -> None:
    with pytest.raises(ValueError, match="--assume-naive-utc"):
        normalize_metadata_contract(
            {"started_at_utc": "2026-07-17T08:00:00"},
            assume_naive_utc=False,
        )
