---
id: fix-strict-gold-schema-unknown-column-violation
title: Fix strict gold schema unknown column contract failure
task_id: fix-strict-gold-schema-unknown-column-violation
created_at: '2026-06-04T15:23:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Verified strict Gold unknown-column contract behavior. Current test surface
  catches Pandera SchemaErrors for unknown columns, strict-gold contract file passes,
  and shared minimal schema dataframe helper now provides valid dtype/domain defaults
  for impacted PubChem/UniProt/publication schema tests. Ran ruff on impacted test
  helpers and contract tests; no src changes required.
---

# Episodic summary

## Task

- Title: Fix strict gold schema unknown column contract failure

## Outcome

- Verified strict Gold unknown-column contract behavior. Current test surface catches Pandera SchemaErrors for unknown columns, strict-gold contract file passes, and shared minimal schema dataframe helper now provides valid dtype/domain defaults for impacted PubChem/UniProt/publication schema tests. Ran ruff on impacted test helpers and contract tests; no src changes required.

## Lessons learned

- Replace with durable follow-up if needed
