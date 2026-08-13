# Temporary Diagnostic Scripts

This directory contains temporary diagnostic scripts with bounded lifecycles.
Every executable below `scripts/temp/` (`.py`, `.sh`, `.ps1`, `.cmd`, `.bat`),
except the package marker `__init__.py`, MUST:

- be listed in this README
- `configs/quality/scripts_lifecycle_registry.json` (`decision: temporary_diagnostic`, with `review_by`)
- `configs/quality/scripts_inventory_manifest.json` (`status: temporary_diagnostic`)

## Scripts

### basedpyright Diagnostic Scripts (Review by: 2026-09-30)

These scripts support the typing debt campaign and should be consolidated into the canonical QA report surface or retired after the campaign closes.

- `report_basedpyright_error_snapshot.py` — shrink-only basedpyright product error snapshot
- `report_basedpyright_suppression_inventory.py` — basedpyright suppression inventory
- `report_basedpyright_tests_snapshot.py` — basedpyright test-snapshot for scripts/tests advisory
- `report_basedpyright_warning_snapshot.py` — basedpyright warning snapshot

### Dashboard audit campaign (Review by: 2026-09-30)

Bounded cycle-2 Grafana contour diagnostics. Prefer `reports/audit/` for dumps; remove or promote after campaign closeout.

- `layout_contour_audit_cycle2.py` — layout-contour companion diagnostic
- `panels_static_audit_cycle2.py` — static panel contour diagnostic
- `panels_contour_cycle2_notes.md` — operator notes for the cycle-2 panel contour run (not executable)

## Lifecycle Management

- **Expiration Date:** 2026-09-30
- **Owners:** `@bioetl-platform` (typing/merge/audit helpers), `@bioetl-observability` (dashboard contour)
- **Purpose:** Temporary utilities for campaign evidence collection
- **Next Step:** Consolidate into canonical QA/dashboard tooling or retire after campaign closes

## Usage

These scripts are not part of the standard development workflow and should only be used for specific diagnostic purposes during their campaigns.

## Cleanup

After each campaign closes (no later than 2026-09-30), these scripts should be:

1. Consolidated into the canonical QA / dashboard report surface, OR
2. Removed from the repository and dropped from lifecycle + inventory registries
