---
id: debug-artifact-duplication-audit-drift
title: Debug architecture artifact drift
task_id: debug-artifact-duplication-audit-drift
created_at: '2026-06-23T06:02:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/config-contract-registry-artifact-duplication.json
- reports/quality/module-coverage-inventory.json
- reports/quality/domain-io-taint-inventory.json
summary: Refreshed stale generated quality artifacts after architecture tests compared
  saved reports with live collectors. Updated config-contract registry duplication
  counts for one additional configs/**/*.yaml registry-scoped file, restored module
  coverage inventory to the canonical coverage-verify artifact while preserving the
  current source_tree_sha256, and verified the domain I/O taint inventory against
  the new domain source file. Duplicate groups/files and Domain I/O violations remain
  zero; targeted architecture subset and generator checks pass.
---

# Episodic summary

## Task

- Title: Debug architecture artifact drift

## Outcome

- Refreshed stale generated quality artifacts after architecture tests compared saved reports with live collectors. Updated config-contract registry duplication counts for one additional configs/**/*.yaml registry-scoped file, restored module coverage inventory to the canonical coverage-verify artifact while preserving the current source_tree_sha256, and verified the domain I/O taint inventory against the new domain source file. Duplicate groups/files and Domain I/O violations remain zero; targeted architecture subset and generator checks pass.

## Lessons learned

- Replace with durable follow-up if needed
