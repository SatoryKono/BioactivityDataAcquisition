---
id: fix-run-manifest-legacy-config-hash-contract
title: Fix run manifest legacy config_hash alias contract drift
task_id: fix-run-manifest-legacy-config-hash-contract
created_at: '2026-05-03T05:46:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/runtime_builders/run_manifest_builder.py
summary: Restored explicit legacy config_hash alias wiring in run_manifest_builder
  by passing config_hash=legacy_config_hash_from_resolved_config_hash(resolved_config_hash)
  into the manifest create request inputs, with creation support consuming the prepared
  alias. Verified the reproducibility docs drift guard, run manifest support unit
  tests, ruff, and py_compile.
---

# Episodic summary

## Task

- Title: Fix run manifest legacy config_hash alias contract drift

## Outcome

- Restored explicit legacy config_hash alias wiring in run_manifest_builder by passing config_hash=legacy_config_hash_from_resolved_config_hash(resolved_config_hash) into the manifest create request inputs, with creation support consuming the prepared alias. Verified the reproducibility docs drift guard, run manifest support unit tests, ruff, and py_compile.

## Lessons learned

- Replace with durable follow-up if needed
