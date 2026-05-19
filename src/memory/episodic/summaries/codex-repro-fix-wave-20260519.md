---
id: codex-repro-fix-wave-20260519
title: Implement reproducibility issue pack 4261 4262 4263 4264
task_id: codex-repro-fix-wave-20260519
created_at: '2026-05-19T04:50:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Implemented and closed reproducibility issues #4261-#4264 on main via commit
  288c5c0d28948d4501a43a58b4908787698f9e67. Preserved normalization and snapshot anchors
  during checkpoint identity enrichment; added occurrence-pinned workflow resume by
  manifest_id/run_id while excluding selectors from execution fingerprint; introduced
  explicit legacy config_hash compatibility seam; removed filesystem mtime from replay-critical
  Bronze snapshot evidence. Validated with targeted unit and architecture tests.'
---

# Episodic summary

## Task

- Title: Implement reproducibility issue pack 4261 4262 4263 4264

## Outcome

- Implemented and closed reproducibility issues #4261-#4264 on main via commit 288c5c0d28948d4501a43a58b4908787698f9e67. Preserved normalization and snapshot anchors during checkpoint identity enrichment; added occurrence-pinned workflow resume by manifest_id/run_id while excluding selectors from execution fingerprint; introduced explicit legacy config_hash compatibility seam; removed filesystem mtime from replay-critical Bronze snapshot evidence. Validated with targeted unit and architecture tests.

## Lessons learned

- Replace with durable follow-up if needed
