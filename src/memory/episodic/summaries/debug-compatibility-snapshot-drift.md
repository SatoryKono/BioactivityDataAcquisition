---
id: debug-compatibility-snapshot-drift
title: Debug compatibility facade snapshot drift
task_id: debug-compatibility-snapshot-drift
created_at: '2026-05-24T13:05:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Fixed compatibility snapshot drift caused by src/bioetl/application/core/pipeline_service_protocols.py
  being unintentionally docstring-tracked as a compatibility module. Root cause: module
  docstring started with the tracked prefix `Compatibility `, but the module is not
  in the curated or measured-only compatibility registry. Updated the module docstring
  to remove the tracked prefix. Verified the snapshot generator check passes and the
  measured docstring surface check returns no unexpected or missing modules.'
---

# Episodic summary

## Task

- Title: Debug compatibility facade snapshot drift

## Outcome

- Fixed compatibility snapshot drift caused by src/bioetl/application/core/pipeline_service_protocols.py being unintentionally docstring-tracked as a compatibility module. Root cause: module docstring started with the tracked prefix `Compatibility `, but the module is not in the curated or measured-only compatibility registry. Updated the module docstring to remove the tracked prefix. Verified the snapshot generator check passes and the measured docstring surface check returns no unexpected or missing modules.

## Lessons learned

- Replace with durable follow-up if needed
