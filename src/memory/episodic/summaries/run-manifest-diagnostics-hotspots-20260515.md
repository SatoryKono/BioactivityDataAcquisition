---
id: run-manifest-diagnostics-hotspots-20260515
title: Reduced runtime-builder provider/entity drift
task_id: run-manifest-diagnostics-hotspots-20260515
created_at: '2026-05-15T08:37:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/runtime_builders/control_plane.py
summary: Updated runtime_builders.control_plane to resolve provider/entity through
  the canonical run-manifest support seam instead of splitting pipeline_name, and
  added a focused unit test covering yaml-driven provider/entity resolution for effective-config
  artifact creation.
---

# Episodic summary

## Task

- Title: Reduced runtime-builder provider/entity drift

## Outcome

- Updated runtime_builders.control_plane to resolve provider/entity through the canonical run-manifest support seam instead of splitting pipeline_name, and added a focused unit test covering yaml-driven provider/entity resolution for effective-config artifact creation.

## Lessons learned

- Replace with durable follow-up if needed
