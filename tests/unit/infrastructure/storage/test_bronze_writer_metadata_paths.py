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
"""Unit tests for Bronze metadata path and timing helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.infrastructure.storage.bronze.metadata_paths import (
    calculate_bronze_completed_at,
    resolve_bronze_metadata_base_path,
)


@pytest.mark.unit
class TestCalculateBronzeCompletedAt:
    """Tests for deterministic Bronze completion timestamps."""

    def test_adds_duration_to_ingestion_timestamp(self) -> None:
        started_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        completed_at = calculate_bronze_completed_at(started_at, 2.5)

        assert completed_at == datetime(2025, 1, 1, 12, 0, 2, 500000, tzinfo=UTC)


@pytest.mark.unit
class TestResolveBronzeMetadataBasePath:
    """Tests for Bronze metadata path resolution."""

    def test_returns_nested_path_when_not_flat(self, tmp_path: Path) -> None:
        result = resolve_bronze_metadata_base_path(
            base_path=tmp_path,
            provider="chembl",
            entity="activity",
            flat_structure=False,
        )

        assert result == tmp_path / "chembl" / "activity"

    def test_returns_base_path_when_flat(self, tmp_path: Path) -> None:
        result = resolve_bronze_metadata_base_path(
            base_path=tmp_path,
            provider="chembl",
            entity="activity",
            flat_structure=True,
        )

        assert result == tmp_path
