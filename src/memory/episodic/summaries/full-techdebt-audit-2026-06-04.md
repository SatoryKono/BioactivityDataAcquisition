---
id: full-techdebt-audit-2026-06-04
title: Full technical debt and governance audit
task_id: full-techdebt-audit-2026-06-04
created_at: '2026-06-04T13:00:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
- configs/quality/compatibility_facade_inventory.yaml
- reports/quality/compatibility-importer-census.md
- reports/quality/hotspot-family-baseline.md
- src/bioetl/composition/bootstrap/cli/run_manifest.py
- src/bioetl/composition/runtime_builders/_run_manifest_publication_support.py
- src/bioetl/application/core/batch_writer.py
- src/bioetl/application/core/postrun/_service_collaborators.py
- docs/reports/evidence/exact-replay-boundary-decisions/SUMMARY.md
- reports/observability/runtime_cardinality_review.json
- reports/quality/test-governance-current.json
summary: Completed a source-first technical debt audit across governance, compatibility,
  layering, runtime-vs-CLI assembly, reproducibility, observability, contracts/configs,
  and test surfaces. Confirmed zero active layer violations, zero transition compatibility
  shims, zero contract/config blocking drift, and zero bronze fixture gaps; the live
  debt is concentrated in sanctioned public entrypoints, control-plane/bootstrap assembly
  duplication, legacy constructor-kwargs compatibility shims, composite exact-replay
  boundary limits, degraded live observability cardinality review, uncovered domain/infrastructure
  modules, and environment-limited-green CI semantics.
---

# Episodic summary

## Task

- Title: Full technical debt and governance audit

## Outcome

- Completed a source-first technical debt audit across governance, compatibility, layering, runtime-vs-CLI assembly, reproducibility, observability, contracts/configs, and test surfaces. Confirmed zero active layer violations, zero transition compatibility shims, zero contract/config blocking drift, and zero bronze fixture gaps; the live debt is concentrated in sanctioned public entrypoints, control-plane/bootstrap assembly duplication, legacy constructor-kwargs compatibility shims, composite exact-replay boundary limits, degraded live observability cardinality review, uncovered domain/infrastructure modules, and environment-limited-green CI semantics.

## Lessons learned

- Replace with durable follow-up if needed
