---
id: fix-module-coverage-hotspot-evidence-20260525
title: Fix module coverage hotspot evidence
task_id: fix-module-coverage-hotspot-evidence-20260525
created_at: '2026-05-25T14:24:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/module-coverage-inventory.json
summary: Restored module coverage inventory to canonical coverage-verify measurements
  while refreshing current source-tree facts; target architecture inventory tests
  pass and local narrow coverage XML is not used to overwrite hotspot evidence.
---

# Episodic summary

## Task

- Title: Fix module coverage hotspot evidence

## Outcome

- Restored module coverage inventory to canonical coverage-verify measurements while refreshing current source-tree facts; target architecture inventory tests pass and local narrow coverage XML is not used to overwrite hotspot evidence.

## Lessons learned

- Do not refresh `reports/quality/module-coverage-inventory.json` from a
  narrow local `reports/coverage/coverage.xml`; preserve canonical
  coverage-verify measurements and update only current source-tree facts unless
  a full coverage-verify lane has just produced the XML.
