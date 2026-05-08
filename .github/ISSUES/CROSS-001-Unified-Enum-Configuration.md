# Complete Unified Enum Configuration Across ChEMBL Pipelines

**Status**: In Progress
**Priority**: P0 (Critical)
**Labels**: `normalization`, `configuration`, `architecture`, `cross-pipeline`
**Epic**: Cross-Pipeline Normalization Improvements 2026Q2
**Last audited**: 2026-05-08

## Current Decision

This task remains active, but it is no longer greenfield. The central enum
registry, domain loader, schema catalog, and parity tests exist. The remaining
work is closeout: finish cross-pipeline parity, remove residual duplication,
and make drift detection explicit.

## Current Repo State

- Canonical ChEMBL enum registry: `configs/enums/chembl.yaml`.
- Domain enum loader API: `src/bioetl/domain/config/enum_loader.py`.
- Schema-facing catalog: `src/bioetl/domain/schemas/_chembl_enum_catalog.py`.
- Normalization-profile enum lookup helper:
  `src/bioetl/domain/normalization/profiles/_chembl_vocab.py`.
- Existing test coverage includes:
  - `tests/unit/domain/config/test_enum_loader.py`
  - `tests/unit/domain/schemas/test_constants_yaml.py`
  - `tests/integration/config/test_chembl_enum_parity.py`
  - `tests/integration/config/test_chembl_policy_surface_parity.py`
  - `tests/contract/test_chembl_enum_normalization_policy.py`

## Remaining Problem

The repo now has the correct enum architecture, but the issue is not complete
until every governed ChEMBL enum family has one clear source of truth across:

- YAML config
- schema validation/catalogs
- normalization profiles
- entity DQ/config contracts
- generated normalization matrices

Residual hardcoded constants are acceptable only when they are explicitly global
domain value objects or format patterns, not duplicated ChEMBL vocabulary.

## Implementation Plan

1. Inventory all governed ChEMBL enum fields from
   `tests/integration/config/test_chembl_enum_parity.py` and
   `tests/contract/test_chembl_enum_normalization_policy.py`.
2. For each enum family, confirm the value source is `configs/enums/chembl.yaml`
   or a documented global domain value object.
3. Remove duplicated ChEMBL vocabulary from profile/schema code where the YAML
   registry is already canonical.
4. Tighten tests so a new governed enum field must declare:
   - registry coordinate
   - normalization case strategy
   - schema/DQ validation surface
   - matrix/documentation source
5. Update generated/reference documentation only after code and tests are green.

## Success Criteria

- [x] Central ChEMBL enum YAML registry exists.
- [x] Domain enum loader keeps direct file I/O outside the domain layer.
- [x] Activity, assay, molecule, target, publication, and related ChEMBL enum
      families are represented in parity tests.
- [ ] All governed enum families have explicit registry coordinates.
- [ ] Residual local enum duplication is eliminated or justified.
- [ ] Schema, profile, config, and generated matrix surfaces agree on enum
      source and values.
- [ ] Targeted enum and parity tests pass.

## Verification

```bash
./.venv/bin/python -m pytest -q tests/unit/domain/config/test_enum_loader.py
./.venv/bin/python -m pytest -q tests/unit/domain/schemas/test_constants_yaml.py
./.venv/bin/python -m pytest -q tests/integration/config/test_chembl_enum_parity.py
./.venv/bin/python -m pytest -q tests/integration/config/test_chembl_policy_surface_parity.py
./.venv/bin/python -m pytest -q tests/contract/test_chembl_enum_normalization_policy.py
```

## Risks

- Enum canonicalization can change content hashes.
- Over-normalizing source-specific publication subsets can erase intentional
  provider semantics.
- Moving constants blindly can violate the domain I/O boundary; registry reads
  must remain injected through infrastructure adapters.

## Related Issues

- **Blocks**: CROSS-002 (Case Canonicalization)
- **Related to**: ADR-038 enum externalization, ChEMBL policy-surface parity

## Time Estimate

2-3 days for closeout and verification.
