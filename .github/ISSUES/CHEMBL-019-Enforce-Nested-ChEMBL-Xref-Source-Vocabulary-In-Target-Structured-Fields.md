# [dq] Enforce nested ChEMBL xref source vocabulary in target structured fields

**Status**: Draft
**Priority**: P1 (High)
**Labels**: `provider:chembl`, `governance`, `data-quality`, `config`, `composite`, `technical-debt`
**Epic**: ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

The nested `xref_src_db` member vocabulary inside target structured JSON fields
is already externalized and covered by offline observed-value governance, but it
is not enforced at the same runtime/DQ level as top-level controlled
vocabularies.

That leaves a selective governance gap:

- the allowed namespace registry exists;
- bronze observed values are checked against that registry offline;
- shipped target/target_component configs do not declare nested member
  validators for `xref_src_db` values inside canonical JSON strings.

This means structured target cross-reference payloads are deterministic in
serialization, but not yet fail-closed or explicitly policy-reviewed at runtime
for nested source namespaces.

## Evidence

- `reports/quality/chembl_normalization_audit_2026-05-19.md`
- `configs/vocab/chembl_reference_sources.yaml`
- `configs/entities/chembl/target.yaml`
- `configs/entities/chembl/target_component.yaml`
- `src/bioetl/domain/schemas/chembl/target.py`
- `src/bioetl/domain/schemas/chembl/target_component.py`
- `tests/integration/config/test_chembl_observed_value_fixtures.py`

## Current Fact Base

- Registry config already externalizes nested `xref_src_db` vocabulary for
  `chembl_target.cross_references[].xref_src_db` and
  `chembl_target_component.target_component_xrefs[].xref_src_db`.
- Offline governance tests already validate observed values against that
  registry.
- Existing target DQ config explicitly validates `component_types` and
  `component_relationships`, but not nested `xref_src_db` members.
- Current gap is semantic enforcement, not JSON determinism or contract-shape
  correctness.

## Required Outcome

- Nested `xref_src_db` source namespaces become first-class governed structured
  vocabulary surfaces.
- Runtime/DQ behavior matches the existing registry-backed offline governance
  posture.
- The final posture is explicit for legacy unknown namespaces:
  validation-only, preserve-unknown, quarantine, or fail-closed rejection.

## Implementation Plan

1. Reuse the existing registry as SSOT for nested `xref_src_db` members.
2. Add structured-field validator support for canonical JSON strings carrying
   nested xref source members.
3. Wire target and target-component entity configs to that validator.
4. Add regression coverage proving parity between registry, observed-value
   inventory, and runtime validation.
5. Decide and document how legacy unknown namespaces should be handled.

## Suggested File Targets

- `configs/vocab/chembl_reference_sources.yaml`
- `configs/entities/chembl/target.yaml`
- `configs/entities/chembl/target_component.yaml`
- `src/bioetl/domain/behavior/_dq_rule_evaluators.py`
- `tests/integration/config/test_chembl_observed_value_fixtures.py`
- `tests/contract/test_normalization_cross_layer_contracts.py`

## Testing Expectations

- Add nested JSON member validator tests for both target surfaces.
- Extend observed-value governance tests so runtime and offline registry checks
  stay aligned.
- Re-run ChEMBL target/target_component contract and DQ slices.
- If any rewriting is introduced instead of validation-only behavior, add
  explicit hash regression coverage.

## Documentation Updates

- Update ChEMBL target and target-component provider docs under
  `docs/04-reference/providers/chembl/`.
- Refresh generated normalization matrix artifacts if nested governed fields are
  surfaced there.
- Document the reviewed unknown-namespace posture in the registry/config
  comments.

## Done When

- Nested `xref_src_db` member values are no longer governed only offline.
- Target structured-field runtime validation matches the existing registry.
- The unknown-value posture is explicit, tested, and documented.

## Dependencies

- Follow-up residual issue from `reports/quality/chembl_normalization_audit_2026-05-19.md`.
