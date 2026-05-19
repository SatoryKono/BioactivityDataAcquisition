---
id: gold-trace-publication-status-fix
title: Fix reproducibility contract drift for gold trace publication_status
task_id: gold-trace-publication-status-fix
created_at: '2026-05-19T09:13:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/runtime_builders/control_plane.py
summary: Made attach_manifest_id tolerant to legacy mock refs missing source_fingerprint
  and updated stale artifact_refs test expectations to include intentional publication_status
  in manifest diagnostics surfaces.
---

# Episodic summary

## Task

- Title: Fix reproducibility contract drift for gold trace publication_status

## Outcome

- Made attach_manifest_id tolerant to legacy mock refs missing source_fingerprint and updated stale artifact_refs test expectations to include intentional publication_status in manifest diagnostics surfaces.

## Lessons learned

- Replace with durable follow-up if needed
