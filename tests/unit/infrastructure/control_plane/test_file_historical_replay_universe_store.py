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
"""Unit tests for file-backed historical replay universe storage."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.infrastructure.control_plane import FileHistoricalReplayUniverseStore

pytestmark = pytest.mark.unit


class _Report:
    def __init__(self, report_id: str, generated_at: str) -> None:
        self.report_id = report_id
        self._generated_at = generated_at

    def to_dict(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "generated_at": self._generated_at,
            "universal_claim": {"claimed": True},
            "durable_evidence_coverage_claim": {"claimed": True},
        }


def test_load_latest_report_returns_newest_artifact_payload(tmp_path) -> None:
    store = FileHistoricalReplayUniverseStore(base_path=tmp_path)
    store.save(
        _Report(
            report_id="historical-replay-universe-a",
            generated_at=datetime(2026, 5, 12, 17, 0, tzinfo=UTC).isoformat(),
        )
    )
    store.save(
        _Report(
            report_id="historical-replay-universe-b",
            generated_at=datetime(2026, 5, 12, 18, 0, tzinfo=UTC).isoformat(),
        )
    )

    payload = store.load_latest_report()

    assert payload is not None
    assert payload["report_id"] == "historical-replay-universe-b"
    assert payload["universal_claim"] == {"claimed": True}
    assert str(payload["_artifact_path"]).endswith("historical-replay-universe-b.json")


def test_load_latest_report_returns_none_for_empty_store(tmp_path) -> None:
    store = FileHistoricalReplayUniverseStore(base_path=tmp_path)

    assert store.load_latest_report() is None
