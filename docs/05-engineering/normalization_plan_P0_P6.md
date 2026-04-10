---
Version: 1.1.0
Status: active
Class: published
Owner: Architecture / Domain
Reviewers:
- BioETL Team
Last verified: '2026-04-10'
---

# Normalization Plan P0-P6

## Purpose

This document is the canonical engineering plan for deterministic normalization
across:

- `RunManifest`
- `RunLedger`
- runtime anchors used by checkpoint / resume compatibility
- record-level normalization and `content_hash`
- `ChemBL Activity` normalization profiles and generated field-matrix artifacts

It is the source of requirements for `P0`-`P6` and the matching test program
`T1`-`T3`.

## Scope

The plan covers:

- control-plane normalization in the domain layer
- canonical serialization before hashing or persistence
- fingerprint and content-hash determinism
- field-rule and profile contracts
- generated normalization matrix artifacts from code

The plan does not cover:

- retroactive rewrite of historical manifests / ledgers
- silent backward-incompatible hash migrations
- ad hoc normalization outside sanctioned seams

## Determinism Invariants

These rules are mandatory for all phases.

1. Normalize before hashing and before persistence.
2. Canonical JSON is the only byte representation allowed before hashing.
3. Canonical JSON uses `sort_keys=True` and `separators=(",", ":")`.
4. Control-plane datetimes normalize to UTC ISO-8601 with trailing `Z`.
5. SHA-256 fingerprints and content hashes serialize as lowercase hex strings.
6. UUID values normalize to canonical string form.
7. Domain normalization code remains pure: no I/O, no pandas, no HTTP, no hidden clock access.
8. Order-sensitive lists preserve order by default.
9. Only fields explicitly marked `set_like` are permutation-invariant for hashing.
10. Technical meta fields do not participate in `content_hash`.

## Canonical Hash and Serialization Rules

### Canonical JSON

Canonical serialization is the shared lexical contract before hashing.

- sort keys lexically
- use compact separators `(",", ":")`
- do not allow unordered mapping traversal to affect bytes on disk

Current main seam:

- [json.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/json.py)
- [serialization.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/serialization.py)

### Datetime

Control-plane timestamps must normalize to UTC ISO-8601 `Z` form.

Example:

- input: `2026-04-08T12:15:30+03:00`
- canonical: `2026-04-08T09:15:30Z`

Current main seam:

- [control_plane.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/control_plane.py)

### SHA-256

Two distinct hash families exist and must not be conflated.

- `execution_fingerprint`: lowercase 64-char hex
- `content_hash`: lowercase 64-char hex

Runtime anchor fields such as `effective_config_hash` are also hash-like and
must compare in lowercase form; validation strictness is part of `P2`.

### UUID

UUID-like values normalize through canonical string conversion.

- lowercase text
- standard hyphenated string form
- blank optional UUIDs collapse to `None`

## Current Main Seams

| Concern | Current seam | Current behavior on `main` |
| --- | --- | --- |
| Control-plane domain normalization | [control_plane.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/control_plane.py) | Pure helpers for manifest specs, ledger payloads, UUIDs, datetimes, set-like collections, runtime anchors |
| Manifest fingerprint | [run_manifest_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/run_manifest_service.py) | Calls `normalize_run_manifest_spec()`, then canonical JSON, then SHA-256 |
| Ledger persist payload | [run_ledger_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/run_ledger_service.py) | Calls `normalize_run_ledger_payload()` before append |
| Record-level normalization | [record_normalization_processor.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/record_normalization_processor.py) | Uses `NormalizationProfile` when available, otherwise falls back to legacy heuristics |
| Profile framework | [base.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/base.py) | Defines `FieldRule` and `NormalizationProfile` with `include_in_hash` and `set_like` |
| ChemBL Activity profile | [chembl_activity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/chembl_activity.py) | Field-by-field profile covers the shipped schema and asserts exact coverage |
| Matrix generation | [generate_chembl_activity_field_matrix.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/docs/generate_chembl_activity_field_matrix.py) | Deterministically emits CSV and MD from schema + profile; DOCX/PDF optional |

## Hash Boundaries

### Where `execution_fingerprint` is computed

Canonical manifest path:

- [run_manifest_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/run_manifest_service.py)

Current algorithm on `main`:

1. build primitive manifest payload
2. call `normalize_run_manifest_spec(...)`
3. call `serialize_json_canonical(...)`
4. compute `hashlib.sha256(...).hexdigest()`

Current payload scope includes:

- `schema_version`
- `run_type`
- `pipeline_name`
- `provider`
- `entity`
- `launch_context`
- `runtime_config`
- `resolved_config`
- normalized `code_provenance`
- normalized `source_refs`
- normalized `planned_artifacts`

Current payload scope excludes:

- `manifest_id`
- `created_at`
- `entry_id`
- `occurred_at`
- other persist-only fields

Important note:

- `main` also has a narrower checkpoint/runtime-anchor fingerprint path outside this file.
- That path must remain explicitly narrower or be converged deliberately under `P2`.

### Where `content_hash` is computed

Canonical record path:

- [record_normalization_processor.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/record_normalization_processor.py)
- [hashing.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/transformations/hashing.py)

Current algorithm on `main`:

1. normalize record through profile or fallback rules
2. resolve include/exclude policy
3. pass `set_like_fields` from the profile when present
4. canonicalize record for hashing
5. compute `sha256(provider + canonical_json(normalized_record)).hexdigest()`

Fields that currently participate in `content_hash`:

- `profile.hash_included_fields` when a profile is active
- or version-policy `include_fields` override when configured
- otherwise the active fallback inclusion policy

Fields currently excluded from `content_hash`:

- profile fields with `include_in_hash=False`
- explicit `content_hash_exclude_fields`
- `entity_id`
- `content_hash`
- `_content_hashes_by_version`
- technical meta fields from `META_FIELDS`
- underscore-prefixed technical fields by the hash policy

## Field-Matrix Source of Truth

The field matrix must be generated from code, not from spreadsheets.

Current deterministic generator on `main`:

- [generate_chembl_activity_field_matrix.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/docs/generate_chembl_activity_field_matrix.py)

Current inputs:

- `CHEMBL_ACTIVITY_SCHEMA`
- `CHEMBL_ACTIVITY_PROFILE`

Current deterministic outputs:

- CSV: required
- MD: shipped
- DOCX/PDF: optional best-effort exports

If a future rename introduces
`scripts/docs/generate_chembl_activity_matrix_artifacts.py`, it must preserve
the same deterministic contract and must not create a second source of truth.

## P0 - Update and Publish the Plan

### Goal

Freeze vocabulary, invariants, and code seams in one canonical document.

### Required outcome

- this document is the source of requirements for `P0`-`P6`
- canonical JSON / datetime / SHA-256 / UUID rules are explicit
- current seams on `main` are linked directly to code

### Acceptance

- document exists at `docs/05-engineering/normalization_plan_P0_P6.md`
- document includes `P0`-`P6` and the invariants above
- document is linked from engineering docs, `RULES`, and policy docs

## P1 - Domain Normalization for Control Plane

### Goal

Keep `RunManifest` and `RunLedger` normalization pure and deterministic.

### Current state on `main`

- [control_plane.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/control_plane.py) already exists
- it normalizes UUIDs, datetimes, set-like collections, manifest payloads, and ledger payloads

### Requirements

- domain-only implementation
- no I/O
- no pandas
- no HTTP
- same input -> same output

### Acceptance

- control-plane functions remain pure
- UUID and datetime normalization are deterministic
- canonical list sorting for sanctioned set-like collections is stable

## P1 - Normalize Before `execution_fingerprint` in RunManifest

### Goal

`execution_fingerprint` must be computed only from normalized data.

### Current state on `main`

- [run_manifest_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/run_manifest_service.py) already normalizes payloads before hashing

### Requirements

- call `normalize_run_manifest_spec()`
- serialize only through canonical JSON
- list order must not affect the fingerprint for sanctioned set-like fields
- key order must never affect the fingerprint

### Acceptance

- semantically equivalent manifest payloads produce identical fingerprints

## P1 - Normalize RunLedger Before Persist

### Goal

Persist a deterministic ledger payload for equivalent lifecycle events.

### Current state on `main`

- [run_ledger_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/run_ledger_service.py) already calls `normalize_run_ledger_payload()`

### Requirements

- normalize before append
- `details` remain canonical
- `_diagnostic` envelope remains deterministic

### Acceptance

- equivalent events serialize identically
- key-order permutations do not change the stored JSON form

## P2 - Normalize `contract_ref` and Checkpoint Anchors

### Goal

Stabilize runtime anchors used for resume / compatibility checks.

### Current state on `main`

- `contract_ref` lowercases
- `contract_version` canonicalizes to semver-like `X.Y.Z`
- `effective_config_hash` lowercases

### Required target behavior

- `contract_ref` -> lowercase
- `contract_version` -> canonical semver string
- `effective_config_hash` -> lowercase
- invalid lexical forms fail validation early

### Acceptance

- runtime anchors compare stably across runs
- malformed anchor values are rejected instead of drifting into persisted state

## P3 - Normalization Profile Framework

### Goal

Replace heuristic drift with explicit field contracts.

### Current state on `main`

- [base.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/base.py) already defines:
  - `FieldRule`
  - `NormalizationProfile`
  - `include_in_hash`
  - `set_like`

### Requirements

- every schema field is covered explicitly
- normalization function is declared field by field
- hash participation is explicit per field

### Acceptance

- profile contracts fully describe normalization semantics for a covered schema

## P3 - ChemBL Activity Profile

### Goal

Use one explicit profile as the canonical contract for `ChemBL Activity`.

### Current state on `main`

- [chembl_activity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/chembl_activity.py) already ships a complete profile and asserts exact schema coverage

### Requirements

- all schema fields covered
- each field has normalization behavior and hash participation policy

### Acceptance

- profile covers all shipped schema fields exactly
- no ChemBL Activity field depends on undocumented normalization heuristics

## P4 - Profile-Driven RecordNormalizationProcessor

### Goal

Make record-level normalization profile-aware while keeping backward compatibility.

### Current state on `main`

- [record_normalization_processor.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/record_normalization_processor.py) already prefers a `NormalizationProfile` and falls back to legacy heuristics when no profile exists

### Requirements

- if a profile exists, use it
- otherwise keep fallback behavior
- hash semantics must be explainable by the active profile or explicit fallback policy

### Acceptance

- profile-driven paths are active
- fallback remains backward-compatible for uncovered entities

## P4 - Stabilize Set-Like Lists

### Goal

Avoid hash drift from order-only changes in semantically unordered collections.

### Current state on `main`

- set-like fields are already carried from the active profile into `generate_content_hash(...)`

### Requirements

- only explicitly marked `set_like` fields get order-insensitive hashing
- ordering changes for non-`set_like` fields still affect the hash

### Acceptance

- permutations of set-like values do not change the hash
- order-sensitive lists still behave as order-sensitive

## P5 - Generate Field-Matrix Artifacts from Code

### Goal

Remove spreadsheet-like drift by generating the matrix from schema + profile.

### Current state on `main`

- [generate_chembl_activity_field_matrix.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/docs/generate_chembl_activity_field_matrix.py) already generates deterministic artifacts

### Requirements

- CSV is mandatory
- MD is first-class published artifact
- DOCX/PDF remain optional
- output order is deterministic

### Acceptance

- two runs on unchanged code produce byte-identical CSV
- matrix content is derived from code, not edited manually

## P6 - Tests and Governance

### Goal

Enforce determinism through tests and reviewable policy changes.

### Required test families

- `T1`: `execution_fingerprint` determinism
- `T2`: `content_hash` determinism
- `T3`: generated artifact reproducibility

### Required governance rules

- domain normalization remains dependency-free
- hash/fingerprint changes require explicit reviewable updates
- docs remain linked to the canonical plan

### Acceptance

- CI-visible tests guard the determinism contract
- policy changes are explicit rather than accidental

## T1 - Fingerprint Tests

### Goal

Prove `RunManifest` fingerprint determinism.

### Required coverage

- golden tests
- permutation tests for sanctioned set-like collections
- key-order invariance checks

### Acceptance

- `execution_fingerprint` remains stable for equivalent manifest inputs

## T2 - Content Hash Tests

### Goal

Prove business-hash stability for equivalent normalized data.

### Required coverage

- canonical JSON shape
- DOI / PMID normalization
- set-like list permutation invariance
- profile include/exclude behavior

### Acceptance

- equivalent normalized records produce identical `content_hash`

## T3 - Artifact Reproducibility Tests

### Goal

Prove generated documentation is reproducible.

### Required coverage

- run generator twice
- compare CSV byte-for-byte
- optional artifact generation must not affect CSV determinism

### Acceptance

- generated CSV is byte-identical across repeated runs on unchanged code

## Recommended Validation Commands

```bash
rg -n '^## P[0-6]\b|^## T[1-3]\b' docs/05-engineering/normalization_plan_P0_P6.md
python3 -m scripts.docs verify --skip-build
python3 scripts/docs/generate_chembl_activity_field_matrix.py --check
```

## Related Documents

- [RULES.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/00-project/RULES.md)
- [Content Hash Identity Policy](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/02-architecture/policies/content-hash-identity-policy.md)
- [ADR-014 Deterministic Writes](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-044 Run Manifest and Run Ledger](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest Inspection](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/05-operations/runbooks/run-manifest-inspection.md)
