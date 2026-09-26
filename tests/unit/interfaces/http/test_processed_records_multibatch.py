"""Local regression reproducer; no data writes or runtime mutation."""

from datetime import UTC, datetime
from dataclasses import replace
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite
import pytest
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.interfaces.http.processed_records_table import (
    build_processed_records_table_payload_from_ledger,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def rows():
    run_id = deterministic_run_uuid_from_callsite("processed_records_multibatch")
    entries = []
    for stage, counts in {
        "bronze": (1000, 1000, 25),
        "silver": (1000, 995, 25),
        "gold": (983, 983, 25),
    }.items():
        for index, count in enumerate(counts):
            entries.append(
                RunLedgerEntry(
                    entry_id=f"{stage}-{index}",
                    manifest_id="manifest",
                    run_id=run_id,
                    event_type="artifact_published",
                    occurred_at=datetime(2026, 9, 15, 11, index, tzinfo=UTC),
                    stage=stage,
                    status="published",
                    idempotency_key=f"{stage}-{index}",
                    details={"stage": stage, "record_count": count},
                )
            )
    entries.append(
        RunLedgerEntry(
            entry_id="finished",
            manifest_id="manifest",
            run_id=run_id,
            event_type="run_finished",
            occurred_at=datetime(2026, 9, 15, 12, tzinfo=UTC),
            status="success",
            metrics_snapshot={
                "records_bronze": 2025,
                "records_silver": 2025,
                "records_gold": 1991,
                "records_gold_excluded_by_contract": 34,
                "records_filtered_out": 0,
                "records_quarantined": 0,
            },
        )
    )
    payload = build_processed_records_table_payload_from_ledger(
        ledger_entries=tuple(entries), pipeline="chembl_assay", run_type="backfill"
    )
    return {row["parameter"]: row for row in payload["rows"]}


@pytest.mark.parametrize(
    ("parameter", "expected"),
    [
        ("01 bronze_records", 2025),
        ("02 silver_valid_records", 2020),
        ("07 gold_written_records", 1991),
        ("06 silver_deduplicated_records", 5),
    ],
)
def test_distinct_batch_publications_are_not_last_batch_totals(
    rows, parameter, expected
):
    assert int(rows[parameter]["value"].replace(" ", "")) == expected


@pytest.mark.unit
def test_gold_exclusion_percentage_uses_run_bronze_total(rows):
    assert rows["08 gold_excluded_by_contract_records"]["percentage"] == "1.679%"


@pytest.mark.parametrize("use_idempotency_key", [False, True])
def test_repeated_publication_is_counted_once(use_idempotency_key):
    from bioetl.interfaces.http._processed_records_table_support import (
        published_layer_artifact_counts,
    )

    entry = RunLedgerEntry(
        entry_id="first",
        manifest_id="manifest",
        run_id=deterministic_run_uuid_from_callsite("repeated_publication"),
        event_type="artifact_published",
        occurred_at=datetime(2026, 9, 15, tzinfo=UTC),
        stage="gold",
        dataset_ref="gold:chembl.assay",
        idempotency_key="publication" if use_idempotency_key else None,
        details={"record_count": 1000},
    )
    repeated = replace(entry, entry_id="retry") if use_idempotency_key else entry
    next_batch = replace(
        entry,
        entry_id="next",
        idempotency_key="next" if use_idempotency_key else None,
        details={"record_count": 25},
    )
    assert published_layer_artifact_counts((entry, repeated, next_batch)) == {
        "gold": 1025
    }


@pytest.mark.unit
def test_conflicting_publication_identity_fails_closed():
    from bioetl.interfaces.http._processed_records_table_support import (
        published_layer_artifact_counts,
    )

    entry = RunLedgerEntry(
        entry_id="first",
        manifest_id="manifest",
        run_id=deterministic_run_uuid_from_callsite("conflicting_publication"),
        event_type="artifact_published",
        occurred_at=datetime(2026, 9, 15, tzinfo=UTC),
        stage="silver",
        idempotency_key="publication",
        details={"record_count": 1000},
    )
    conflict = replace(entry, entry_id="retry", details={"record_count": 25})
    with pytest.raises(RuntimeError, match="Conflicting record counts"):
        published_layer_artifact_counts((entry, conflict))
