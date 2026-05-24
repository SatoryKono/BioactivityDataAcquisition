---
id: debug-run-manifest-append-message-20260524
title: Fix strict replay append-mode error message
task_id: debug-run-manifest-append-message-20260524
created_at: '2026-05-24T13:26:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/runtime_builders/_run_manifest_support.py
summary: Adjusted validate_reproducible_sink_modes error text so strict replay failures
  include the strict reproducibility anchor while replay-capable-family failures keep
  their existing policy wording.
---

# Episodic summary

## Task

- Title: Fix strict replay append-mode error message

## Outcome

- Adjusted validate_reproducible_sink_modes error text so strict replay failures include the strict reproducibility anchor while replay-capable-family failures keep their existing policy wording.

## Lessons learned

- Replace with durable follow-up if needed
