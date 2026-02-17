# Contracts Reference

This directory is the contract registry for BioETL Gold schemas and contract-adjacent specifications.

## Source of Truth (export-only)

- **Source of Truth for schema definition**: `src/bioetl/domain/contracts/gold/` (Pandera `DataFrameModel` classes).
- `docs/04-reference/contracts/gold/*.json` are **export artifacts only** (consumer-facing snapshots), not hand-maintained source files.
- Any contract change MUST be introduced in code first (domain contract classes), then exported to JSON.
- Manual edits in exported JSON are prohibited because they break reproducibility and code-doc parity.

Implementation references:

- Content hash and normalization orchestration entrypoint: `src/bioetl/domain/services/identity_service.py`.
- Canonical hash algorithm implementation: `src/bioetl/domain/transformations.py`.

## Contract SemVer policy

Contract files use SemVer in filename and inside `$version`.

- File pattern: `<entity>_vMAJOR.MINOR.json` (e.g., `chembl_activity_v1.0.json`).
- JSON field `$version` must use full SemVer (`MAJOR.MINOR.PATCH`, e.g., `1.0.0`).
- Policy:
  - **MAJOR** (`1.x` -> `2.0`): incompatible change for consumers.
  - **MINOR** (`1.0` -> `1.1`): backward-compatible contract extension.
  - **PATCH** (`1.0.0` -> `1.0.1`): wording/metadata fix without schema compatibility impact.

Recommended bump workflow:

1. Update schema model in `src/bioetl/domain/contracts/gold/`.
1. Export JSON contract.
1. Update filename and `$version` consistently.
1. Publish migration notice (for MAJOR), including cutover timeline.

## Breaking vs non-breaking criteria

### Breaking (requires MAJOR)

- Removing an existing field.
- Renaming a field without compatibility alias period.
- Making an optional field required.
- Narrowing type domain (e.g., `number` -> `integer`, or `nullable` -> `non-nullable`).
- Changing semantics of an existing field such that old values are reinterpreted.

### Non-breaking (can be MINOR or PATCH)

- Adding a new optional field.
- Expanding accepted type/enum values in backward-compatible way.
- Adding descriptive metadata (`description`, examples, docs links).
- Correcting typos or comments with no machine-readable schema effect (PATCH).

## CI freshness check

Contract freshness in CI is enforced through architecture tests on exported JSON contracts.

Current baseline checks:

- `tests/architecture/test_gold_schema_contracts.py` verifies:
  - required contracts exist;
  - each file is valid JSON;
  - required schema fields are present;
  - versioning conventions are respected.

Recommended freshness gate for PRs that change Gold schemas:

```bash
pytest tests/architecture/test_gold_schema_contracts.py -q
```

If a schema model changes but exported JSON is not updated, CI SHOULD fail through contract test mismatches (missing/incorrect artifacts/version metadata).

## Hash Stability Guarantees

Hashing behavior is standardized and deterministic for equivalent business records.
Canonical implementation lives in:

- `src/bioetl/domain/services/identity_service.py`
- `src/bioetl/domain/transformations.py`

### Inputs

`content_hash = sha256(provider + canonical_json(normalized_record))`

Inputs:

- `provider` (string prefix participating in hash domain separation).
- `record` business payload (dict-like structure).
- `exclude_none` flag (controls whether `None` values are retained or removed before hash).

### Canonicalization

Before hashing, values are normalized recursively:

- `float`: `NaN`/`Inf` -> `null`; finite values rounded to 10 decimals.
- `datetime` -> date ISO (`YYYY-MM-DD`).
- `date` -> ISO date string.
- `str` -> trimmed (`strip()`).
- `dict`/`list` -> recursive normalization of nested values.

Then canonical JSON serialization is applied via `serialize_to_json_canonical(...)`.

### Exclusions

Meta fields are excluded from hash calculation (via `META_FIELDS`), including run/ingestion technical lineage fields (e.g., `_ingestion_ts`, `_run_id`, `_run_type`, and `_dq_*` family).

### None policy

- Default mode: `exclude_none=False` -> explicit `null` participates in hash.
- Optional mode: `exclude_none=True` -> fields with `None` are dropped before hash.

All producers/consumers for a specific entity MUST use the same `exclude_none` mode, otherwise semantically equal records may hash differently.

### Sort order

Deterministic ordering is guaranteed by canonical JSON serialization (`canonical_json_dumps` delegates to `serialize_to_json_canonical`).
Field order in source dict MUST NOT affect the resulting hash.

## Migration notice templates for MAJOR contract changes

Use these templates in release notes / PR description when introducing MAJOR updates.

### Example 1 — field rename with compatibility window

```text
[MAJOR CONTRACT NOTICE] chembl_activity: v1.0 -> v2.0

What changed:
- Field renamed: `standard_value` -> `activity_value`
- Legacy field `standard_value` removed from v2.0 contract

Why:
- Unified naming across ChEMBL/PubChem/UniProt activity-like entities

Impact:
- Downstream consumers parsing `standard_value` must migrate to `activity_value`
- Backfill scripts and BI dashboards require update

Timeline:
- v1.0: supported until 2026-06-30
- v2.0: default starting 2026-04-01
- Dual-publish window: 2026-04-01 .. 2026-06-30

Action required:
1) Update parsers/selectors
2) Re-run validation against `chembl_activity_v2.0.json`
3) Sign off in consumer migration checklist
```

### Example 2 — optional -> required tightening

```text
[MAJOR CONTRACT NOTICE] uniprot_protein: v1.1 -> v2.0

What changed:
- `sequence` changed from nullable optional to required non-null field

Why:
- Gold quality policy now requires complete sequence payload for protein analytics

Impact:
- Rows without sequence will fail strict validation in Gold
- Existing ingestion shortcuts that emit null sequence are no longer valid

Timeline:
- Announcement date: 2026-02-15
- Enforcement in CI: 2026-03-01
- Production cutover: 2026-03-15

Action required:
1) Ensure extractor populates `sequence`
2) Add pre-Gold DQ guard for missing sequence
3) Validate against `uniprot_protein_v2.0.json`
```
