# 99-Archive Index

*Status: archive (non-nav) | Last updated: 2026-03-03*

----------------------------------------------------------------------

## Purpose

`docs/99-archive/` stores historical and superseded materials:
- retired plans and reports;
- superseded ADR variants;
- legacy dashboard and data-model notes.

These documents are preserved for traceability and historical context.

----------------------------------------------------------------------

## Usage Rules

1. Archive pages are not normative for current project behavior.
2. If archive content contradicts active docs, active docs in `docs/00-05` win.
3. Legacy paths/commands are allowed only as historical records.
4. New archive materials should include a short reason for archival/supersession.

----------------------------------------------------------------------

## Main Subsections

- `analysis/` — historical analytical notes.
- `audit/` — old audit packs and baselines.
- `dashboards-legacy/` — superseded dashboard docs.
- `data-model/` — historical model migration notes.
- `decisions/` — superseded decision records.
- `plans/` — archived planning artifacts.
- `reports/` — archived reports from earlier cycles.

----------------------------------------------------------------------

## Archive Catalog (Linked Artifacts)

### Root

- [CONFIG-GUIDE.md](CONFIG-GUIDE.md)
- [pyAuditBot.md](pyAuditBot.md)
- [refactoring-plan.md](refactoring-plan.md)
- [subagents_registry.md](subagents_registry.md)

### Analysis

- [analysis/data-normalization-comparison.md](analysis/data-normalization-comparison.md)
- [analysis/normalization-unification-plan.md](analysis/normalization-unification-plan.md)

### Audit

- [`audit/README.md`](audit/README.md) — historical audit baseline index
- `audit/02-test-baseline-2026-02-23.md` — historical path retained in audit notes

### Dashboards Legacy

- [dashboards-legacy/README.md](dashboards-legacy/README.md)
- [dashboards-legacy/BIOETL_DASHBOARD_COMPLETE.md](dashboards-legacy/BIOETL_DASHBOARD_COMPLETE.md)
- [dashboards-legacy/BIOETL_DASHBOARD_README.md](dashboards-legacy/BIOETL_DASHBOARD_README.md)
- [dashboards-legacy/BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md](dashboards-legacy/BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md)
- [dashboards-legacy/INFO_PANELS_ADDED.md](dashboards-legacy/INFO_PANELS_ADDED.md)
- [dashboards-legacy/TIMESTAMP_FIXED.md](dashboards-legacy/TIMESTAMP_FIXED.md)
- [dashboards-legacy/TIMESTAMP_WITH_VARIABLES_FIX.md](dashboards-legacy/TIMESTAMP_WITH_VARIABLES_FIX.md)

### Data Model

- [data-model/consolidated-refactoring-plan.md](data-model/consolidated-refactoring-plan.md)
- [data-model/field-catalog-source-pipelines.md](data-model/field-catalog-source-pipelines.md)
- [data-model/field-migration-checklist.md](data-model/field-migration-checklist.md)
- [data-model/field-naming-unification-matrix.md](data-model/field-naming-unification-matrix.md)
- [data-model/json-field-typing-inventory.md](data-model/json-field-typing-inventory.md)
- [data-model/pipeline-validation-matrix.md](data-model/pipeline-validation-matrix.md)
- [data-model/rf-naming-unification-plan.md](data-model/rf-naming-unification-plan.md)

### Decisions

- [decisions/ADR-030-api-offset-stability.md](decisions/ADR-030-api-offset-stability.md)
- [decisions/ADR-030-openalex-offset-stability.md](decisions/ADR-030-openalex-offset-stability.md)
- [decisions/ADR-030-publication-field-unification-SUPERSEDED.md](decisions/ADR-030-publication-field-unification-SUPERSEDED.md)
- [decisions/ADR-030-publication-field-unification.md](decisions/ADR-030-publication-field-unification.md)
- [decisions/ADR-031-full-scan-loading.md](decisions/ADR-031-full-scan-loading.md)

### Plans

- `plans/optimize-config-deduplication.md` — historical path no longer retained as a published archive page
- [plans/rf-fs-2026-03/README.md](plans/rf-fs-2026-03/README.md)

### Reports

- No markdown report artifacts are currently retained under `reports/` in this workspace snapshot.

----------------------------------------------------------------------

## Related Active Policies

- [Documentation Publication Policy](../00-project/governance/06-doc-publication-policy.md)
- [Documentation Navigation Policy](../00-project/governance/07-doc-nav-policy.md)
