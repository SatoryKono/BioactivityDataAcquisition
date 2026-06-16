---
id: close-5268-5261-composition-seams-dead-code
title: 'Close #5268 composition seams and #5261 zero-import dead-code debt'
task_id: close-5268-5261-composition-seams-dead-code
created_at: '2026-06-16T15:53:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5268
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5261
summary: Active task session context.
query: 5268 composition public seams default registry compatibility 5261 zero import
  retained entrypoint exemptions
---

# Session note

## Task

- Title: Close #5268 composition seams and #5261 zero-import dead-code debt
- Retrieval query: 5268 composition public seams default registry compatibility 5261 zero import retained entrypoint exemptions

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- `src/bioetl/interfaces/cli/commands/run.py` no longer calls the retained `get_cli_run_orchestration_service()` singleton from first-party helper wrappers; wrappers now build fresh orchestration services.
- Coverage config no longer omits `src/bioetl/**/__main__.py`; `reports/quality/module-coverage-inventory.json` reports `bioetl.__main__` as partially covered and `bioetl.interfaces.cli.__main__` as fully covered.
- `report-dead-code-inventory --check`, `report-compatibility-importer-census --check`, and `report-module-coverage --check` passed; GitHub issues #5268 and #5261 were closed as completed.
