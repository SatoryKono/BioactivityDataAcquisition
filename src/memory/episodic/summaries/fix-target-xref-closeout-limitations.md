---
id: fix-target-xref-closeout-limitations
title: Fix target_xref_modification validation limitations
task_id: fix-target-xref-closeout-limitations
created_at: '2026-05-31T14:43:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Fixed validate-configs by aligning composition registry validation with
  the canonical config validator: legacy provider=composite stubs under configs/entities
  are ignored because runtime composite configs live under configs/composites. Added
  regression coverage for this behavior. Verified transformer snapshot tests with
  project-managed environments where syrupy is available via .venv and uv run, avoiding
  the system-python missing-dependency limitation. Refreshed module coverage inventory
  after src changes.'
---

# Episodic summary

## Task

- Title: Fix target_xref_modification validation limitations

## Outcome

- Fixed validate-configs by aligning composition registry validation with the canonical config validator: legacy provider=composite stubs under configs/entities are ignored because runtime composite configs live under configs/composites. Added regression coverage for this behavior. Verified transformer snapshot tests with project-managed environments where syrupy is available via .venv and uv run, avoiding the system-python missing-dependency limitation. Refreshed module coverage inventory after src changes.

## Lessons learned

- Replace with durable follow-up if needed
