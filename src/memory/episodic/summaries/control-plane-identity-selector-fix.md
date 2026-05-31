---
id: control-plane-identity-selector-fix
title: Fix control-plane identity selector regressions
task_id: control-plane-identity-selector-fix
created_at: '2026-05-31T16:59:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/http/test_health_server_control_plane_identity.py
summary: Updated control-plane identity-table routing to load persisted checkpoint
  metadata for the resolved scope before building rows. Verified the latest-manifest
  and selected-run identity-table flows now classify checkpoint anchors from persisted
  evidence, and refreshed module-coverage inventory source_tree_sha256 after editing
  src/bioetl.
---

# Episodic summary

## Task

- Title: Fix control-plane identity selector regressions

## Outcome

- Updated control-plane identity-table routing to load persisted checkpoint metadata for the resolved scope before building rows. Verified the latest-manifest and selected-run identity-table flows now classify checkpoint anchors from persisted evidence, and refreshed module-coverage inventory source_tree_sha256 after editing src/bioetl.

## Lessons learned

- Replace with durable follow-up if needed
