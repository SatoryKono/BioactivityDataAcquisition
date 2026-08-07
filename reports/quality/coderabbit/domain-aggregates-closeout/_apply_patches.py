from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[4]
print("root", root)

# --- #8172 ---
p = root / "src/bioetl/domain/aggregates/pipeline_run_stage_result.py"
text = p.read_text(encoding="utf-8")
old = '''def _validate_stage_completion(
    status: StageStatus, error: str | None, completed_at: datetime | None
) -> None:
    """Validate stage completion invariants."""
    if status == StageStatus.FAILED and not error:
        raise ValueError("Failed stage must have an error message")
    needs_timestamp = status in {StageStatus.SUCCESS, StageStatus.FAILED}
    if needs_timestamp and not completed_at:
        raise ValueError(
            f"Completed/Failed stage must have completed_at timestamp, "
            f"got status={status.value}"
        )


def _validate_stage_result(
    stage: str,
    status: StageStatus,
    error: str | None,
    completed_at: datetime | None,
    records_processed: int,
) -> None:
    """Validate stage result invariants (extracted for lower CC)."""
    _validate_stage_name(stage)
    _validate_stage_completion(status, error, completed_at)
    if records_processed < 0:
        raise ValueError(f"records_processed cannot be negative: {records_processed}")
'''
new = '''def _validate_stage_completion(
    status: StageStatus,
    error: str | None,
    completed_at: datetime | None,
    started_at: datetime,
) -> None:
    """Validate stage completion invariants."""
    if status == StageStatus.FAILED and not error:
        raise ValueError("Failed stage must have an error message")
    if status in {StageStatus.PENDING, StageStatus.RUNNING} and completed_at is not None:
        raise ValueError(
            f"In-progress stage must not have completed_at timestamp, "
            f"got status={status.value}"
        )
    needs_timestamp = status in {StageStatus.SUCCESS, StageStatus.FAILED}
    if needs_timestamp and not completed_at:
        raise ValueError(
            f"Completed/Failed stage must have completed_at timestamp, "
            f"got status={status.value}"
        )
    if completed_at is not None and completed_at < started_at:
        raise ValueError(
            "completed_at cannot be earlier than started_at: "
            f"started_at={started_at!s}, completed_at={completed_at!s}"
        )


def _validate_stage_result(
    stage: str,
    status: StageStatus,
    error: str | None,
    completed_at: datetime | None,
    records_processed: int,
    started_at: datetime,
) -> None:
    """Validate stage result invariants (extracted for lower CC)."""
    _validate_stage_name(stage)
    _validate_stage_completion(status, error, completed_at, started_at)
    if records_processed < 0:
        raise ValueError(f"records_processed cannot be negative: {records_processed}")
'''
if old not in text:
    raise SystemExit("stage validation block not found")
text = text.replace(old, new)
old2 = '''        _validate_stage_result(
            self.stage,
            self.status,
            self.error,
            self.completed_at,
            self.records_processed,
        )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate stage duration in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
'''
new2 = '''        _validate_stage_result(
            self.stage,
            self.status,
            self.error,
            self.completed_at,
            self.records_processed,
            self.started_at,
        )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate stage duration in seconds for valid completions only."""
        if self.completed_at is None:
            return None
        if self.status in {StageStatus.PENDING, StageStatus.RUNNING}:
            return None
        duration = (self.completed_at - self.started_at).total_seconds()
        if duration < 0:
            return None
        return duration
'''
if old2 not in text:
    raise SystemExit("stage post_init/duration not found")
text = text.replace(old2, new2)
p.write_text(text, encoding="utf-8")
print("patched #8172")

# --- #8173 ---
p = root / "src/bioetl/domain/aggregates/_batch_lifecycle.py"
text = p.read_text(encoding="utf-8")
old = "            record_id=str(entity_id) if entity_id else None,"
new = "            record_id=str(entity_id) if entity_id is not None else None,"
if old not in text:
    raise SystemExit("entity_id truthiness not found")
p.write_text(text.replace(old, new), encoding="utf-8")
print("patched #8173")

# --- #8174 #8175 ---
p = root / "src/bioetl/domain/aggregates/_batch_mixins.py"
text = p.read_text(encoding="utf-8")
old = '''        self._assert_open("quarantine_record")
        if record not in self._records:
            raise ValueError("Record does not belong to this batch")

        quarantined = record.with_validation_error(error, error_code)
        index = self._records.index(record)
        self._records[index] = quarantined
        self._quarantined.append(quarantined)
'''
new = '''        self._assert_open("quarantine_record")
        position = record.index - self._start_index
        if position < 0 or position >= len(self._records):
            raise ValueError("Record does not belong to this batch")

        quarantined = record.with_validation_error(error, error_code)
        self._records[position] = quarantined
        self._quarantined.append(quarantined)
'''
if old not in text:
    raise SystemExit("quarantine_record block not found")
text = text.replace(old, new)

old = '''        """Seal the batch using runtime-computed transform result counts.

        Batch processing can filter or quarantine records outside the aggregate
        record collection. The transition still belongs to the aggregate; the
        runtime supplies the counts observed at the transform boundary.
        """
        self._status, self._sealed_at = lifecycle.seal(
'''
new = '''        """Seal the batch using runtime-computed transform result counts.

        Batch processing can filter or quarantine records outside the aggregate
        record collection. The transition still belongs to the aggregate; the
        runtime supplies the counts observed at the transform boundary.

        Counts must be non-negative and satisfy
        ``valid_count + quarantined_count == record_count``.
        """
        if record_count < 0 or valid_count < 0 or quarantined_count < 0:
            raise ValueError(
                "seal counts must be non-negative: "
                f"record_count={record_count}, valid_count={valid_count}, "
                f"quarantined_count={quarantined_count}"
            )
        if valid_count + quarantined_count != record_count:
            raise ValueError(
                "seal counts are inconsistent: "
                f"valid_count ({valid_count}) + quarantined_count "
                f"({quarantined_count}) != record_count ({record_count})"
            )
        self._status, self._sealed_at = lifecycle.seal(
'''
if old not in text:
    raise SystemExit("seal_with_counts block not found")
text = text.replace(old, new)
p.write_text(text, encoding="utf-8")
print("patched #8174 #8175")

# --- #8176 ---
p = root / "src/bioetl/domain/aggregates/_quarantine_aggregate.py"
text = p.read_text(encoding="utf-8")
old = '''    Example:
        >>> entry = QuarantineEntry.create(
        ...     pipeline_name="chembl_activity",
        ...     error_code="SCHEMA_VIOLATION",
        ...     payload={"id": "bad-record"},
        ...     run_id=run_id,
        ...     batch_id=batch_id,
        ... )
        >>> entry.start_review()
        >>> entry.mark_ignored(reason="Known bad data source")
        >>> events = entry.collect_events()
'''
new = '''    Example:
        >>> from datetime import datetime, timezone
        >>> created_at = datetime(202
