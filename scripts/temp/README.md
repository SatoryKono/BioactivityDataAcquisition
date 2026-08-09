# Temporary Diagnostic Scripts

This directory contains temporary diagnostic scripts with bounded lifecycles.

## Scripts

### basedpyright Diagnostic Scripts (Review by: 2026-09-30)

These scripts support the typing debt campaign and should be consolidated into the canonical QA report surface or retired after the campaign closes.

- `report_basedpyright_error_snapshot.py` - Generate shrink-only basedpyright product error snapshot
- `report_basedpyright_suppression_inventory.py` - Generate basedpyright suppression inventory
- `report_basedpyright_tests_snapshot.py` - Generate basedpyright test-snapshot for scripts/tests advisory
- `report_basedpyright_warning_snapshot.py` - Generate basedpyright warning snapshot

## Lifecycle Management

- **Expiration Date:** 2026-09-30
- **Owner:** @bioetl-platform
- **Purpose:** Temporary utilities for typing debt campaign evidence collection
- **Next Step:** Consolidate into canonical QA report surface or retire after campaign closes

## Usage

These scripts are not part of the standard development workflow and should only be used for specific diagnostic purposes during the typing debt campaign.

## Cleanup

After the typing debt campaign closes (2026-09-30), these scripts should be:
1. Consolidated into the canonical QA report surface, OR
2. Removed from the repository
