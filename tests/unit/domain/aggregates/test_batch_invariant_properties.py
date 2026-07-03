"""Property-based invariant tests for the Batch aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.domain.aggregates.batch import Batch
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = [pytest.mark.hypothesis]

_TEXT = st.text(
    min_size=1,
    max_size=12,
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_:",
    ),
)
_SCALAR = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-10_000, max_value=10_000),
    _TEXT,
)
_BRONZE_RECORD = st.dictionaries(
    keys=_TEXT,
    values=_SCALAR,
    min_size=1,
    max_size=4,
)


def _ts(offset_seconds: int = 0) -> datetime:
    return datetime(2026, 4, 24, tzinfo=UTC) + timedelta(seconds=offset_seconds)


def _run_id() -> RunID:
    return RunID(deterministic_uuid_value("hypothesis.batch.run_id"))


class TestBatchInvariantProperties:
    """Invariant-focused properties for Batch lifecycle and record partitioning."""

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        start_index=st.integers(min_value=0, max_value=10_000),
        payloads=st.lists(_BRONZE_RECORD, min_size=0, max_size=8),
    )
    def test_record_indices_follow_start_index_law(
        self,
        start_index: int,
        payloads: list[dict[str, object]],
    ) -> None:
        """Added records must occupy a contiguous index range."""
        batch = Batch.create(
            run_id=_run_id(),
            start_index=start_index,
            created_at=_ts(0),
        )

        created = batch.add_records(payloads)

        expected_indices = list(range(start_index, start_index + len(payloads)))
        assert [record.index for record in created] == expected_indices
        assert [record.index for record in batch.all_records] == expected_indices
        assert batch.record_count == len(payloads)
        assert batch.valid_count == len(payloads)
        assert batch.quarantined_count == 0
        assert batch.next_index == start_index + len(payloads)

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        payloads=st.lists(_BRONZE_RECORD, min_size=1, max_size=6),
        quarantined_positions=st.data(),
    )
    def test_quarantine_partition_law(
        self,
        payloads: list[dict[str, object]],
        quarantined_positions: st.DataObject,
    ) -> None:
        """Quarantining records must preserve total count and partition counts."""
        batch = Batch.create(run_id=_run_id(), created_at=_ts(0))
        batch.add_records(payloads)

        positions = sorted(
            quarantined_positions.draw(
                st.sets(
                    st.integers(min_value=0, max_value=len(payloads) - 1),
                    max_size=len(payloads),
                )
            )
        )

        for offset, position in enumerate(positions, start=1):
            batch.quarantine_record(
                batch.all_records[position],
                error=f"validation-{offset}",
                error_code="SCHEMA_VIOLATION",
                quarantined_at=_ts(offset),
            )

        expected_quarantined_indices = {
            batch.all_records[position].index for position in positions
        }

        assert batch.record_count == len(payloads)
        assert batch.quarantined_count == len(positions)
        assert batch.valid_count == len(payloads) - len(positions)
        assert {record.index for record in batch.quarantined_records} == (
            expected_quarantined_indices
        )
        assert batch.valid_count + batch.quarantined_count == batch.record_count

    def test_regression_sealed_batch_rejects_further_mutation(self) -> None:
        """Sealed batches must reject both append and quarantine mutations."""
        batch = Batch.create(run_id=_run_id(), created_at=_ts(0))
        original = batch.add_record({"id": "1"})
        batch.seal(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot add_record"):
            batch.add_record({"id": "2"})

        with pytest.raises(InvalidStateError, match="Cannot quarantine_record"):
            batch.quarantine_record(
                original,
                error="schema violation",
                error_code="SCHEMA_VIOLATION",
                quarantined_at=_ts(11),
            )
