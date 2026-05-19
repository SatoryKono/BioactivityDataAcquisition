---
id: uniprot-dq-pattern-regression
title: Debug UniProt protein DQ pattern regression in sequential E2E
task_id: uniprot-dq-pattern-regression
created_at: '2026-05-19T10:41:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Updated UniProt protein DQ regex rules to accept canonical structured reference
  arrays for go_terms/interpro_xrefs/pfam_xrefs/reactome_xrefs while preserving legacy
  string-array compatibility; added integration regression test and confirmed sequential
  ChEMBL+UniProt E2E passes.
---

# Episodic summary

## Task

- Title: Debug UniProt protein DQ pattern regression in sequential E2E

## Outcome

- Updated UniProt protein DQ regex rules to accept canonical structured reference arrays for go_terms/interpro_xrefs/pfam_xrefs/reactome_xrefs while preserving legacy string-array compatibility; added integration regression test and confirmed sequential ChEMBL+UniProt E2E passes.

## Lessons learned

- Replace with durable follow-up if needed
