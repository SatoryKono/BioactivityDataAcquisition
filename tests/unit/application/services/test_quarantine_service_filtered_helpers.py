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
"""Pure coverage for quarantine filtered statistics helper functions."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import bioetl.application.services._quarantine_service_filtered_helpers as helpers
from bioetl.domain.control_plane.run_ledger import RUN_FINISHED_EVENT


pytestmark = pytest.mark.unit


_RUN_ID = "00000000-0000-0000-0000-000000000123"
_NOW = datetime(2026, 7, 6, 12, 0)


class _ManifestPort:
    def __init__(self, manifests: tuple[object, ...]) -> None:
        self._manifests = manifests

    def list_all(self) -> tuple[object, ...]:
        return self._manifests


class _LedgerPort:
    def __init__(self, entries: dict[str, list[object]]) -> None:
        self._entries = entries

    def list_entries_by_run_id(self, run_id: object) -> list[object]:
        if str(run_id) == "raise":
            raise ValueError("bad run id")
        return self._entries.get(str(run_id), [])


class _RunManifestService:
    def __init__(
        self,
        *,
        manifests: tuple[object, ...] = (),
        entries: dict[str, list[object]] | None = None,
        inspections: dict[str, object] | None = None,
    ) -> None:
        self.manifest_port = _ManifestPort(manifests)
        self.ledger_port = _LedgerPort(entries or {})
        self._inspections = inspections or {}

    def show(self, run_id: str) -> object:
        if run_id == "missing":
            raise ValueError("missing")
        return self._inspections.get(run_id, SimpleNamespace(ledger_entries=()))


def _entry(
    *,
    records_bronze: object,
    event_type: str = RUN_FINISHED_EVENT,
    occurred_at: object = _NOW,
    entry_id: str = "entry",
) -> object:
    return SimpleNamespace(
        metrics_snapshot=(
            records_bronze
            if not isinstance(records_bronze, int)
            else {"records_bronze": records_bronze}
        ),
        event_type=event_type,
        occurred_at=occurred_at,
        entry_id=entry_id,
    )


def test_bronze_record_resolution_filters_invalid_metrics_and_takes_max() -> None:
    inspection = SimpleNamespace(
        ledger_entries=(
            SimpleNamespace(metrics_snapshot=None),
            _entry(records_bronze=0),
            _entry(records_bronze=10),
            _entry(records_bronze=15),
        )
    )

    assert helpers._resolve_bronze_records_from_inspection(inspection) == 15
    assert helpers._resolve_bronze_records_from_entries("not-a-sequence") is None
    assert (
        helpers._resolve_bronze_records_from_entries(
            [SimpleNamespace(metrics_snapshot=[]), _entry(records_bronze=-1)]
        )
        is None
    )
    assert (
        helpers._resolve_bronze_records_from_entries(
            [_entry(records_bronze=3), _entry(records_bronze=8)]
        )
        == 8
    )


def test_scope_resolution_uses_terminal_time_and_scope_tokens() -> None:
    first = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_type=SimpleNamespace(value="incremental"),
        run_id="run-1",
        created_at=_NOW,
    )
    second = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_type="incremental",
        run_id="run-2",
        created_at=_NOW + timedelta(minutes=1),
    )
    off_scope = SimpleNamespace(
        pipeline_name="pubchem_compound",
        run_type="backfill",
        run_id="run-3",
        created_at=_NOW + timedelta(minutes=2),
    )
    service = _RunManifestService(
        manifests=(first, second, off_scope),
        entries={
            "run-1": [
                _entry(
                    records_bronze=5,
                    occurred_at=_NOW + timedelta(minutes=5),
                    entry_id="b",
                )
            ],
            "run-2": [_entry(records_bronze=5, occurred_at="not-a-datetime")],
        },
    )

    assert helpers._parse_scope_tokens(None) == ()
    assert helpers._parse_scope_tokens("{chembl_activity,$__all, all}") == (
        "chembl_activity",
    )
    assert helpers._latest_terminal_timestamp(run_id="run-1", ledger_port=None) is None
    assert (
        helpers._latest_terminal_timestamp(
            run_id="missing",
            ledger_port=service.ledger_port,
        )
        is None
    )
    assert (
        helpers._latest_terminal_timestamp(
            run_id="run-2",
            ledger_port=service.ledger_port,
        )
        is None
    )
    assert (
        helpers._manifest_matches_scope(
            manifest=first,
            selected_pipelines=("missing",),
            selected_run_types=(),
        )
        is False
    )
    assert (
        helpers._manifest_matches_scope(
            manifest=first,
            selected_pipelines=("chembl_activity",),
            selected_run_types=(),
        )
        is True
    )
    assert (
        helpers._manifest_matches_scope(
            manifest=first,
            selected_pipelines=("chembl_activity",),
            selected_run_types=("incremental",),
        )
        is True
    )
    assert (
        helpers._pick_latest_scope_manifest(candidates=(), run_manifest_service=service)
        is None
    )
    assert (
        helpers._resolve_latest_scope_run_id(
            pipeline=None,
            run_type=None,
            run_manifest_service=SimpleNamespace(manifest_port=None),
        )
        is None
    )
    assert (
        helpers._resolve_latest_scope_run_id(
            pipeline="chembl_activity,pubchem_compound",
            run_type=None,
            run_manifest_service=service,
        )
        is None
    )
    assert (
        helpers._resolve_latest_scope_run_id(
            pipeline="missing",
            run_type=None,
            run_manifest_service=service,
        )
        is None
    )
    assert (
        helpers._resolve_latest_scope_run_id(
            pipeline="chembl_activity",
            run_type="incremental",
            run_manifest_service=service,
        )
        == "run-1"
    )


def test_filtered_stats_denominator_uses_run_scope_ledger_and_show_fallback() -> None:
    service = _RunManifestService(
        entries={
            _RUN_ID: [_entry(records_bronze=20)],
            "invalid": [_entry(records_bronze=0)],
            "raise": [],
        },
        inspections={
            "invalid": SimpleNamespace(ledger_entries=(_entry(records_bronze=7),)),
            "raise": SimpleNamespace(ledger_entries=(_entry(records_bronze=11),)),
        },
    )

    assert helpers._resolve_filtered_stats_run_ids(
        run_id="explicit",
        scoped_run_ids=["ignored"],
        pipeline=None,
        run_type=None,
        run_manifest_service=service,
    ) == ["explicit"]
    assert (
        helpers._resolve_filtered_stats_run_ids(
            run_id=None,
            scoped_run_ids=["already-scoped"],
            pipeline=None,
            run_type=None,
            run_manifest_service=service,
        )
        == []
    )
    assert (
        helpers._sum_bronze_records_for_runs(
            run_ids=[_RUN_ID, "invalid", "missing", "raise"],
            run_manifest_service=service,
        )
        == 38
    )
    assert (
        helpers._sum_bronze_records_for_runs(
            run_ids=["invalid"],
            run_manifest_service=SimpleNamespace(
                ledger_port=None,
                show=lambda run_id: SimpleNamespace(
                    ledger_entries=(_entry(records_bronze=4),)
                ),
            ),
        )
        == 4
    )

    assert helpers._enrich_filtered_stats_with_bronze_denominator(
        {"total": 2, "run_ids": [_RUN_ID]},
        pipeline=None,
        run_type=None,
        run_id=None,
        run_manifest_service=None,
    ) == {"total": 2}
    enriched = helpers._enrich_filtered_stats_with_bronze_denominator(
        {"total": 2, "run_ids": []},
        pipeline=None,
        run_type=None,
        run_id=_RUN_ID,
        run_manifest_service=service,
    )
    assert enriched["bronze_records"] == 20
    assert enriched["reject_ratio"] == 0.1
    assert (
        helpers._enrich_filtered_stats_with_bronze_denominator(
            {"total": "2", "run_ids": []},
            pipeline=None,
            run_type=None,
            run_id=_RUN_ID,
            run_manifest_service=service,
        )["reject_ratio"]
        == 0.0
    )


def test_filtered_timeseries_enrichment_normalizes_rows_and_ratios() -> None:
    service = _RunManifestService(entries={_RUN_ID: [_entry(records_bronze=10)]})

    row = {"run_ids": ["", _RUN_ID, 42], "reject_count": 5}
    assert helpers._filtered_timeseries_run_ids(dict(row)) == [_RUN_ID]
    assert helpers._reject_ratio(5, 10) == 0.5
    assert helpers._reject_ratio("5", 10) == 0.0
    assert helpers._enrich_filtered_timeseries_row(
        {"run_ids": [], "reject_count": 5},
        run_manifest_service=service,
    ) == {"reject_count": 5}
    assert helpers._enrich_filtered_timeseries_row(
        {"run_ids": [_RUN_ID], "reject_count": 5},
        run_manifest_service=None,
    ) == {"reject_count": 5}
    enriched = helpers._enrich_filtered_timeseries_row(
        {"run_ids": [_RUN_ID], "reject_count": 5},
        run_manifest_service=service,
    )
    assert enriched == {"reject_count": 5, "bronze_records": 10, "reject_ratio": 0.5}
    assert helpers._enrich_filtered_timeseries_row(
        {"run_ids": ["missing"], "reject_count": 5},
        run_manifest_service=service,
    ) == {"reject_count": 5}

    assert helpers._enrich_filtered_timeseries_with_bronze_denominators(
        {"rows": "not-a-list"},
        run_manifest_service=service,
    ) == {"rows": "not-a-list"}
    payload = helpers._enrich_filtered_timeseries_with_bronze_denominators(
        {"rows": [{"run_ids": [_RUN_ID], "reject_count": 2}, "skip"]},
        run_manifest_service=service,
    )
    assert payload["rows"] == [
        {"reject_count": 2, "bronze_records": 10, "reject_ratio": 0.2}
    ]
