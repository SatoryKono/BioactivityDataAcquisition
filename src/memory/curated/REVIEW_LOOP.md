# Curated Review Loop

Curated memory is intentionally slower and smaller than episodic memory. The goal
is not to capture every useful observation, but to preserve only durable,
repeatable knowledge that remains helpful across future tasks.

## Cadence

- Run `python -m memory.tooling.review_curated` at least once per review cycle.
- Use the policy cadence from `src/memory/policy/retention.yaml` as the baseline.
- Treat `due` notes as needing verification.
- Treat `stale` notes as review-or-archive candidates.

## Review checklist

For each non-`keep` record in the report:

1. Confirm the cited `source_refs` still represent the same reality.
2. Check whether the note still captures repeatable knowledge instead of one-off context.
3. Decide whether to:
   - keep the note and refresh `last_verified`,
   - improve the note body/summary,
   - merge it with another curated note,
   - archive it with `memory.tooling.archive_note`.

## Heuristics

- `duplicate:title` means the curated layer may already contain the same lesson.
- `source_refs:thin` means the note likely needs stronger provenance before staying durable.
- `summary:brief` means the note may not explain enough value to justify long-term storage.
- `verification:due` and `verification:stale` are freshness warnings, not proof that the note is wrong.

## Expected outcome

Healthy curated memory should:

- grow slowly,
- keep duplicate themes rare,
- keep `stale` notes uncommon,
- maintain clear, source-backed summaries,
- archive superseded knowledge instead of silently leaving it active.
