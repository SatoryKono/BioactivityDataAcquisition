---
id: arch-debt-issues-5402-5414
title: Close architecture debt issue batch 5402-5414
task_id: arch-debt-issues-5402-5414
created_at: '2026-06-18T17:38:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/manifest/validation.py
- src/bioetl/infrastructure/compat/pandera_compat.py
- tests/unit/application/services/test_run_manifest_service.py
- tests/unit/infrastructure/test_pandera_python314_support.py
- docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md
- configs/quality/observability_metric_governance.yaml
summary: 'Closed GitHub issue #5414 with evidence from committed observability cardinality
  governance gates. Implemented local changes for #5402 strict RunManifest provenance
  construction-time validation and #5412 Pandera Python 3.14 sunset metadata/tests/docs,
  with targeted ruff and unit tests passing. Full closeout for #5402-#5413 is blocked
  by current repository state: a parallel commit changed HEAD to 438bf67df and left
  staged/worktree leftovers around module coverage and protein_class_target_type/protein_class_target_type_helpers;
  module coverage --check is stale because current working tree module count differs
  from the committed/staged artifact. No tech-debt budgets were increased.'
---

# Episodic summary

## Task

- Title: Close architecture debt issue batch 5402-5414

## Outcome

- Closed GitHub issue #5414 with evidence from committed observability cardinality governance gates. Implemented local changes for #5402 strict RunManifest provenance construction-time validation and #5412 Pandera Python 3.14 sunset metadata/tests/docs, with targeted ruff and unit tests passing. Full closeout for #5402-#5413 is blocked by current repository state: a parallel commit changed HEAD to 438bf67df and left staged/worktree leftovers around module coverage and protein_class_target_type/protein_class_target_type_helpers; module coverage --check is stale because current working tree module count differs from the committed/staged artifact. No tech-debt budgets were increased.

## Lessons learned

- Replace with durable follow-up if needed
