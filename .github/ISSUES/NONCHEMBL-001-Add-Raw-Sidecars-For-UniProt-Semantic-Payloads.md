# [normalization] Add raw sidecars for UniProt semantic payloads

**Status**: active
**Priority**: P0 (Critical)
**Labels**: `normalization`, `contracts`, `replay`, `uniprot`
**Epic**: Non-ChEMBL Normalization Governance 2026Q2
**Last audited**: 2026-05-19

> Audit basis: the non-ChEMBL normalization stack is already deterministic and
> profile-owned, but UniProt semantic structured payload handling is materially
> weaker than publication-family handling for replay/debug semantics.

## Problem

`uniprot_protein` preserves dual raw/canonical JSON only for `features_json`,
while other semantic payload fields such as `alternative_products`,
`biophysicochemical_properties`, `cofactors`, and `reactions` are currently
persisted as canonical-only evidence payloads.

That makes normalization deterministic, but it weakens forensic replay and
semantic diff explainability because future extractor/profile changes cannot be
compared against a persisted raw sidecar for these payload families.

## Evidence

- `src/bioetl/domain/normalization/structured_payload_policies.py`
- `configs/vocab/uniprot_semantic_payloads.yaml`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `src/bioetl/domain/contracts/gold/uniprot.py`
- `configs/entities/uniprot/protein.yaml`
- `reports/codex/non_chembl_normalization_audit_20260519.md` (to be published)

## Current Fact Base

- `features_json` already has `features_raw_json` + canonical representation.
- `alternative_products`, `biophysicochemical_properties`, `cofactors`, and
  `reactions` are governed in structured payload policy, but as canonical-only
  sidecars.
- These fields are persisted in Gold as plain string payloads.
- The project already uses raw+canonical dual-field strategy successfully in
  PubMed, OpenAlex, and Semantic Scholar pipelines.

## Required Outcome

- High-semantic UniProt payload families have explicit raw-sidecar persistence
  where replay/debug meaning would otherwise be lost.
- Hash policy remains deterministic and excludes raw-sidecar payloads where
  appropriate.
- Silver/Gold contracts distinguish raw JSON from canonical JSON explicitly.

## Implementation Plan

1. Define which UniProt payload families require raw-sidecar retention:
   - `alternative_products`
   - `biophysicochemical_properties`
   - `cofactors`
   - `reactions`
2. Extend
   `src/bioetl/domain/normalization/structured_payload_policies.py`
   with raw-sidecar + canonical-sidecar policy for those families.
3. Extend `uniprot_protein` normalization profile and entity config with the
   new fields and hash exclusion policy.
4. Update Gold contract and schema expectations to carry explicit
   `*_raw_json` and canonical companions.
5. Add regression tests proving replay-stable hashing and raw/canonical
   separation.
6. Reconcile generated normalization/governance artifacts so the new
   raw-sidecar posture is visible outside code.

## Suggested File Targets

- `src/bioetl/domain/normalization/structured_payload_policies.py`
- `configs/vocab/uniprot_semantic_payloads.yaml`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `configs/entities/uniprot/protein.yaml`
- `src/bioetl/domain/contracts/gold/uniprot.py`
- `tests/unit/domain/normalization/profiles/`
- `tests/integration/config/`

## Testing Expectations

- Extend `tests/unit/domain/normalization/test_structured_payload_policies.py`
  to assert raw-sidecar + canonical-sidecar posture for the four UniProt
  payload families, matching the existing `features_json` pattern.
- Extend `tests/contract/test_non_chembl_cross_layer_contract_matrix.py` so
  cross-layer parity covers the newly introduced `*_raw_json` fields and their
  canonical companions.
- Extend `tests/architecture/test_non_chembl_json_field_typing_policy.py` so
  JSON typing policy no longer reports these payloads as canonical-only
  comment projections.
- Extend `tests/unit/application/core/test_non_chembl_normalization_hash_golden.py`
  to prove raw-sidecar deltas do not perturb `content_hash` when policy says
  the raw evidence field is hash-excluded.
- Re-run relevant UniProt runtime slices:
  - `tests/unit/application/pipelines/uniprot/test_comments_extractor.py`
  - `tests/unit/application/pipelines/uniprot/test_comment_structured_facets.py`
  - `tests/e2e/test_uniprot_protein_e2e.py`
- If fixture payload richness is insufficient, update
  `tests/fixtures/bronze/uniprot/protein/sample_edge_semantic_payloads_2026-05-12.jsonl`
  and the related VCR coverage listed in
  `docs/05-operations/verification/vcr-test-tasks.md`.

## Documentation Updates

- Update `docs/03-data-model/json-field-typing-inventory.md` to move
  `alternative_products`, `biophysicochemical_properties`, `cofactors`, and
  `reactions` from canonical-only description to explicit raw+canonical
  sidecar posture.
- Update `docs/04-reference/pipelines/uniprot/01-protein-spec.md` so the
  pipeline spec documents the new sidecar fields and replay/debug semantics.
- Update `docs/04-reference/pipelines/uniprot/protein-xwalk.csv`, which
  currently marks these fields as `MISSING_DOC`.
- Regenerate or refresh any affected contract reference exports under
  `docs/04-reference/contracts/gold/uniprot_protein_v1.0.json` if the Gold
  contract surface changes.
- Refresh generated governance artifacts that surface JSON typing or
  normalization posture, especially:
  - `docs/reports/generated/pipeline_normalization_field_matrix/`
  - `docs/reports/generated/pipeline_normalization_validation_table/`

## Done When

- The selected UniProt semantic payload families have explicit raw-sidecar
  persistence.
- Raw sidecars are excluded from hash identity where required.
- Gold contracts and entity configs surface the dual-field strategy
  consistently.
- Replay/debug tests show semantic diffs remain explainable after future
  canonicalization changes.
- JSON typing docs and UniProt pipeline reference docs describe the new
  evidence posture without leaving `MISSING_DOC` drift behind.

## Risks

- Adding raw-sidecar fields is a contract-surface change.
- Content hash behavior must remain stable and documented.
- Backfill may be required for existing Silver/Gold artifacts if the new fields
  are persisted historically.

## Dependencies

- Should precede `NONCHEMBL-006`.
