______________________________________________________________________

id: run-reports-and-governance-hash-refresh
title: Pipeline/workflow run reports and governance hash closeouts
kind: lesson
source_refs:

- docs/04-reference/reports/run-reports.md
- configs/contracts/reports/pipeline_run_report.v1.json
- configs/contracts/reports/workflow_run_report.v1.json
- configs/contracts/reports/reason_catalog.v1.yaml
- reports/quality/module-coverage-inventory.json
- docs/reports/evidence/project-package-topology/SUMMARY.md
- configs/quality/technical_debt_audit_registry.yaml
- configs/quality/test_telemetry_baseline.yaml
  confidence: curated
  last_verified: '2026-07-24T00:00:00Z'
  summary: Run reports are ledger/accounting projections; after src/bioetl changes refresh inventory, topology SUMMARY, debt evidence surface, and test-telemetry source_tree_sha256 together.

______________________________________________________________________

# Lesson

## Observation

- Operator post-run reports are **projections**, not a third SoT:
  stage accounting (ContextVar) + coarse RunResult metrics →
  `pipeline_run_report_v1` / `workflow_run_report_v1` under
  `reports/run-reports/`.
- Architecture closeout tests fail loudly when governance artifacts lag
  source-tree changes, especially:
  - `module-coverage-inventory.json` `source_tree_sha256`
  - `project-package-topology/SUMMARY.md` module count + hash
  - `technical_debt_audit_registry.yaml` `evidence_surface_sha256`
  - `test_telemetry_baseline.yaml` `source_tree_sha256` (tests tree digest)
- Evidence surface hash includes ordered content of listed quality JSON files;
  regenerating `debt-governance-gates.json` **after** pinning the hash makes
  the hash stale again — pin **after** the last evidence-path write.

## Reuse guidance

- After write-capable work under `src/bioetl/**`:
  1. `python -m scripts.engineering.qa.report_module_coverage_inventory --allow-missing-coverage-xml`
  2. refresh topology SUMMARY baseline to match inventory count/hash
  3. `python -m scripts.engineering.qa.report_debt_governance_gates`
  4. recompute `evidence_surface_sha256` and update registry + current audit MD
  5. if tests changed: update `configs/quality/test_telemetry_baseline.yaml`
     `source_tree_sha256` to
     `compute_test_telemetry_source_tree_sha256()` and sync
     `reports/test-telemetry/{slowest-tests,coverage-summary}.json`
- Contracts live under `configs/contracts/reports/`; operator guide at
  `docs/04-reference/reports/run-reports.md`.
- Never raise tech-debt budgets to clear these gates.
