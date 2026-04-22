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
- canonical execution identity used by manifest and checkpoint persistence
- degraded runtime-anchor compatibility helpers used only for legacy resume paths
- record-level normalization and `content_hash`
- shipped normalization profiles and generated field-matrix artifacts
- composite join-key normalization policies and adapters

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

## 2026-04-21 Data Normalization Audit Closure

Issues `#3011`-`#3025` turn the normalization audit into explicit code
guardrails. The active implementation policy is:

- `RecordNormalizationProcessor.compute_content_hash()` always hashes with
  `exclude_none=True` and passes profile `set_like_fields` to the domain hash
  identity seam.
- DOI, PMID, and PMC identifiers are normalized through domain identifier
  helpers from every shipped publication profile.
- ChEMBL strict enum fields are centralized in `configs/enums/chembl.yaml`,
  mirrored by `domain/schemas/constants.py`, applied by normalization profiles,
  and guarded by Pandera `isin`/pattern checks where schemas expose the field.
- Shared profile rule families cover boolean-like values, binary flags,
  comparison operators, units, pseudo-null collapse, canonical JSON strings,
  and set-like JSON/list hash behavior.
- ChEMBL ontology identifiers are normalized in profiles for BAO, BTO, CALOHA,
  CLO, EFO, UBERON, UO, and related prefixed IDs instead of transformer-local
  one-offs.
- Composite join keys must have an explicit policy in
  `JOIN_KEY_NORMALIZATION_POLICIES`; configuration coverage is enforced by unit
  tests over `configs/composites/*.yaml`.

## Canonical Hash and Serialization Rules

### Canonical JSON

Canonical serialization is the shared lexical contract before hashing.

- sort keys lexically
- use compact separators `(",", ":")`
- do not allow unordered mapping traversal to affect bytes on disk

Current main seams:

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

Execution-identity and degraded runtime-anchor fields such as
`effective_config_hash` are also hash-like and must compare in lowercase form;
validation strictness is part of `P2`.

### UUID

UUID-like values normalize through canonical string conversion.

- lowercase text
- standard hyphenated string form
- blank optional UUIDs collapse to `None`

## Current Main Seams

| Concern | Current seam | Current behavior on `main` |
| --- | --- | --- |
| Control-plane domain normalization | [control_plane.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/control_plane.py) | Pure helpers for manifest specs, ledger payloads, UUIDs, datetimes, set-like collections, canonical execution identity, and degraded runtime anchors |
| Hash-identity domain normalization | [hash_identity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/hash_identity.py) | Pure helpers for `content_hash` and content-aware dedup identity, including the current date-only datetime contract |
| Manifest fingerprint | [run_manifest_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/control_plane/run_manifest_service.py) | Calls `normalize_run_manifest_spec()`, then canonical JSON, then SHA-256 |
| Ledger persist payload | [run_ledger_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/control_plane/run_ledger_service.py) | Calls `normalize_run_ledger_payload()` before append |
| Record-level normalization | [record_normalization_processor.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/record_normalization_processor.py) | Uses `NormalizationProfile` when available, otherwise falls back to legacy heuristics |
| Profile framework | [base.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/base.py) | Defines `FieldRule` and `NormalizationProfile` with `include_in_hash` and `set_like` |
| Shipped profile registry | [registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/registry.py) | Registers shipped profiles for `chembl.activity`, `chembl.assay`, `chembl.assay_parameters`, `chembl.cell_line`, `chembl.compound_record`, `chembl.molecule`, `chembl.protein_class`, `chembl.publication`, `chembl.publication_similarity`, `chembl.publication_term`, `chembl.subcellular_fraction`, `chembl.target`, `chembl.target_component`, `chembl.tissue`, `crossref.publication`, `openalex.publication`, `pubchem.compound`, `pubmed.publication`, `semanticscholar.publication`, `uniprot.idmapping`, and `uniprot.protein` |
| Join-key domain policies | [join_keys.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/join_keys.py) | Pure scalar join-key policies for canonical trim/casing behavior |
| Join-key application adapters | [join_key_normalization.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/composite/join_key_normalization.py) | Applies canonical join-key policies to composite runtime/config and DataFrame-oriented flows |
| Matrix generation | [generate_pipeline_normalization_field_matrix.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/docs/generate_pipeline_normalization_field_matrix.py) | Deterministically emits multi-pipeline CSV and MD artifacts from schemas, profiles, fallback rules, and join-key seams |
| Fallback inventory | [report_normalization_fallback_inventory.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/engineering/qa/report_normalization_fallback_inventory.py) | Reports `fallback_business` vs `fallback_technical_passthrough` debt from the published matrix for governance and ratchets |

## Hash Boundaries

### Where `execution_fingerprint` is computed

Canonical manifest path:

- [run_manifest_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/control_plane/run_manifest_service.py)

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

- `main` also has a checkpoint-resident canonical execution-identity fallback used when a full persisted manifest fingerprint is unavailable.
- `main` also retains an explicitly degraded runtime-anchor helper for legacy resume compatibility when neither full nor checkpoint-canonical identity is available.
- Those two fallback surfaces must not be conflated.

### Where `content_hash` is computed

Canonical record path:

- [hash_identity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/hash_identity.py)
- [record_normalization_processor.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/record_normalization_processor.py)
- [hashing.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/transformations/hashing.py)
- [retention.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/infrastructure/storage/support/retention.py)
- [validation_operations.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/infrastructure/storage/silver/validation_operations.py)

Current algorithm on `main`:

1. normalize record through profile or fallback rules
2. resolve include/exclude policy
3. pass `set_like_fields` from the profile when present
4. normalize hash identity through the explicit domain seam in `hash_identity.py`
5. canonicalize record for hashing through the same hash-identity contract
6. compute `sha256(provider + canonical_json(normalized_record)).hexdigest()`

Hash-identity note:

- `content_hash` and content-aware dedup now share one explicit contract.
- This contract is intentionally distinct from control-plane datetime normalization.
- `datetime` currently collapses to `date().isoformat()` inside hash identity to preserve historical `content_hash` stability until a deliberate migration is approved.
- 2026-04 evaluation outcome: keep this split in place; any convergence toward
  UTC ISO-8601 `Z` datetime semantics must be treated as a separate
  breaking-change migration with explicit versioning and validation.

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

- [generate_pipeline_normalization_field_matrix.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/docs/generate_pipeline_normalization_field_matrix.py)

Current inputs:

- silver schema registry for shipped entity pipelines
- canonical profile registry in [registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/registry.py)
- canonical fallback field families from [normalization_fallbacks.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/normalization_fallbacks.py)
- composite join-key policy seams from [join_keys.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/join_keys.py) and [join_key_normalization.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/composite/join_key_normalization.py)

Current deterministic outputs:

- CSV: required
- MD: shipped
- DOCX/PDF: optional best-effort exports

The generated artifact family is multi-pipeline and must not regress to a
ChemBL-only source of truth.

## Generated Evidence Governance

Normalization evidence is a governed artifact bundle, not a loose collection of
docs.

Current evidence bundle on `main`:

- canonical plan: [normalization_plan_P0_P6.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/05-engineering/normalization_plan_P0_P6.md)
- shipped multi-pipeline matrix: [pipeline_normalization_field_matrix.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md)
- fallback inventory report: [report_normalization_fallback_inventory.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/engineering/qa/report_normalization_fallback_inventory.py)
- join-key policy seams: [join_keys.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/join_keys.py) and [join_key_normalization.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/composite/join_key_normalization.py)

Governance rules:

- the canonical plan must describe the currently shipped profile registry
- the published matrix must be reproducible from code
- fallback inventory must classify business debt separately from technical passthrough
- normalization governance must publish surface-scoped KPIs instead of one blended headline:
  `explicit_profile_coverage_pct` for entity-record coverage,
  `composite_join_key_policy_coverage_pct` for composite join-key coverage, and
  `control_plane_normalization_coverage_pct` for control-plane / reproducibility coverage
- checkpoint governance consumers must import anchor helpers through the
  sanctioned package facade `bioetl.application.composite.checkpoint`;
  `bioetl.application.composite.checkpoint.anchor_context` remains a
  compatibility-only shim and is not a sanctioned new first-party import style
- join-key policies must remain part of the same normalization evidence story as entity profiles
- drift between plan, registry, matrix, and fallback inventory is a governance defect

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

- [run_manifest_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/control_plane/run_manifest_service.py) already normalizes payloads before hashing

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

- [run_ledger_service.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/services/control_plane/run_ledger_service.py) already calls `normalize_run_ledger_payload()`

### Requirements

- normalize before append
- `details` remain canonical
- `_diagnostic` envelope remains deterministic

### Acceptance

- equivalent events serialize identically
- key-order permutations do not change the stored JSON form

## P2 - Normalize `contract_ref`, Canonical Checkpoint Identity, and Degraded Anchors

### Goal

Stabilize checkpoint-resident execution identity and degraded runtime-anchor
helpers used for resume / compatibility checks.

### Current state on `main`

- `contract_ref` lowercases
- `contract_version` canonicalizes to semver-like `X.Y.Z`
- `effective_config_hash` lowercases
- canonical checkpoint execution identity reuses the same normalized payload
  family as manifest execution identity
- degraded runtime anchors remain narrower and must stay explicitly named

### Required target behavior

- `contract_ref` -> lowercase
- `contract_version` -> canonical semver string
- `effective_config_hash` -> lowercase
- invalid lexical forms fail validation early

### Acceptance

- checkpoint execution identity compares stably across runs
- degraded runtime anchors remain explicitly scoped to legacy fallback
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
- standard profile families must distinguish:
  - pure textual normalization
  - explicitly declared JSON-bearing string normalization
  - meta-field passthrough outside `content_hash`

### Acceptance

- profile contracts fully describe normalization semantics for a covered schema

## P3 - Shipped Profile Registry

### Goal

Use explicit profiles as canonical contracts for covered pipeline schemas.

### Current state on `main`

- [registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/registry.py) already ships a canonical registry derived from one declarative shipped-profile table
- shipped profiles currently include:
  - `chembl.activity`
  - `chembl.assay`
  - `chembl.assay_parameters`
  - `chembl.cell_line`
  - `chembl.compound_record`
  - `chembl.molecule`
  - `chembl.protein_class`
  - `chembl.publication`
  - `chembl.publication_similarity`
  - `chembl.publication_term`
  - `chembl.subcellular_fraction`
  - `chembl.target`
  - `chembl.target_component`
  - `chembl.tissue`
  - `crossref.publication`
  - `openalex.publication`
  - `pubchem.compound`
  - `pubmed.publication`
  - `semanticscholar.publication`
  - `uniprot.idmapping`
  - `uniprot.protein`

### Requirements

- each covered schema field is described explicitly
- each profile field declares normalization behavior and hash participation
- profile lookup coordinates are canonicalized by provider/entity pair
- registry/module-path views must be derived from one canonical declaration rather than duplicated maps

### Acceptance

- shipped profiles resolve only through the canonical registry
- runtime registry and module-path registry cannot drift independently
- each shipped profile covers its target schema exactly
- covered fields do not depend on undocumented fallback heuristics

## P4 - Profile-Driven RecordNormalizationProcessor

### Goal

Make record-level normalization profile-aware while keeping compatibility
fallback explicit and bounded.

### Current state on `main`

- [record_normalization_processor.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/core/record_normalization_processor.py) prefers a `NormalizationProfile`
- shipped profile-backed pipelines must fail loudly on unprofiled business fields by default
- compatibility fallback remains available only through explicit opt-in for bounded non-shipped or transitional paths

### Requirements

- if a shipped profile exists, use it and reject implicit fallback for uncovered business fields
- compatibility fallback must be enabled explicitly when transitional behavior is still required
- if no profile exists, keep fallback behavior
- hash semantics must be explainable by the active profile or explicit fallback policy

### Acceptance

- profile-driven shipped paths are active and fail on uncovered business fields
- fallback remains backward-compatible for uncovered entities and explicit compatibility mode only

## P4 - Composite Join-Key Normalization

### Goal

Keep composite join-key normalization deterministic without violating domain
purity or import boundaries.

### Current state on `main`

- [join_keys.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/join_keys.py) already ships pure scalar normalization policies
- [join_key_normalization.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/application/composite/join_key_normalization.py) already applies those policies in application/composite flows

### Requirements

- pure scalar join-key policies stay in the domain layer
- DataFrame/runtime/config traversal stays in application/composite
- canonical trim/casing semantics for join-key text remain shared across composite runtime paths
- publication join-key identifiers must distinguish row-level canonical form from join-level canonical form:
  - row-level `pmid` stays digits-only
  - row-level `pmc_id` stays uppercase `PMC...`
  - join-level `pmid` must validate against the PMID contract before comparison
  - join-level `pmc_id` must validate against the PMC contract before lowercase comparison
  - wrong-family values must collapse before they participate in composite joins

### Acceptance

- domain join-key helpers remain dependency-free
- application adapters reuse the canonical domain policies rather than redefining them locally
- join-key behavior is documented as part of the normalization architecture
- composite publication joins cannot silently accept `pmc_id` payloads in `pmid` keys

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

Remove spreadsheet-like drift by generating the matrix from schemas, shipped
profiles, fallback seams, and composite join-key policies.

### Current state on `main`

- [generate_pipeline_normalization_field_matrix.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/docs/generate_pipeline_normalization_field_matrix.py) already generates deterministic multi-pipeline artifacts

### Requirements

- CSV is mandatory
- MD is first-class published artifact
- DOCX/PDF remain optional
- output order is deterministic
- the artifact reflects shipped profile coverage, fallback coverage, and join-key normalization seams
- the published matrix should surface the normalized coverage split across
  entity-record, composite join-key, and control-plane / reproducibility seams
  so maintainers can track each normalization surface without overstating repo-wide closure

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
python3 -m scripts.docs generate-pipeline-normalization-matrix --check
```

## Related Documents

- [RULES.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/00-project/RULES.md)
- [Content Hash Identity Policy](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/02-architecture/policies/content-hash-identity-policy.md)
- [ADR-014 Deterministic Writes](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-044 Run Manifest and Run Ledger](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest Inspection](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/05-operations/runbooks/run-manifest-inspection.md)
