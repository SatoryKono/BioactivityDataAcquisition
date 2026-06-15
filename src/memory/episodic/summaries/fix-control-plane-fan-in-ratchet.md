---
id: fix-control-plane-fan-in-ratchet
title: Fix control plane hotspot fan-in ratchet
task_id: fix-control-plane-fan-in-ratchet
created_at: '2026-06-15T17:42:30Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/manifest/diagnostics/replay_helpers.py
summary: Reduced application_services_control_plane max_internal_fan_in back to budget
  by splitting diagnostics imports away from replay_helpers and turning replay_helpers
  into a thin dynamic facade with no static owner-module imports.
---

# Episodic summary

## Task

- Title: Fix control plane hotspot fan-in ratchet

## Outcome

- Reduced application_services_control_plane max_internal_fan_in back to budget by splitting diagnostics imports away from replay_helpers and turning replay_helpers into a thin dynamic facade with no static owner-module imports.

## Lessons learned

- Replace with durable follow-up if needed
