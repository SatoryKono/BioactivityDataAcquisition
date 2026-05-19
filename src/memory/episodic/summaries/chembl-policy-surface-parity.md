---
id: chembl-policy-surface-parity
title: Fix chembl policy surface parity missing relation row
task_id: chembl-policy-surface-parity
created_at: '2026-05-19T03:34:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/config/test_chembl_policy_surface_parity.py
summary: Updated chembl policy surface parity lookup to honor shipped matrix alias
  seams from ENTITY_PROFILE_FIELD_ALIASES, so governed config fields like chembl_activity.relation
  resolve to their canonical matrix rows instead of reporting false missing coverage.
---

# Episodic summary

## Task

- Title: Fix chembl policy surface parity missing relation row

## Outcome

- Updated chembl policy surface parity lookup to honor shipped matrix alias seams from ENTITY_PROFILE_FIELD_ALIASES, so governed config fields like chembl_activity.relation resolve to their canonical matrix rows instead of reporting false missing coverage.

## Lessons learned

- Replace with durable follow-up if needed
