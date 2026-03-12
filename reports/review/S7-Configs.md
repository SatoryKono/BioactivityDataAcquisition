# Code Review Report — S7: Configs
**Date**: 2026-03-12
**Scope**: configs
**Files reviewed**: 48
**Total LOC**: 8489
**Status**: WARN
**Score**: 7.00/10.0

---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 11 | 0 | 11 | 0 | 0 | 0.00 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.00 |
| DI Violations | 0 | 0 | 0 | 0 | 0 | 10.00 |
| Naming | 0 | 0 | 0 | 0 | 0 | 10.00 |
| Types | 0 | 0 | 0 | 0 | 0 | 10.00 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.00 |
| **TOTAL** | **11** | **0** | **11** | **0** | **0** | **7.00** |

## Critical Issues (MUST fix before merge)
None

## High Issues
### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/uniprot/protein.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/publication_term.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/publication_similarity.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/assay_parameters.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/target.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/target_component.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/assay.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/activity.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/molecule.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/chembl/protein_class.yaml:1`

### ADR-014: Missing sort_by in Silver sink
- **File**: `configs/entities/pubchem/compound.yaml:1`


## Medium Issues
None

## Low Issues
None

## Positive Observations
- Mechanically verified DI bindings and clean boundaries in large parts of the code.
- Types are primarily consistent.

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Architecture | 30.0% | 10 | 11.0 | 0.00 |
| Anti-Patterns | 25.0% | 10 | 0.0 | 2.50 |
| DI Violations | 20.0% | 10 | 0.0 | 2.00 |
| Naming | 10.0% | 10 | 0.0 | 1.00 |
| Types | 10.0% | 10 | 0.0 | 1.00 |
| Testing | 5.0% | 10 | 0.0 | 0.50 |
| **FINAL** | **100%** | | | **7.00** |
