---
id: fix-domain-purity-pipeline-run-complete-cc
title: Fix domain purity cyclomatic complexity for pipeline run completion guard
task_id: fix-domain-purity-pipeline-run-complete-cc
created_at: '2026-06-19T14:44:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/aggregates/_pipeline_run_mixins.py
summary: 'Refactored PipelineRun._assert_can_complete into focused private guards
  for failed stages, missing stages, and non-success stages so domain cyclomatic complexity
  stays within the CC<=5 gate while preserving existing InvalidStateError messages
  and check ordering. Removed unused imports from the related internal mixin unit
  test file after ruff surfaced them. Updated module coverage inventory and architecture
  scorecard source artifact hashes to match the current src tree. Validation: targeted
  domain purity CC pytest passed, related PipelineRun aggregate unit/property pytest
  passed, ruff check passed, architecture scorecard module coverage consistency pytest
  passed, module coverage hash pytest skipped on WSL per repository skip marker.'
---

# Episodic summary

## Task

- Title: Fix domain purity cyclomatic complexity for pipeline run completion guard

## Outcome

- Refactored PipelineRun._assert_can_complete into focused private guards for failed stages, missing stages, and non-success stages so domain cyclomatic complexity stays within the CC<=5 gate while preserving existing InvalidStateError messages and check ordering. Removed unused imports from the related internal mixin unit test file after ruff surfaced them. Updated module coverage inventory and architecture scorecard source artifact hashes to match the current src tree. Validation: targeted domain purity CC pytest passed, related PipelineRun aggregate unit/property pytest passed, ruff check passed, architecture scorecard module coverage consistency pytest passed, module coverage hash pytest skipped on WSL per repository skip marker.

## Lessons learned

- Replace with durable follow-up if needed
