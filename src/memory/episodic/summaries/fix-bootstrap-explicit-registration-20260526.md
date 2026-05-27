---
id: fix-bootstrap-explicit-registration-20260526
title: Fix bootstrap explicit pipeline registration contract
task_id: fix-bootstrap-explicit-registration-20260526
created_at: '2026-05-26T04:18:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/runtime/pipeline.py
summary: Updated runtime pipeline bootstrap so bootstrap_pipeline_runner explicitly
  calls prepare_runtime_registry before assembling runner phases. Shared post-registry
  assembly was factored into a private helper so build_runtime_bootstrap_phases keeps
  its existing public semantics while the architecture no-side-effect contract can
  see the deterministic registration seam directly.
---

# Episodic summary

## Task

- Title: Fix bootstrap explicit pipeline registration contract

## Outcome

- Updated runtime pipeline bootstrap so bootstrap_pipeline_runner explicitly calls prepare_runtime_registry before assembling runner phases. Shared post-registry assembly was factored into a private helper so build_runtime_bootstrap_phases keeps its existing public semantics while the architecture no-side-effect contract can see the deterministic registration seam directly.

## Lessons learned

- Architecture tests that inspect AST calls require the canonical bootstrap
  entry point to expose deterministic registration seams directly; hiding the
  call inside a broader phase helper can preserve runtime behavior while still
  violating governance.
