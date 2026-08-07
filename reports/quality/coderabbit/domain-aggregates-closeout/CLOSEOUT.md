# domain/aggregates residual closeout (#8172–#8177)

- Branch: `grok-260807-108155`
- Fixed: **6**
- Rejected: **0**
- Total: **6**

## Dispositions

- **#8172** `fixed` — StageResult rejects completed_at for PENDING/RUNNING, rejects completed_at < started_at; duration_seconds only for valid completions (non-negative).
- **#8173** `fixed` — RecordQuarantined.record_id uses `entity_id is not None` so empty-string identifiers are preserved.
- **#8174** `fixed` — seal_with_counts rejects negative counts and requires valid_count + quarantined_count == record_count before BatchSealed.
- **#8175** `fixed` — quarantine_record positions via BatchRecord.index - start_index (bounds check), no list membership/index().
- **#8176** `fixed` — QuarantineEntry doctest supplies created_at and mark_ignored resolved_at timestamps matching API.
- **#8177** `fixed` — ResolutionInfo allowed resolution_type values derived from QuarantineStatus terminal enum values.

## Validation
- `pytest tests/unit/domain/aggregates` green (residuals + suite)
- No tech-debt budget growth
