# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
"""Tests for Processed Records payload formatting and HTTP exposure."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import ARTIFACT_PUBLISHED_EVENT
from bioetl.interfaces.http import processed_records_table as processed_records_module
from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload,
    build_processed_records_table_payload_from_ledger,
)
from tests.helpers.control_plane import InMemoryRunLedgerStore


pytestmark = pytest.mark.unit


class TestProcessedRecordsTable:
    """Tests for formatted Processed Records dashboard payloads."""

    _SAMPLE_VALUES = {
        "bioetl_processed_records_bronze_current": 10000,
        "bioetl_processed_records_silver_valid_current": 9102,
        "bioetl_processed_records_silver_filtered_out_current": 851,
        "bioetl_processed_records_silver_quarantined_current": 47,
        "bioetl_processed_records_silver_skipped_current": 0,
        "bioetl_processed_records_silver_deduplicated_current": 0,
        "bioetl_processed_records_gold_written_current": 9009,
        "bioetl_processed_records_gold_excluded_by_contract_current": 0,
        "bioetl_processed_records_gold_quarantined_current": 0,
        "bioetl_processed_records_gold_skipped_current": 0,
        "bioetl_processed_records_gold_deduplicated_current": 0,
    }

    @staticmethod
    def _get_server_port(server: HealthServer) -> int:
        assert server._server is not None
        sockets = server._server.sockets
        assert sockets is not None
        return int(sockets[0].getsockname()[1])

    async def _send_request(self, port: int, path: str) -> tuple[int, str, str]:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            request = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request.encode())
            await writer.drain()

            response_line = await reader.readline()
            response_str = response_line.decode("utf-8").strip()
            parts = response_str.split(" ", 2)
            status_code = int(parts[1])
            status_text = parts[2] if len(parts) > 2 else ""

            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                header_line = line.decode("utf-8").strip()
                if ":" in header_line:
                    key, value = header_line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            content_length = int(headers.get("content-length", 0))
            body = await reader.read(content_length)
            return status_code, status_text, body.decode("utf-8")
        finally:
            writer.close()
            await writer.wait_closed()

    def test_payload_formats_row_specific_percentage_precision(self) -> None:
        """Primary rows keep one decimal while zero-valued outcomes stay visible."""
        payload = build_processed_records_table_payload(
            metric_values=self._SAMPLE_VALUES,
            pipeline="chembl_activity",
            run_type="backfill",
        )

        rows = {row["parameter"]: row for row in payload["rows"]}

        assert rows["01 bronze_records"]["value"] == "10 000"
        assert rows["02 silver_valid_records"]["value"] == (" 9 102")
        assert rows["03 silver_filtered_out_records"]["value"] == ("   851")
        assert rows["04 silver_quarantined_records"]["value"] == ("    47")
        assert rows["05 silver_skipped_records"]["value"] == ("     0")
        assert rows["06 silver_deduplicated_records"]["value"] == ("     0")
        assert rows["07 gold_written_records"]["value"] == (" 9 009")
        assert rows["08 gold_excluded_by_contract_records"]["value"] == ("     0")
        assert rows["09 gold_quarantined_records"]["value"] == ("     0")
        assert rows["10 gold_skipped_records"]["value"] == ("     0")
        assert rows["11 gold_deduplicated_records"]["value"] == ("     0")
        assert rows["01 bronze_records"]["row_status"] == ""
        assert rows["02 silver_valid_records"]["row_status"] == ""
        assert rows["03 silver_filtered_out_records"]["row_status"] == ""
        assert rows["04 silver_quarantined_records"]["row_status"] == ""
        assert rows["05 silver_skipped_records"]["row_status"] == ""
        assert rows["06 silver_deduplicated_records"]["row_status"] == ""
        assert rows["07 gold_written_records"]["row_status"] == "gold_deficit"
        assert rows["08 gold_excluded_by_contract_records"]["row_status"] == (
            "gold_deficit"
        )
        assert rows["09 gold_quarantined_records"]["row_status"] == "gold_deficit"
        assert rows["10 gold_skipped_records"]["row_status"] == "gold_deficit"
        assert rows["11 gold_deduplicated_records"]["row_status"] == ("gold_deficit")
        assert rows["01 bronze_records"]["percentage"] == "100%"
        assert rows["02 silver_valid_records"]["percentage"] == ("91.0%")
        assert rows["03 silver_filtered_out_records"]["percentage"] == ("8.51%")
        assert rows["04 silver_quarantined_records"]["percentage"] == ("0.47%")
        assert rows["07 gold_written_records"]["percentage"] == "90.1%"
        assert rows["05 silver_skipped_records"]["percentage"] == ("0%")
        assert rows["06 silver_deduplicated_records"]["percentage"] == ("0%")
        assert rows["08 gold_excluded_by_contract_records"]["percentage"] == ("0%")
        assert rows["09 gold_quarantined_records"]["percentage"] == ("0%")
        assert rows["10 gold_skipped_records"]["percentage"] == ("0%")
        assert rows["11 gold_deduplicated_records"]["percentage"] == ("0%")
        assert all("percintage" not in row for row in payload["rows"])
        assert len(payload["rows"]) == 11
        assert all("__zero" not in str(row["parameter"]) for row in payload["rows"])
        assert payload["run_type"] == ["backfill"]

    def test_payload_marks_silver_rows_when_accounting_is_below_bronze(self) -> None:
        """Visible Silver rows should get deficit status when accounting is short."""
        metric_values = dict(self._SAMPLE_VALUES)
        metric_values["bioetl_processed_records_silver_filtered_out_current"] = 850

        payload = build_processed_records_table_payload(
            metric_values=metric_values,
            pipeline="chembl_activity",
            run_type="backfill",
        )

        rows = {row["parameter"]: row for row in payload["rows"]}

        assert rows["01 bronze_records"]["row_status"] == ""
        assert rows["02 silver_valid_records"]["row_status"] == "silver_deficit"
        assert rows["03 silver_filtered_out_records"]["row_status"] == "silver_deficit"
        assert rows["04 silver_quarantined_records"]["row_status"] == "silver_deficit"
        assert rows["07 gold_written_records"]["row_status"] == "gold_deficit"

    def test_query_uses_bounded_selectors_without_run_identity_or_range(self) -> None:
        """The formatter queries current accounting metrics without run_id or $__range."""
        query = processed_records_module._processed_record_value_query(
            metric="bioetl_processed_records_gold_written_current",
            pipeline="{chembl_activity,pubchem_compound}",
            run_type="$__all",
        )

        assert query == (
            "round(sum(bioetl_processed_records_gold_written_current{"
            'pipeline=~"(?:chembl_activity|pubchem_compound)",run_type=~".*"}))'
        )
        assert "run_id" not in query
        assert "$__range" not in query
        assert "or vector(0)" not in query

    def test_unknown_pipeline_scope_returns_no_data_without_prometheus(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dashboard fallback scope should fail fast instead of fanning out Prometheus."""

        def fail_fetch(**_: object) -> dict[str, float | None]:
            raise AssertionError("unknown pipeline scope must not query Prometheus")

        monkeypatch.setattr(
            processed_records_module, "fetch_processed_record_values", fail_fetch
        )

        payload = processed_records_module.build_processed_records_table_payload_from_prometheus(
            prometheus_base_url="http://prometheus.example",
            pipeline="unknown",
            run_type="__all",
        )

        assert payload["pipeline"] == "unknown"
        assert payload["run_type"] == []
        assert len(payload["rows"]) == 11
        assert all("UNKNOWN" in str(row["value"]) for row in payload["rows"])
        assert all("UNKNOWN" in str(row["percentage"]) for row in payload["rows"])

    def test_prometheus_payload_fetches_values_for_known_pipeline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Known scopes should fetch bounded Prometheus values before formatting."""
        calls: list[dict[str, str | None]] = []

        def fake_fetch(
            *,
            prometheus_base_url: str,
            pipeline: str,
            run_type: str | None,
        ) -> dict[str, int]:
            calls.append(
                {
                    "prometheus_base_url": prometheus_base_url,
                    "pipeline": pipeline,
                    "run_type": run_type,
                }
            )
            return dict(self._SAMPLE_VALUES)

        monkeypatch.setattr(
            processed_records_module, "fetch_processed_record_values", fake_fetch
        )

        payload = processed_records_module.build_processed_records_table_payload_from_prometheus(
            prometheus_base_url="http://prometheus.example",
            pipeline="chembl_activity",
            run_type="{backfill,incremental}",
        )

        rows = {row["parameter"]: row for row in payload["rows"]}
        assert calls == [
            {
                "prometheus_base_url": "http://prometheus.example",
                "pipeline": "chembl_activity",
                "run_type": "{backfill,incremental}",
            }
        ]
        assert payload["pipeline"] == "chembl_activity"
        assert payload["run_type"] == ["backfill", "incremental"]
        assert rows["01 bronze_records"]["value"] == "10 000"
        assert rows["07 gold_written_records"]["row_status"] == "gold_deficit"

    def test_empty_ledger_payload_returns_no_data_rows(self) -> None:
        """Exact-run ledger payloads with no entries should remain deterministic."""
        payload = build_processed_records_table_payload_from_ledger(
            pipeline="chembl_target",
            run_type="{backfill,incremental}",
            ledger_entries=(),
        )

        assert payload["pipeline"] == "chembl_target"
        assert payload["run_type"] == ["backfill", "incremental"]
        assert len(payload["rows"]) == 11
        assert all("UNKNOWN" in str(row["value"]) for row in payload["rows"])
        assert all("UNKNOWN" in str(row["percentage"]) for row in payload["rows"])
        # Empty-ledger responses carry v2 to signal the UNKNOWN-row semantic
        # (ADR-044 §Ops-HTTP contract).  Populated-entries responses keep v1.
        assert payload["contract"] == "processed_records_table_v2"

    def test_ledger_payload_uses_metrics_snapshot_when_artifacts_are_absent(
        self,
    ) -> None:
        """RunLedger snapshots should format exact-run rows without artifacts."""
        run_id = deterministic_run_uuid_from_callsite("test_processed_records_table")
        payload = build_processed_records_table_payload_from_ledger(
            pipeline="chembl_target",
            run_type="backfill",
            ledger_entries=(
                RunLedgerEntry(
                    entry_id="finished",
                    manifest_id="manifest-chembl-target",
                    run_id=run_id,
                    event_type="run_finished",
                    occurred_at=datetime(2026, 5, 29, 17, 37, tzinfo=UTC),
                    status="success",
                    metrics_snapshot={
                        "records_bronze": 10,
                        "records_silver": 8,
                        "records_gold": 7,
                        "records_quarantined": 1,
                        "records_filtered_out": 1,
                        "records_gold_excluded_by_contract": 1,
                    },
                ),
            ),
        )

        assert payload["contract"] == "processed_records_table_v1"

        rows = {row["parameter"]: row for row in payload["rows"]}
        assert rows["01 bronze_records"]["value"] == "10"
        assert rows["02 silver_valid_records"]["value"] == " 8"
        assert rows["03 silver_filtered_out_records"]["value"] == (" 1")
        assert rows["04 silver_quarantined_records"]["value"] == (" 1")
        assert rows["07 gold_written_records"]["value"] == " 7"
        assert rows["08 gold_excluded_by_contract_records"]["value"] == (" 1")
        assert rows["07 gold_written_records"]["row_status"] == ""

    def test_ledger_artifact_count_above_snapshot_does_not_deduplicate(
        self,
    ) -> None:
        """Artifact corrections must not create negative deduplication counts."""
        run_id = deterministic_run_uuid_from_callsite("test_processed_records_table")
        occurred_at = datetime(2026, 5, 29, 17, 37, tzinfo=UTC)
        payload = build_processed_records_table_payload_from_ledger(
            pipeline="chembl_target",
            run_type="backfill",
            ledger_entries=(
                RunLedgerEntry(
                    entry_id="finished",
                    manifest_id="manifest-chembl-target",
                    run_id=run_id,
                    event_type="run_finished",
                    occurred_at=occurred_at,
                    status="success",
                    metrics_snapshot={
                        "records_bronze": 10,
                        "records_silver": 3,
                        "records_gold": 5,
                    },
                ),
                RunLedgerEntry(
                    entry_id="silver-artifact",
                    manifest_id="manifest-chembl-target",
                    run_id=run_id,
                    event_type=ARTIFACT_PUBLISHED_EVENT,
                    occurred_at=occurred_at,
                    stage="silver",
                    status="published",
                    details={"stage": "silver", "record_count": 5},
                ),
            ),
        )

        rows = {row["parameter"]: row for row in payload["rows"]}
        assert rows["02 silver_valid_records"]["value"] == " 5"
        assert rows["06 silver_deduplicated_records"]["value"] == (" 0")
        assert rows["06 silver_deduplicated_records"]["percentage"] == ("0%")

    def test_exact_run_payload_uses_run_ledger_artifacts_as_source_of_truth(
        self,
    ) -> None:
        """Exact-run Processed Records should not contradict published artifacts."""
        run_id = deterministic_run_uuid_from_callsite("test_processed_records_table")
        occurred_at = datetime(2026, 5, 29, 17, 37, tzinfo=UTC)
        payload = build_processed_records_table_payload_from_ledger(
            pipeline="chembl_target",
            run_type="backfill",
            ledger_entries=(
                RunLedgerEntry(
                    entry_id="finished",
                    manifest_id="manifest-chembl-target",
                    run_id=run_id,
                    event_type="run_finished",
                    occurred_at=occurred_at,
                    status="success",
                    metrics_snapshot={
                        "records_bronze": 1000,
                        "records_silver": 993,
                        "records_gold": 993,
                        "records_quarantined": 7,
                        "records_filtered_out": 0,
                        "records_gold_excluded_by_contract": 0,
                    },
                ),
                RunLedgerEntry(
                    entry_id="silver-artifact",
                    manifest_id="manifest-chembl-target",
                    run_id=run_id,
                    event_type=ARTIFACT_PUBLISHED_EVENT,
                    occurred_at=occurred_at,
                    stage="silver",
                    status="published",
                    details={"stage": "silver", "record_count": 990},
                ),
                RunLedgerEntry(
                    entry_id="gold-artifact",
                    manifest_id="manifest-chembl-target",
                    run_id=run_id,
                    event_type=ARTIFACT_PUBLISHED_EVENT,
                    occurred_at=occurred_at,
                    stage="gold",
                    status="published",
                    details={"stage": "gold", "record_count": 993},
                ),
            ),
        )

        rows = {row["parameter"]: row for row in payload["rows"]}
        assert rows["02 silver_valid_records"]["value"] == ("  990")
        assert rows["06 silver_deduplicated_records"]["value"] == ("    3")
        assert rows["06 silver_deduplicated_records"]["percentage"] == ("0.3%")
        assert rows["02 silver_valid_records"]["row_status"] == ""
        assert rows["06 silver_deduplicated_records"]["row_status"] == ""
        assert rows["07 gold_written_records"]["value"] == ("  993")
        assert rows["08 gold_excluded_by_contract_records"]["value"] == ("    0")
        assert rows["07 gold_written_records"]["row_status"] == ""

    @pytest.mark.asyncio
    async def test_observability_processed_records_endpoint_returns_rows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Health server should expose formatted rows for the Grafana table."""

        def fake_fetch(
            *,
            prometheus_base_url: str,
            pipeline: str,
            run_type: str | None,
        ) -> dict[str, int]:
            assert prometheus_base_url == "http://prometheus.example"
            assert pipeline == "chembl_activity"
            assert run_type == "backfill"
            return dict(self._SAMPLE_VALUES)

        monkeypatch.setattr(
            processed_records_module, "fetch_processed_record_values", fake_fetch
        )
        server = HealthServer(
            host="127.0.0.1", port=0, prometheus_base_url="http://prometheus.example"
        )
        await server.start()
        try:
            port = self._get_server_port(server)
            empty_status, _, empty_body = await self._send_request(
                port,
                "/ops/observability/processed-records?"
                "pipeline=chembl_activity&run_type=backfill&run_id=-",
            )
            status_code, _, body = await self._send_request(
                port,
                "/ops/observability/processed-records?"
                "pipeline=chembl_activity&run_type=backfill"
                "&run_id=00000000-0000-4000-8000-000000000001",
            )
        finally:
            await server.stop()

        assert empty_status == 200
        empty = json.loads(empty_body)
        assert empty["contract"] == "processed_records_table_v1"
        assert empty["selection"] == "required"
        assert empty["rows"] == []

        assert status_code == 200
        data = json.loads(body)
        rows = {row["parameter"]: row for row in data["rows"]}
        assert data["contract"] == "processed_records_table_v1"
        assert rows["01 bronze_records"]["value"] == "10 000"
        assert rows["03 silver_filtered_out_records"]["value"] == ("   851")
        assert rows["02 silver_valid_records"]["row_status"] == ""
        assert rows["07 gold_written_records"]["row_status"] == "gold_deficit"
        assert rows["02 silver_valid_records"]["percentage"] == "91.0%"
        assert rows["07 gold_written_records"]["percentage"] == "90.1%"
        assert rows["05 silver_skipped_records"]["value"] == ("     0")
        assert rows["11 gold_deduplicated_records"]["value"] == ("     0")

    @pytest.mark.asyncio
    async def test_observability_processed_records_endpoint_prefers_exact_run_ledger(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Exact run_id scopes should use RunLedger instead of current Prometheus rows."""
        run_id = deterministic_run_uuid_from_callsite("test_processed_records_table")
        ledger_store = InMemoryRunLedgerStore()
        ledger_store.append(
            RunLedgerEntry(
                entry_id="finished",
                manifest_id="manifest-exact",
                run_id=run_id,
                event_type="run_finished",
                occurred_at=datetime(2026, 5, 29, 17, 37, tzinfo=UTC),
                status="success",
                metrics_snapshot={
                    "records_bronze": 1000,
                    "records_silver": 993,
                    "records_gold": 993,
                    "records_quarantined": 7,
                    "records_filtered_out": 0,
                    "records_gold_excluded_by_contract": 0,
                },
            )
        )

        def fail_fetch(**_: object) -> dict[str, float | None]:
            raise AssertionError("exact run_id must not query Prometheus")

        monkeypatch.setattr(
            processed_records_module, "fetch_processed_record_values", fail_fetch
        )
        server = HealthServer(
            host="127.0.0.1",
            port=0,
            prometheus_base_url="http://prometheus.example",
            run_ledger_port=ledger_store,
        )
        await server.start()
        try:
            port = self._get_server_port(server)
            status_code, _, body = await self._send_request(
                port,
                "/ops/observability/processed-records?"
                f"pipeline=chembl_target&run_type=backfill&run_id={run_id}",
            )
        finally:
            await server.stop()

        assert status_code == 200
        data = json.loads(body)
        rows = {row["parameter"]: row for row in data["rows"]}
        assert rows["07 gold_written_records"]["value"] == ("  993")
        assert rows["08 gold_excluded_by_contract_records"]["value"] == ("    0")
