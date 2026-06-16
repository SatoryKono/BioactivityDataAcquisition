---
id: close-5268-5261-composition-seams-dead-code
title: 'Close #5268 composition seams and #5261 zero-import dead-code debt'
task_id: close-5268-5261-composition-seams-dead-code
created_at: '2026-06-16T16:46:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/cli/commands/run.py
- pyproject.toml
- tests/architecture/test_module_coverage_inventory.py
- tests/architecture/test_compatibility_freeze_guards.py
- reports/quality/module-coverage-inventory.json
- reports/quality/compatibility-importer-census.json
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5268
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5261
summary: 'Closed #5268 and #5261 by narrowing first-party CLI run helper access away
  from the retained singleton compatibility accessor, measuring retained BioETL __main__
  entrypoints in module coverage, adding fail-fast coverage/compatibility guards,
  refreshing compatibility census and module coverage inventory, and confirming dead-code
  inventory remains fully classified with zero untriaged candidates.'
---

# Episodic summary

## Task

- Title: Close #5268 composition seams and #5261 zero-import dead-code debt

## Outcome

- Closed #5268 and #5261 by narrowing first-party CLI run helper access away from the retained singleton compatibility accessor, measuring retained BioETL __main__ entrypoints in module coverage, adding fail-fast coverage/compatibility guards, refreshing compatibility census and module coverage inventory, and confirming dead-code inventory remains fully classified with zero untriaged candidates.

## Lessons learned

- Retained module entrypoints should be measured directly once coverage config stops omitting `src/bioetl/**/__main__.py`; do not grow coverage exemptions for this class of seam.
