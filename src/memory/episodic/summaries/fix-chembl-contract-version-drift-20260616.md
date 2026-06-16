---
id: fix-chembl-contract-version-drift-20260616
title: Fix chembl contract registry version drift
task_id: fix-chembl-contract-version-drift-20260616
created_at: '2026-06-16T14:21:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/base/contract_registry.yaml
summary: Verified chembl.target_protein_classification canonical surfaces already
  converge on contract version 2.1.0 in the current working tree (entity config, contract
  registry, and integration expectation). Targeted contract-registry coverage tests
  pass on the unstaged sync.
---

# Episodic summary

## Task

- Title: Fix chembl contract registry version drift

## Outcome

- Verified chembl.target_protein_classification canonical surfaces already converge on contract version 2.1.0 in the current working tree (entity config, contract registry, and integration expectation). Targeted contract-registry coverage tests pass on the unstaged sync.

## Lessons learned

- Replace with durable follow-up if needed
