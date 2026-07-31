---
record_id: debug-export-openpyxl-core-properties
record_type: working
repo_id: bioactivitydataacquisition
git_commit: b3e14f1178765caab280b5fbe51b29011eeb49be
branch: fix/unit-fast-adr-matrix-20260731
worktree_id: ccd98afae0adb4ee
task_id: debug-export-openpyxl-core-properties
actor:
  runtime: codex
  agent: root
  model: null
created_at: '2026-07-31T06:04:53.312589+00:00'
source_refs:
- src/bioetl/infrastructure/export/debug_export_ops.py
- src/bioetl/infrastructure/export/debug_export_adapter.py
- tests/unit/infrastructure/export/test_debug_export_adapter.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 231b3673a27fe342c083802d4d5377d27e11d26623752f026f05869427b1d0c3
id: debug-export-openpyxl-core-properties
title: Fix deterministic debug export workbook
ttl_days: 14
confidence: episodic
summary: Fixed Windows openpyxl 3.1.5 core-properties serialization with a deterministic
  non-null workbook timestamp; changed debug_export_hash to hash semantic table content
  while excluding occurrence created_at; added Windows-focused regression coverage
  and refreshed module coverage inventory.
---

# Episodic summary

## Task

- Title: Fix deterministic debug export workbook

## Outcome

- Fixed Windows openpyxl 3.1.5 core-properties serialization with a deterministic non-null workbook timestamp; changed debug_export_hash to hash semantic table content while excluding occurrence created_at; added Windows-focused regression coverage and refreshed module coverage inventory.

## Lessons learned

- Replace with durable follow-up if needed
