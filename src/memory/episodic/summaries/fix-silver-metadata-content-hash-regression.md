---
id: fix-silver-metadata-content-hash-regression
title: Fix silver metadata integration content_hash regression
task_id: fix-silver-metadata-content-hash-regression
created_at: '2026-05-22T14:45:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Hardened strict replay Silver merge guard so MagicMock-derived run_context
  attributes do not implicitly enable exact replay; only real bool exact_replay or
  real strict required_persistence_profile strings activate the content_hash contract.
  Fixed unit coverage import to target the owning operations module and verified targeted
  ruff, unit validation-operations tests, and the previously failing silver metadata
  integration test all pass.
---

# Episodic summary

## Task

- Title: Fix silver metadata integration content_hash regression

## Outcome

- Hardened strict replay Silver merge guard so MagicMock-derived run_context attributes do not implicitly enable exact replay; only real bool exact_replay or real strict required_persistence_profile strings activate the content_hash contract. Fixed unit coverage import to target the owning operations module and verified targeted ruff, unit validation-operations tests, and the previously failing silver metadata integration test all pass.

## Lessons learned

- Replace with durable follow-up if needed
