# Complete Consistent Case and Ontology ID Canonicalization

**Status**: In Progress
**Priority**: P1 (High)
**Labels**: `normalization`, `data-quality`, `architecture`, `cross-pipeline`
**Epic**: Cross-Pipeline Normalization Improvements 2026Q2
**Last audited**: 2026-05-08

## Current Decision

This task remains active, but the shared primitives already exist. The remaining
work is parity: make every governed ChEMBL case and ontology family use the same
runtime rules, config metadata, tests, and generated matrix semantics.

## Current Repo State

- Shared case primitive:
  `src/bioetl/domain/normalization/rules.py::normalize_cross_pipeline_case`.
- Shared ontology primitive:
  `src/bioetl/domain/normalization/identifiers.py::normalize_ontology_id`.
- Ontology registry:
  `configs/vocab/chembl_ontology.yaml`.
- Controlled-vocabulary metadata:
  `configs/vocab/chembl_controlled.yaml`.
- Normalization profiles already reference ontology/case helpers for BAO, CLO,
  EFO, UBERON, BTO, CALOHA, and related families.
- Existing test coverage includes:
  - `tests/unit/domain/normalization/test_rules.py`
  - `tests/unit/domain/normalization/test_chembl_ontology_companions.py`
  - `tests/contract/test_chembl_case_and_ontology_consistency.py`
  - `tests/contract/test_normalization_cross_layer_contracts.py`
  - `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`

## Remaining Problem

The implementation is broad but not yet closed out as a cross-pipeline
contract. The repo still needs an explicit audit that every governed field
family has matching:

- canonical case strategy
- ontology prefix and separator policy
- companion IRI/version/status fields where required
- generated normalization matrix metadata
- schema/config validation expectations

## Implementation Plan

1. Inventory governed case and ontology fields from:
   - `configs/vocab/chembl_controlled.yaml`
   - `configs/vocab/chembl_ontology.yaml`
   - ChEMBL normalization profiles
   - generated normalization field matrix tests
2. Create a parity checklist by family:
   - enum text fields: uppercase unless explicitly source-specific
   - free-text descriptions: preserve after trimming/null normalization
   - ontology IDs: canonical underscore form such as `BAO_0000357`
   - companion fields: IRI/version/status emitted for mapped identifiers
3. Patch any remaining profile/config/schema mismatch.
4. Tighten tests so adding a new ontology/case family requires matrix and
   contract alignment.
5. Regenerate or update documentation/matrix artifacts only after targeted tests
   pass.

## Success Criteria

- [x] Shared case normalization primitive exists.
- [x] Shared ontology ID canonicalization primitive exists.
- [x] BAO, CLO, EFO, UBERON, BTO, and CALOHA families are represented in
      ontology/config/test surfaces.
- [ ] Every governed field family declares one case/identifier strategy.
- [ ] Profile runtime behavior, YAML metadata, and generated matrix output match.
- [ ] Contract tests catch cross-pipeline case or ontology drift.
- [ ] Targeted normalization tests pass.

## Verification

```bash
./.venv/bin/python -m pytest -q tests/unit/domain/normalization/test_rules.py
./.venv/bin/python -m pytest -q tests/unit/domain/normalization/test_chembl_ontology_companions.py
./.venv/bin/python -m pytest -q tests/contract/test_chembl_case_and_ontology_consistency.py
./.venv/bin/python -m pytest -q tests/contract/test_normalization_cross_layer_contracts.py
./.venv/bin/python -m pytest -q tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py
```

## Risks

- Canonicalizing ID separators can change content hashes and downstream joins.
- Some source-specific values may be intentionally case-sensitive; preserve
  them only with explicit metadata.
- Ontology companion-field generation must not invent evidence when a source
  identifier is unmapped or ambiguous.

## Related Issues

- **Depends on**: CROSS-001 (Unified Enum Configuration)
- **Related to**: ChEMBL ontology companion contracts and normalization matrix

## Time Estimate

2 days for parity audit, targeted fixes, and verification.
