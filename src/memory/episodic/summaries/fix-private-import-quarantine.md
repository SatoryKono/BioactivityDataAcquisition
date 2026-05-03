---
id: fix-private-import-quarantine
title: Fix quarantine CLI private module import architecture failure
task_id: fix-private-import-quarantine
created_at: '2026-05-03T05:42:35Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/quarantine.py
summary: Fixed owner-aware private module import failure by re-exporting RunManifestInspectionServiceProtocol
  through the public quarantine support module and importing it from that public surface
  in CLI quarantine command. Verified private import architecture guard, ruff, and
  py_compile.
---

# Episodic summary

## Task

- Title: Fix quarantine CLI private module import architecture failure

## Outcome

- Fixed owner-aware private module import failure by re-exporting RunManifestInspectionServiceProtocol through the public quarantine support module and importing it from that public surface in CLI quarantine command. Verified private import architecture guard, ruff, and py_compile.

## Lessons learned

- Replace with durable follow-up if needed
