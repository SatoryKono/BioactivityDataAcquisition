---
id: reproducibility-golden-drift-fix
title: Fix reproducibility golden drift
task_id: reproducibility-golden-drift-fix
created_at: '2026-05-06T13:25:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/services/test_reproducibility_golden_fixtures.py
summary: Updated reproducibility golden fixtures to reflect dependency_lock_hash_missing
  audit blockers and verified related normalization-matrix regressions after adding
  chembl publication issn_list to the reviewed silver schema.
---

# Episodic summary

## Task

- Title: Fix reproducibility golden drift

## Outcome

- Updated reproducibility golden fixtures to reflect dependency_lock_hash_missing audit blockers and verified related normalization-matrix regressions after adding chembl publication issn_list to the reviewed silver schema.

## Lessons learned

- Replace with durable follow-up if needed
