---
id: fix-scripts-catalog-active-surface-cap
title: Fix scripts catalog active script surface cap drift
task_id: fix-scripts-catalog-active-surface-cap
created_at: '2026-06-19T15:55:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/repo/catalog.yaml
summary: 'Resolved scripts catalog governance drift without increasing the no-growth
  budget. The live scripts inventory now reports active=363/supporting=75. scripts/engineering/repo/catalog.yaml
  active_script_count_max was ratcheted down to 363. configs/quality/scripts_lifecycle_registry.json
  classifies scripts/engineering/qa/analyze_duplicate_functions.py as a compatibility_wrapper,
  allowing the legacy duplicate-function analyzer wrapper to leave the active surface.
  Regenerated configs/quality/scripts_inventory_manifest.json with the canonical sync
  tool. Validation passed: scripts inventory --check, scripts catalog check, lifecycle
  registry check, Linux pytest tests/architecture/test_scripts_catalog_governance.py,
  and Windows .venv-win pytest for the same architecture file.'
---

# Episodic summary

## Task

- Title: Fix scripts catalog active script surface cap drift

## Outcome

- Resolved scripts catalog governance drift without increasing the no-growth budget. The live scripts inventory now reports active=363/supporting=75. scripts/engineering/repo/catalog.yaml active_script_count_max was ratcheted down to 363. configs/quality/scripts_lifecycle_registry.json classifies scripts/engineering/qa/analyze_duplicate_functions.py as a compatibility_wrapper, allowing the legacy duplicate-function analyzer wrapper to leave the active surface. Regenerated configs/quality/scripts_inventory_manifest.json with the canonical sync tool. Validation passed: scripts inventory --check, scripts catalog check, lifecycle registry check, Linux pytest tests/architecture/test_scripts_catalog_governance.py, and Windows .venv-win pytest for the same architecture file.

## Lessons learned

- Replace with durable follow-up if needed
