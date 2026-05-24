---
id: implement-rf010-idempotent-sinks-20260524
title: Implement replay-capable sink idempotency guard
task_id: implement-rf010-idempotent-sinks-20260524
created_at: '2026-05-24T13:13:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/runtime_builders/_run_manifest_support.py
summary: Extended validate_reproducible_sink_modes so replay-capable families reject
  append-mode Silver/Gold semantic sinks even outside an explicit strict replay request,
  and wired ManifestReproducibilityContext resolution to pass strict_exact_replay_supported
  into the sink-mode guard. Added unit tests for occurrence_only rejection in replay-capable
  families and non-replay allowance. Verified ruff format/check and targeted sink
  idempotency tests.
---

# Episodic summary

## Task

- Title: Implement replay-capable sink idempotency guard

## Outcome

- Extended validate_reproducible_sink_modes so replay-capable families reject append-mode Silver/Gold semantic sinks even outside an explicit strict replay request, and wired ManifestReproducibilityContext resolution to pass strict_exact_replay_supported into the sink-mode guard. Added unit tests for occurrence_only rejection in replay-capable families and non-replay allowance. Verified ruff format/check and targeted sink idempotency tests.

## Lessons learned

- Replace with durable follow-up if needed
