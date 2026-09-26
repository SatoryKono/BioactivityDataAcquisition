---
title: "[TEST-AUDIT-011] Consolidate generated schema validation tests with explicit assertions"
github_issue: 5498
labels: enhancement, technical-debt
assignees: []
---

## Context

The 2026-06-22 audit found strong Gold and contract coverage overall, but also a
large volume of generated schema-validation tests that validate happy paths by
relying on `Schema.validate(...)` not raising.

## Problem

`reports/quality/test-governance-current.json` reports 497
`assertless_candidates`. Many are intentional no-exception contracts, but the
largest clusters are generated publication schema validation files:

- `tests/unit/domain/schemas/pubmed/test_pubmed_publication_validation.py` - 100 candidates
- `tests/unit/domain/schemas/openalex/test_openalex_publication_validation.py` - 76 candidates
- `tests/unit/domain/schemas/crossref/test_crossref_publication_validation.py` - 72 candidates
- `tests/unit/domain/schemas/semanticscholar/test_semanticscholar_publication_validation.py` - 67 candidates
- `tests/unit/domain/schemas/chembl/test_chembl_publication_validation.py` - 53 candidates

## Acceptance Criteria

- [ ] Generated publication schema tests no longer dominate `assertless_candidates`.
- [ ] Happy-path validation tests assert returned dataframe shape, columns, or normalized values.
- [ ] Negative validation tests assert meaningful error details, not only that `SchemaError` was raised.
- [ ] `contract-coverage-matrix.json` still reports 27/27 covered Gold-enabled rows.
- [ ] No Gold schema, DQ rule, determinism, or replay contract coverage is removed.

