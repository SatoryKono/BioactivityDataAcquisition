---
id: dbg-chembl-publication-fixtures
title: Fix missing fixture aliases in chembl publication subset policy tests
task_id: dbg-chembl-publication-fixtures
created_at: '2026-06-02T08:38:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_chembl_publication_subset_policy.py
summary: Added backward-compatible underscored fixture aliases in the ChEMBL publication
  subset policy architecture test module so existing tests resolve chembl_enum_config
  and chembl_publication_entity_config consistently.
---

# Episodic summary

## Task

- Title: Fix missing fixture aliases in chembl publication subset policy tests

## Outcome

- Added backward-compatible underscored fixture aliases in the ChEMBL publication subset policy architecture test module so existing tests resolve chembl_enum_config and chembl_publication_entity_config consistently.

## Lessons learned

- Replace with durable follow-up if needed
