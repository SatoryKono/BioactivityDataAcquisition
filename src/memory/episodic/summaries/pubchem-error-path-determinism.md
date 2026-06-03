---
id: pubchem-error-path-determinism
title: Fix PubChem error-path determinism
task_id: pubchem-error-path-determinism
created_at: '2026-06-03T10:36:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/adapters/test_pubchem.py
summary: Replaced live/VCR-dependent PubChem error-path assertions with deterministic
  failing fetch-flow injection. Query failures now assert OSError propagation; SMILES
  and CID failure paths assert logged empty-result behavior without relying on upstream
  PubChem identifiers. Targeted error-path tests, full PubChem integration file, ruff
  check/format, and test-governance audit pass.
---

# Episodic summary

## Task

- Title: Fix PubChem error-path determinism

## Outcome

- Replaced live/VCR-dependent PubChem error-path assertions with deterministic failing fetch-flow injection. Query failures now assert OSError propagation; SMILES and CID failure paths assert logged empty-result behavior without relying on upstream PubChem identifiers. Targeted error-path tests, full PubChem integration file, ruff check/format, and test-governance audit pass.

## Lessons learned

- Replace with durable follow-up if needed
