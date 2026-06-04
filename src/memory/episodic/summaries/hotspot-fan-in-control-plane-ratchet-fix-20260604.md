---
id: hotspot-fan-in-control-plane-ratchet-fix-20260604
title: Fix control-plane hotspot fan-in ratchet
task_id: hotspot-fan-in-control-plane-ratchet-fix-20260604
created_at: '2026-06-04T11:30:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Reduced application_services_control_plane internal fan-in by moving snapshot_support
  off the broad run_manifest_diagnostics_support facade onto the owner module manifest.snapshot_payloads
  for manifest_input_snapshot_trace_refs. Verified test_hotspot_fan_in_family_ratchets.py
  and test_control_plane_ownership_boundaries.py pass. Module-coverage source_tree_sha256
  refresh was attempted but remains unreliable on the current shared-drive worktree,
  so that guard was not revalidated here.
---

# Episodic summary

## Task

- Title: Fix control-plane hotspot fan-in ratchet

## Outcome

- Reduced application_services_control_plane internal fan-in by moving snapshot_support off the broad run_manifest_diagnostics_support facade onto the owner module manifest.snapshot_payloads for manifest_input_snapshot_trace_refs. Verified test_hotspot_fan_in_family_ratchets.py and test_control_plane_ownership_boundaries.py pass. Module-coverage source_tree_sha256 refresh was attempted but remains unreliable on the current shared-drive worktree, so that guard was not revalidated here.

## Lessons learned

- Replace with durable follow-up if needed
