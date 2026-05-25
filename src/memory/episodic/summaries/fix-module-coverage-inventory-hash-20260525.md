---
id: fix-module-coverage-inventory-hash-20260525
title: Fix module coverage inventory source hash
task_id: fix-module-coverage-inventory-hash-20260525
created_at: '2026-05-25T13:53:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/module-coverage-inventory.json
summary: Updated committed module coverage inventory source-tree hash and source line
  facts while preserving coverage-verify measurements because local coverage.xml was
  a narrow non-authoritative run.
---

# Episodic summary

## Task

- Title: Fix module coverage inventory source hash

## Outcome

- Updated committed module coverage inventory source-tree hash and source line facts while preserving coverage-verify measurements because local coverage.xml was a narrow non-authoritative run.

## Lessons learned

- Do not regenerate the committed module coverage inventory from a narrow local
  coverage XML; preserve coverage-verify measurements and refresh only
  source-tree facts unless a green coverage-verify artifact is available.
