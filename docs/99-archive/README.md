# 99-Archive Index

*Status: archive (non-nav) | Last updated: 2026-03-26*

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

- `analysis/` — historical analytical notes; not retained as published pages in this workspace snapshot.
- `audit/` — old audit packs and baselines; not retained as published pages in this workspace snapshot.
- `dashboards-legacy/` — superseded dashboard docs; not retained as published pages in this workspace snapshot.
- `data-model/` — historical model migration notes; not retained as published pages in this workspace snapshot.
- `decisions/` — superseded decision records; not retained as published pages in this workspace snapshot.
- `plans/` — archived planning artifacts; retained only through references and summaries in the current snapshot.
- `reports/` — archived reports from earlier cycles; not retained as published pages in this workspace snapshot.

----------------------------------------------------------------------

## Archive Catalog (Linked Artifacts)

### Root

- [CONFIG-GUIDE.md](CONFIG-GUIDE.md)
- [dq-system-contract-implementation-summary.md](dq-system-contract-implementation-summary.md) — historical implementation summary moved from repository root
- [scripts-reorganization-phase1-plan.md](scripts-reorganization-phase1-plan.md) — historical planning artifact moved from repository root
- `pyAuditBot.md` — historical path no longer retained as a published archive page
- `refactoring-plan.md` — historical path no longer retained as a published archive page
- `subagents_registry.md` — historical path no longer retained as a published archive page

### Analysis

- `analysis/data-normalization-comparison.md` — historical path no longer retained as a published archive page
- `analysis/normalization-unification-plan.md` — historical path no longer retained as a published archive page

### Audit

- `audit/README.md` — historical audit baseline index path no longer retained as a published archive page
- `audit/02-test-baseline-2026-02-23.md` — historical path retained in audit notes

### Dashboards Legacy

- `dashboards-legacy/README.md` — historical path no longer retained as a published archive page
- `dashboards-legacy/BIOETL_DASHBOARD_COMPLETE.md` — historical path no longer retained as a published archive page
- `dashboards-legacy/BIOETL_DASHBOARD_README.md` — historical path no longer retained as a published archive page
- `dashboards-legacy/BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md` — historical path no longer retained as a published archive page
- `dashboards-legacy/INFO_PANELS_ADDED.md` — historical path no longer retained as a published archive page
- `dashboards-legacy/TIMESTAMP_FIXED.md` — historical path no longer retained as a published archive page
- `dashboards-legacy/TIMESTAMP_WITH_VARIABLES_FIX.md` — historical path no longer retained as a published archive page

### Data Model

- `data-model/consolidated-refactoring-plan.md` — historical path no longer retained as a published archive page
- `data-model/field-catalog-source-pipelines.md` — historical path no longer retained as a published archive page
- `data-model/field-migration-checklist.md` — historical path no longer retained as a published archive page
- `data-model/field-naming-unification-matrix.md` — historical path no longer retained as a published archive page
- `data-model/json-field-typing-inventory.md` — historical path no longer retained as a published archive page
- `data-model/pipeline-validation-matrix.md` — historical path no longer retained as a published archive page
- `data-model/rf-naming-unification-plan.md` — historical path no longer retained as a published archive page

### Decisions

- `decisions/ADR-030-api-offset-stability.md` — historical path no longer retained as a published archive page
- `decisions/ADR-030-openalex-offset-stability.md` — historical path no longer retained as a published archive page
- `decisions/ADR-030-publication-field-unification-SUPERSEDED.md` — historical path no longer retained as a published archive page
- `decisions/ADR-030-publication-field-unification.md` — historical path no longer retained as a published archive page
- `decisions/ADR-031-full-scan-loading.md` — historical path no longer retained as a published archive page

### Plans

- `plans/optimize-config-deduplication.md` — historical path no longer retained as a published archive page
- `plans/rf-fs-2026-03/README.md` — historical path no longer retained as a published archive page

### Reports

- No markdown report artifacts are currently retained under `reports/` in this workspace snapshot.

----------------------------------------------------------------------

## Related Active Policies

- [Documentation Publication Policy](../00-project/governance/06-doc-publication-policy.md)
- [Documentation Navigation Policy](../00-project/governance/07-doc-nav-policy.md)
