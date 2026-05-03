---
id: fix-domain-run-manifest-serialization-cc
title: Reduce domain run manifest serialization cyclomatic complexity
task_id: fix-domain-run-manifest-serialization-cc
created_at: '2026-05-03T05:51:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/control_plane/_run_manifest_serialization.py
summary: Reduced freeze_manifest_payload cyclomatic complexity by replacing explicit
  mapping/sequence/set branching with a pure freezer-dispatch tuple while preserving
  deep-freeze behavior and fallback deepcopy. Verified domain complexity guard, ruff,
  py_compile, and domain control-plane serialization-related unit tests.
---

# Episodic summary

## Task

- Title: Reduce domain run manifest serialization cyclomatic complexity

## Outcome

- Reduced freeze_manifest_payload cyclomatic complexity by replacing explicit mapping/sequence/set branching with a pure freezer-dispatch tuple while preserving deep-freeze behavior and fallback deepcopy. Verified domain complexity guard, ruff, py_compile, and domain control-plane serialization-related unit tests.

## Lessons learned

- Replace with durable follow-up if needed
