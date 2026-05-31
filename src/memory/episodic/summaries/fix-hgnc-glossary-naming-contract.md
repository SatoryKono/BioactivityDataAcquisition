---
id: fix-hgnc-glossary-naming-contract
title: Fix HGNC glossary naming contract
task_id: fix-hgnc-glossary-naming-contract
created_at: '2026-05-31T14:48:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Documented HGNC ID in docs/00-project/glossary.md and added hgnc to the silver
  schema naming abbreviation allowlist so chembl_target.target_xref_hgnc_ids satisfies
  the glossary-backed naming convention. Validated the failing parametrized naming
  test, full naming conventions module, chembl_target silver schema stability subset,
  JSON/list inventory guard, and ruff on the changed naming test.
---

# Episodic summary

## Task

- Title: Fix HGNC glossary naming contract

## Outcome

- Documented HGNC ID in docs/00-project/glossary.md and added hgnc to the silver schema naming abbreviation allowlist so chembl_target.target_xref_hgnc_ids satisfies the glossary-backed naming convention. Validated the failing parametrized naming test, full naming conventions module, chembl_target silver schema stability subset, JSON/list inventory guard, and ruff on the changed naming test.

## Lessons learned

- Replace with durable follow-up if needed
