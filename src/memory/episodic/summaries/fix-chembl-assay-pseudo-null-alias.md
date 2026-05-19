---
id: fix-chembl-assay-pseudo-null-alias
title: Fix ChEMBL assay pseudo-null alias coverage
task_id: fix-chembl-assay-pseudo-null-alias
created_at: '2026-05-19T03:48:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/domain/normalization/profiles/test_chembl_pseudo_null_policy.py
summary: Normalized the ChEMBL assay pseudo-null registry to use the canonical field
  name assay_description instead of the legacy alias description. This restored null-guard
  wrapping for the real assay profile rule and fixed both schema-coverage and pseudo-null
  collapse regressions in the generic ChEMBL pseudo-null matrix tests. Verified with
  the generic pseudo-null policy suite and the assay-specific pseudo-null regression
  tests.
---

# Episodic summary

## Task

- Title: Fix ChEMBL assay pseudo-null alias coverage

## Outcome

- Normalized the ChEMBL assay pseudo-null registry to use the canonical field name assay_description instead of the legacy alias description. This restored null-guard wrapping for the real assay profile rule and fixed both schema-coverage and pseudo-null collapse regressions in the generic ChEMBL pseudo-null matrix tests. Verified with the generic pseudo-null policy suite and the assay-specific pseudo-null regression tests.

## Lessons learned

- Replace with durable follow-up if needed
