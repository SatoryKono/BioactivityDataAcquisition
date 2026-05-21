---
id: issues-4382-4381-4380-control-plane-governance-20260521
title: Implement control-plane duplication FSM ownership and generated governance
  refresh
task_id: issues-4382-4381-4380-control-plane-governance-20260521
created_at: '2026-05-21T08:43:29Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/_ledger_identity_support.py
- src/bioetl/application/composite/runner_pkg/runner_stage_mixin.py
- configs/quality/debt_scorecard.yaml
summary: Reduced application/services/control_plane duplication from 20 to 17 clusters
  by extracting shared ledger identity, manifest-time, and checkpoint-anchor diagnostic
  helpers; routed composite seed resume through the explicit recovery transition service;
  refreshed dependency-map, hotspot-family, hotspot-duplication, scripts inventory,
  and lifecycle registry governance artifacts.
---

# Episodic summary

## Task

- Title: Implement control-plane duplication FSM ownership and generated governance refresh

## Outcome

- Reduced application/services/control_plane duplication from 20 to 17 clusters by extracting shared ledger identity, manifest-time, and checkpoint-anchor diagnostic helpers; routed composite seed resume through the explicit recovery transition service; refreshed dependency-map, hotspot-family, hotspot-duplication, scripts inventory, and lifecycle registry governance artifacts.

## Lessons learned

- Replace with durable follow-up if needed
