---
id: debug-persistence-profile-strict-kwarg-20260521
title: Debug workflow run TypeError for strict_persistence_profiles kwarg
task_id: debug-persistence-profile-strict-kwarg-20260521
created_at: '2026-05-21T16:42:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/control_plane/reproducibility_policy.py
summary: Fixed workflow run TypeError by making public domain.control_plane.reproducibility_policy.resolve_effective_required_persistence_profile
  accept the low-level strict_persistence_profiles keyword and default to central
  STRICT_PERSISTENCE_PROFILES when omitted. Added regression coverage and verified
  Windows .venv workflow dry-run for chembl_target degraded_observable plus runtime-builder
  persistence tests.
---

# Episodic summary

## Task

- Title: Debug workflow run TypeError for strict_persistence_profiles kwarg

## Outcome

- Fixed workflow run TypeError by making public domain.control_plane.reproducibility_policy.resolve_effective_required_persistence_profile accept the low-level strict_persistence_profiles keyword and default to central STRICT_PERSISTENCE_PROFILES when omitted. Added regression coverage and verified Windows .venv workflow dry-run for chembl_target degraded_observable plus runtime-builder persistence tests.

## Lessons learned

- Replace with durable follow-up if needed
