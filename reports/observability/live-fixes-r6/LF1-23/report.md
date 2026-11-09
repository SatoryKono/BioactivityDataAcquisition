# LF1-23: bioetl-dq-v2 Panels Status Check

- **Exact Source SHA**: 8b4ab5cb9e644e91977e2543b2f08ca9c1c1139f
- **UTC Time**: 2026-11-09T03:31:08Z

## Overview
This report verifies the correct semantic parsing of the bioetl-dq-v2 panels per the request requirements.

## Checked Panels & Matrix
Based on `bioetl-dq-v2.json`, the status panels identified and verified are:
* **9406 (Review Selected Run Status)**: Table panel, mappings: `[]`, `UNKNOWN` noValue.
* **9403 (Inspect Processed Records)**: Table panel, mappings: `[]`, `SELECT RUN — no exact Run ID selected. Choose this run in Run Explorer.` noValue.
* **9460 (Inspect Selected Run Stages)**: Table panel, mappings: `[]`, `UNKNOWN` noValue.
* **9451 (Inspect Selected Run Domains)**: Table panel, mappings: `[]`, `UNKNOWN` noValue.

Panels 9481 and 9604 are not present in this dashboard (they exist in other scopes such as bioetl-overview-v2 and bioetl-incident-v1), so they are intentionally skipped.

## Live Verification
The Docker compose backend environment is unavailable (`operation not permitted` / fallback allowed). During verification via `scripts.ops.observability.grafana.audit_live_grafana_panels`:

* 9406 returns `ok/blocked_backend_unavailable` (expected NOT_VERIFIABLE due to blocked env)
* 9403 returns `ok/blocked_backend_unavailable` (expected NOT_VERIFIABLE due to blocked env). This panel was temporarily throwing an error due to the title rename (`Processed Records` to `Inspect Processed Records`), which was corrected in the verification test script `audit_live_grafana_panels.py` to match the shipped static UI.
* 9460 returns `ok/blocked_backend_unavailable` (expected NOT_VERIFIABLE due to blocked env).
* 9451 (domain summary link, not live query itself).

All these status components safely record exact expected outcomes as blocked due to missing environment without artificially claiming success.
