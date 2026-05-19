---
id: align-assay-parameters-unit-profile-test
title: Align stale assay-parameters unit-profile test with current runtime contract
task_id: align-assay-parameters-unit-profile-test
created_at: '2026-05-19T12:02:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/domain/normalization/profiles/test_chembl_assay_parameters_units.py
- src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py
summary: Updated the assay-parameters unit-profile unit test from the retired non-bundle
  expectation to the current optional UO/QUDT companion-bundle contract and verified
  the targeted unit test plus chembl policy surface parity suite pass.
---

# Episodic summary

## Task

- Title: Align stale assay-parameters unit-profile test with current runtime contract

## Outcome

- Updated the assay-parameters unit-profile unit test from the retired non-bundle expectation to the current optional UO/QUDT companion-bundle contract and verified the targeted unit test plus chembl policy surface parity suite pass.

## Lessons learned

- Replace with durable follow-up if needed
