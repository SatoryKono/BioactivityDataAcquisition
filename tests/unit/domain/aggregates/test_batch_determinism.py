"""Determinism-focused tests for Batch aggregate behavior."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.aggregates.batch import Batch
from bioetl.domain.types import RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(offset_seconds: int = 0) -> datetime:
    """Return deterministic UTC timestamps for batch determinism tests."""
    return datetime(2026, 6, 3, tzinfo=UTC) + timedelta(seconds=offset_seconds)


@pytest.fixture
def run_id() -> RunID:
    """Return a stable typed run identifier for replay tests."""
    return RunID(deterministic_uuid_value("unit.batch.determinism.run_id"))


@pytest.fixture
def stable_payload_factory() -> Callable[[], list[dict[str, object]]]:
    """Return fresh deterministic payloads for repeatable batch scenarios."""

    def _build() -> list[dict[str, object]]:
        return [
            {"id": "mol-1", "smiles": "CCO", "activity": 0.5},
            {"id": "mol-2", "smiles": "CCN", "activity": 0.7},
            {"id": "mol-3", "smiles": "CCC", "activity": 0.9},
        ]

    return _build


class TestBatchDeterminism:
    """Regression tests for replay-stable Batch behavior."""

    def test_batch_id_is_stable_for_equivalent_metadata_key_orders(
        self,
        run_id: RunID,
    ) -> None:
        """Equivalent metadata mappings must produce the same deterministic batch id."""
        metadata_a = {"source": "chembl", "page": 1, "entity": "activity"}
        metadata_b = {"entity": "activity", "page": 1, "source": "chembl"}

        batch_a = Batch.create(run_id=run_id, created_at=_ts(0), metadata=metadata_a)
        batch_b = Batch.create(run_id=run_id, created_at=_ts(0), metadata=metadata_b)

        assert batch_a.batch_id == batch_b.batch_id

    def test_batch_create_replay_is_stable_for_identical_inputs(
        self,
        run_id: RunID,
    ) -> None:
        """Replaying the same create inputs should keep batch identity stable."""
        created_ids = [
            Batch.create(
                run_id=run_id,
                start_index=25,
                created_at=_ts(5),
                metadata={"provider": "pubchem", "mode": "replay"},
            ).batch_id
            for _ in range(3)
        ]

        assert created_ids == [created_ids[0], created_ids[0], created_ids[0]]

    def test_index_sequence_is_replay_stable_from_start_index(
        self,
        run_id: RunID,
        stable_payload_factory: Callable[[], list[dict[str, object]]],
    ) -> None:
        """Repeated runs with the same payloads must yield the same record indices."""
        observed_sequences: list[list[int]] = []

        for _ in range(2):
            batch = Batch.create(run_id=run_id, start_index=100, created_at=_ts(0))
            batch.add_records(deepcopy(stable_payload_factory()))
            observed_sequences.append([record.index for record in batch.all_records])

        assert observed_sequences == [[100, 101, 102], [100, 101, 102]]

    def test_valid_and_quarantined_views_preserve_deterministic_order_under_replay(
        self,
        run_id: RunID,
        stable_payload_factory: Callable[[], list[dict[str, object]]],
    ) -> None:
        """Valid/quarantined projections should keep the same ordering across replays."""
        replay_snapshots: list[tuple[list[str], list[str]]] = []

        for _ in range(2):
            batch = Batch.create(run_id=run_id, created_at=_ts(0))
            created = batch.add_records(deepcopy(stable_payload_factory()))
            batch.quarantine_record(
                created[1],
                error="schema violation",
                error_code="SCHEMA_VIOLATION",
                quarantined_at=_ts(10),
            )
            replay_snapshots.append(
                (
                    [str(record.data["id"]) for record in batch.records],
                    [str(record.data["id"]) for record in batch.quarantined_records],
                )
            )

        assert replay_snapshots == [
            (["mol-1", "mol-3"], ["mol-2"]),
            (["mol-1", "mol-3"], ["mol-2"]),
        ]
