---
id: fix-stale-file-size-exemption
title: Fix stale file size exemption
task_id: fix-stale-file-size-exemption
created_at: '2026-05-21T08:45:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
summary: Removed stale file_size_limits exemption for src/bioetl/application/services/control_plane/_run_manifest_diagnostics_base.py
  after the module fell below the default application-layer file size limit.
---

# Episodic summary

## Task

- Title: Fix stale file size exemption

## Outcome

- Removed stale file_size_limits exemption for src/bioetl/application/services/control_plane/_run_manifest_diagnostics_base.py after the module fell below the default application-layer file size limit.

## Lessons learned

- Replace with durable follow-up if needed
