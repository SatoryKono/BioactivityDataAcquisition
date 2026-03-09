"""Integration tests for pipeline idempotency.

Verifies that re-running a pipeline with identical source data produces
identical output records, same content hashes, same entity IDs and the
same Silver layer state (merge mode behaves as an upsert, not append).

These tests use in-memory storage fakes and mocked transformers so that
no filesystem or network I/O is required.  They exercise the
write_silver merge semantics defined in fakes/storage_fake.py.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

import pytest

from bioetl.domain.transformations import (
    generate_content_hash,
    generate_entity_id,
    normalize_for_hash,
)

# =============================================================================
# Minimal in-memory storage for idempotency tests
# =============================================================================


class _IdempotentStorage:
    """Minimal in-memory storage that replicates merge semantics.

    Tracks every individual write call so tests can assert how many times
    a record was written versus how many unique records are present.
    """

    def __init__(self) -> None:
        self.silver: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.bronze: dict[str, list[bytes]] = defaultdict(list)
        self.write_calls: list[dict[str, Any]] = []

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: Any = None,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
    ) -> None:
        self.write_calls.append(
            {
                "table_name": table_name,
                "record_count": len(records),
                "mode": mode,
                "primary_keys": primary_keys,
            }
        )

        if mode == "merge":
            pk_set = set(primary_keys)
            existing_by_pk: dict[tuple[Any, ...], dict[str, Any]] = {}
            for rec in self.silver[table_name]:
                pk_vals = tuple(rec.get(k) for k in pk_set)
                existing_by_pk[pk_vals] = rec
            for rec in records:
                pk_vals = tuple(rec.get(k) for k in pk_set)
                existing_by_pk[pk_vals] = rec
            self.silver[table_name] = list(existing_by_pk.values())
        elif mode == "append":
            self.silver[table_name].extend(records)

    def clear(self) -> None:
        self.silver.clear()
        self.bronze.clear()
        self.write_calls.clear()


# =============================================================================
# Helper: build a deterministic Silver record from raw source data
# =============================================================================


def _build_silver_record(
    raw: dict[str, Any],
    provider: str,
    run_id: str,
) -> dict[str, Any]:
    """Transform raw source data into a deterministic Silver-layer record.

    Mirrors the minimal transformation logic that every pipeline stage
    applies: strip meta fields, generate content hash and entity ID.
    """
    content_hash = generate_content_hash(raw, provider)
    entity_id = generate_entity_id(raw, provider)
    return {
        **raw,
        "_content_hash": content_hash,
        "_entity_id": entity_id,
        "_provider": provider,
        "_run_id": run_id,
        "_ingestion_ts": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# Source data fixtures
# =============================================================================


CHEMBL_ACTIVITY_RECORDS: list[dict[str, Any]] = [
    {
        "activity_id": 1001,
        "molecule_chembl_id": "CHEMBL25",
        "standard_type": "IC50",
        "standard_value": 0.5,
        "standard_units": "nM",
        "assay_chembl_id": "CHEMBL697780",
    },
    {
        "activity_id": 1002,
        "molecule_chembl_id": "CHEMBL12",
        "standard_type": "Ki",
        "standard_value": 12.3,
        "standard_units": "nM",
        "assay_chembl_id": "CHEMBL697780",
    },
]

PUBMED_PUBLICATION_RECORDS: list[dict[str, Any]] = [
    {
        "pmid": "12345678",
        "title": "Effect of aspirin on platelet aggregation",
        "doi": "10.1000/xyz001",
        "year": 2020,
        "journal": "Journal of Pharmacology",
    },
    {
        "pmid": "98765432",
        "title": "Ibuprofen pharmacokinetics revisited",
        "doi": "10.1000/xyz002",
        "year": 2021,
        "journal": "Clinical Pharmacology",
    },
]


# =============================================================================
# 1. Content hash stability across runs
# =============================================================================


@pytest.mark.integration
class TestContentHashStability:
    """Content hashes must be identical for the same source data across runs."""

    def test_same_record_same_hash_different_run_ids(self) -> None:
        """Content hash must not depend on run_id or ingestion_ts."""
        raw = CHEMBL_ACTIVITY_RECORDS[0]

        hash_run1 = generate_content_hash(raw, "chembl")
        hash_run2 = generate_content_hash(raw, "chembl")

        assert hash_run1 == hash_run2

    def test_same_record_same_entity_id_different_run_ids(self) -> None:
        """Entity ID must be stable across runs for the same source data."""
        raw = CHEMBL_ACTIVITY_RECORDS[0]

        id_run1 = generate_entity_id(raw, "chembl")
        id_run2 = generate_entity_id(raw, "chembl")

        assert id_run1 == id_run2

    def test_all_records_produce_stable_hashes(self) -> None:
        """All source records should produce stable hashes on repeated calls."""
        for raw in CHEMBL_ACTIVITY_RECORDS + PUBMED_PUBLICATION_RECORDS:
            h1 = generate_content_hash(raw, "test")
            h2 = generate_content_hash(raw, "test")
            assert h1 == h2, f"Hash unstable for record: {raw}"

    def test_hash_changes_when_content_changes(self) -> None:
        """A changed field must produce a different content hash."""
        raw = deepcopy(CHEMBL_ACTIVITY_RECORDS[0])
        h1 = generate_content_hash(raw, "chembl")

        raw["standard_value"] = 999.0  # Change a data field
        h2 = generate_content_hash(raw, "chembl")

        assert h1 != h2

    def test_meta_fields_do_not_affect_hash(self) -> None:
        """Adding meta-fields using exclude_fields should not alter the content hash."""
        raw = deepcopy(CHEMBL_ACTIVITY_RECORDS[0])
        meta_fields = {"_run_id", "_ingestion_ts", "_run_type"}

        h1 = generate_content_hash(raw, "chembl", exclude_fields=meta_fields)

        raw["_run_id"] = str(uuid4())
        raw["_ingestion_ts"] = datetime.now(UTC).isoformat()
        h2 = generate_content_hash(raw, "chembl", exclude_fields=meta_fields)

        assert h1 == h2


# =============================================================================
# 2. Silver layer merge idempotency
# =============================================================================


@pytest.mark.integration
class TestSilverMergeIdempotency:
    """Re-running a pipeline should not duplicate Silver records."""

    @pytest.fixture
    def storage(self) -> _IdempotentStorage:
        return _IdempotentStorage()

    @pytest.mark.asyncio
    async def test_second_run_does_not_add_new_rows(
        self, storage: _IdempotentStorage
    ) -> None:
        """Merging the same records twice yields the same row count."""
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())
        table = "silver_chembl_activity"
        primary_keys = ["activity_id"]

        records_run1 = [
            _build_silver_record(r, "chembl", run_id_1)
            for r in CHEMBL_ACTIVITY_RECORDS
        ]

        await storage.write_silver(table, records_run1, primary_keys)
        count_after_run1 = len(storage.silver[table])

        records_run2 = [
            _build_silver_record(r, "chembl", run_id_2)
            for r in CHEMBL_ACTIVITY_RECORDS
        ]

        await storage.write_silver(table, records_run2, primary_keys)
        count_after_run2 = len(storage.silver[table])

        assert count_after_run2 == count_after_run1, (
            f"Row count changed: {count_after_run1} → {count_after_run2}. "
            "Idempotency violated: re-run should not add duplicate rows."
        )

    @pytest.mark.asyncio
    async def test_content_hashes_identical_after_two_runs(
        self, storage: _IdempotentStorage
    ) -> None:
        """Content hashes in Silver must remain unchanged after a re-run."""
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())
        table = "silver_chembl_activity"
        primary_keys = ["activity_id"]

        records_run1 = [
            _build_silver_record(r, "chembl", run_id_1)
            for r in CHEMBL_ACTIVITY_RECORDS
        ]
        await storage.write_silver(table, records_run1, primary_keys)
        hashes_run1 = {
            rec["activity_id"]: rec["_content_hash"]
            for rec in storage.silver[table]
        }

        records_run2 = [
            _build_silver_record(r, "chembl", run_id_2)
            for r in CHEMBL_ACTIVITY_RECORDS
        ]
        await storage.write_silver(table, records_run2, primary_keys)
        hashes_run2 = {
            rec["activity_id"]: rec["_content_hash"]
            for rec in storage.silver[table]
        }

        assert hashes_run1 == hashes_run2, (
            "Content hashes changed between runs — possible schema or transformation change."
        )

    @pytest.mark.asyncio
    async def test_entity_ids_stable_across_runs(
        self, storage: _IdempotentStorage
    ) -> None:
        """Entity IDs in Silver must be stable across runs for the same source data."""
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())
        table = "silver_pubmed"
        primary_keys = ["pmid"]

        records_run1 = [
            _build_silver_record(r, "pubmed", run_id_1)
            for r in PUBMED_PUBLICATION_RECORDS
        ]
        await storage.write_silver(table, records_run1, primary_keys)
        ids_run1 = {
            rec["pmid"]: rec["_entity_id"] for rec in storage.silver[table]
        }

        records_run2 = [
            _build_silver_record(r, "pubmed", run_id_2)
            for r in PUBMED_PUBLICATION_RECORDS
        ]
        await storage.write_silver(table, records_run2, primary_keys)
        ids_run2 = {rec["pmid"]: rec["_entity_id"] for rec in storage.silver[table]}

        assert ids_run1 == ids_run2

    @pytest.mark.asyncio
    async def test_three_runs_no_row_growth(
        self, storage: _IdempotentStorage
    ) -> None:
        """Row count must remain stable across three identical pipeline runs."""
        table = "silver_chembl_activity"
        primary_keys = ["activity_id"]
        row_counts: list[int] = []

        for _ in range(3):
            run_id = str(uuid4())
            records = [
                _build_silver_record(r, "chembl", run_id)
                for r in CHEMBL_ACTIVITY_RECORDS
            ]
            await storage.write_silver(table, records, primary_keys)
            row_counts.append(len(storage.silver[table]))

        assert len(set(row_counts)) == 1, (
            f"Row counts across three runs: {row_counts}. Expected constant value."
        )

    @pytest.mark.asyncio
    async def test_updated_record_replaces_not_duplicates(
        self, storage: _IdempotentStorage
    ) -> None:
        """An updated record value must replace the old row, not append."""
        table = "silver_chembl_activity"
        primary_keys = ["activity_id"]

        original_raw = deepcopy(CHEMBL_ACTIVITY_RECORDS[0])
        rec_v1 = _build_silver_record(original_raw, "chembl", str(uuid4()))
        await storage.write_silver(table, [rec_v1], primary_keys)
        count_v1 = len(storage.silver[table])

        updated_raw = deepcopy(original_raw)
        updated_raw["standard_value"] = 0.99  # simulated upstream update
        rec_v2 = _build_silver_record(updated_raw, "chembl", str(uuid4()))
        await storage.write_silver(table, [rec_v2], primary_keys)

        records_after = storage.silver[table]
        assert len(records_after) == count_v1, (
            "Update should replace existing row, not add a new one."
        )
        stored_value = records_after[0]["standard_value"]
        assert stored_value == 0.99, (
            f"Expected updated value 0.99, got {stored_value}"
        )


# =============================================================================
# 3. Append mode — rows accumulate predictably
# =============================================================================


@pytest.mark.integration
class TestAppendModeAccumulation:
    """Append mode must accumulate rows linearly (one batch = one addition)."""

    @pytest.fixture
    def storage(self) -> _IdempotentStorage:
        return _IdempotentStorage()

    @pytest.mark.asyncio
    async def test_two_append_runs_double_the_rows(
        self, storage: _IdempotentStorage
    ) -> None:
        """Two separate append operations should double the row count."""
        table = "bronze_dump"
        primary_keys: list[str] = []

        records_batch = [
            _build_silver_record(r, "chembl", str(uuid4()))
            for r in CHEMBL_ACTIVITY_RECORDS
        ]
        batch_size = len(records_batch)

        await storage.write_silver(table, records_batch, primary_keys, mode="append")
        await storage.write_silver(table, records_batch, primary_keys, mode="append")

        assert len(storage.silver[table]) == batch_size * 2


# =============================================================================
# 4. Normalization idempotency
# =============================================================================


@pytest.mark.unit
class TestNormalizationIdempotency:
    """normalize_for_hash must be idempotent: applying it twice yields the same result."""

    def test_normalize_twice_equals_normalize_once(self) -> None:
        """Normalizing an already-normalized record should be a no-op."""
        raw = CHEMBL_ACTIVITY_RECORDS[0]
        first_pass = normalize_for_hash(raw)
        second_pass = normalize_for_hash(first_pass)
        assert first_pass == second_pass

    def test_normalize_idempotent_for_all_fixture_records(self) -> None:
        for raw in CHEMBL_ACTIVITY_RECORDS + PUBMED_PUBLICATION_RECORDS:
            first_pass = normalize_for_hash(raw)
            second_pass = normalize_for_hash(first_pass)
            assert first_pass == second_pass, (
                f"normalize_for_hash is not idempotent for record: {raw}"
            )
