---
id: runner-builder-fake-factory-nameerror
title: Fix runner builder fake_factory test NameError
task_id: runner-builder-fake-factory-nameerror
created_at: '2026-05-06T07:49:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/runtime_builders/test_runner_builder.py
summary: Fixed tests/unit/composition/runtime_builders/test_runner_builder.py NameError
  by retaining fake_factory from _build_factory_registry() in test_build_pipeline_runner_persists_manifest_before_factory_create.
  Also fixed an existing RUF043 regex warning in the same file. Targeted pytest passed
  for the failing test and ruff passed for the file.
---

# Episodic summary

## Task

- Title: Fix runner builder fake_factory test NameError

## Outcome

- Fixed tests/unit/composition/runtime_builders/test_runner_builder.py NameError by retaining fake_factory from _build_factory_registry() in test_build_pipeline_runner_persists_manifest_before_factory_create. Also fixed an existing RUF043 regex warning in the same file. Targeted pytest passed for the failing test and ruff passed for the file.

## Lessons learned

- Replace with durable follow-up if needed
