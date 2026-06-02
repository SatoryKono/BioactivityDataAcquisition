---
id: selector-shell-implementation
title: Implement selector-shell backend stabilization
task_id: selector-shell-implementation
created_at: '2026-06-01T19:14:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/http/control_plane_selector_context.py
summary: Implemented the first execution slice for exact-run selector correctness.
  control_plane_selector_context.build_selector_filter_options_payload now narrows
  manifests with fail_open_when_empty=False so Run ID options fail closed instead
  of falling back to the full manifest catalog on zero-match workflow/pipeline/run_type
  scope. Added direct and endpoint regression tests covering zero-match fail-closed
  Run ID options plus strengthened selector-context exact-run invariant by asserting
  workflow resolution on selected_run_id override. Refreshed reports/quality/module-coverage-inventory.json
  by updating only source_tree_sha256 to the current computed value after src changes.
---

# Episodic summary

## Task

- Title: Implement selector-shell backend stabilization

## Outcome

- Implemented the first execution slice for exact-run selector correctness. control_plane_selector_context.build_selector_filter_options_payload now narrows manifests with fail_open_when_empty=False so Run ID options fail closed instead of falling back to the full manifest catalog on zero-match workflow/pipeline/run_type scope. Added direct and endpoint regression tests covering zero-match fail-closed Run ID options plus strengthened selector-context exact-run invariant by asserting workflow resolution on selected_run_id override. Refreshed reports/quality/module-coverage-inventory.json by updating only source_tree_sha256 to the current computed value after src changes.

## Lessons learned

- Replace with durable follow-up if needed
