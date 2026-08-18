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
"""Unit tests for observability quarantine summary helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.workflow._observability_workflow_quarantine_support import (
    enrich_quarantine_summary,
)


pytestmark = pytest.mark.unit


def test_enrich_quarantine_summary_does_not_mutate_nested_stats() -> None:
    silver_stats = {"total_count": 2}
    stats = {"silver_filter_rejects": silver_stats}
    run_manifest = SimpleNamespace(
        ledger_entries=(
            SimpleNamespace(metrics_snapshot={"records_bronze": 10}),
        )
    )

    summary = enrich_quarantine_summary(
        stats=stats,
        run_id="run-1",
        run_manifest=run_manifest,
    )

    assert silver_stats == {"total_count": 2}
    assert summary["silver_filter_rejects"]["bronze_records"] == 10
    assert summary["silver_filter_rejects"]["bronze_ratio"] == pytest.approx(0.2)
