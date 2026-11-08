# LF1-11 Execution Report

## Overview
This report confirms the successful execution of the `chembl_activity` pipeline for a limited backfill run and the publication of its observability bundle.

## Execution Details
- **Command:** `uv run python -m bioetl run --pipeline chembl_activity --run-type backfill --limit 10 --required-persistence-profile degraded_observable -y`
- **Exit Code:** 0
- **Source SHA (base):** `74cb6ccaa5dfe6fa97ec4e7ce468cc2d3c3992fd`
- **Deploy SHA (HEAD):** `99caf1aee6f214de0832eef2c8e0d51496cc811d`
- **Execution UTC:** 2026-11-07 23:22:46 UTC
- **Run ID:** `8ed593ce-3b75-56e0-a337-192953048582`
- **Manifest ID:** `6da492a7-cc24-5adf-88f0-b9c2ad0e8df2`
- **Status:** PASS

## Actual vs Expected
- **Expected:** Pipeline executes successfully and generates a complete manifest bundle in `data/output/control/run_manifest`.
- **Actual:** Pipeline executed successfully. The manifest, contract-evidence sidecar, and validation/inspection artifacts were generated and successfully copied to `reports/observability/live-fixes-r6/LF1-11/`.

## Dependencies
- **LF1-10 / #12806:** BLOCKED / NOT_VERIFIABLE (Artifacts unavailable in this environment).
- **LF1-05 / #12801:** BLOCKED / NOT_VERIFIABLE (Artifacts unavailable in this environment).

## Artifacts
1. `manifest.json` - Complete manifest bundle.
2. `contract-evidence.json` - Evidence of contract validation.
3. `manifest-validation.json` - Score validation output.
4. `manifest-show.txt` - Complete execution diagnostics and trace output.
