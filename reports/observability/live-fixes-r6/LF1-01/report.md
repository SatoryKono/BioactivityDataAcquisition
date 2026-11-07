# LF1-01 Live Environment Snapshot Report

## 1. Environment Identity & Context
- **Base SHA:** `e54596f903e0b280e2b7e572a1c32ab831590b54` (current main)
- **Time (UTC):** `2026-11-06 18:48:37 UTC`
- **Environment Access:** The live monitoring stack failed preflight (docker compose start error: Connection refused for both 3000 and 8000 ports on both `main` and `monitoring` stacks). Missing access to Grafana instance. Marked NOT_VERIFIABLE for live components per instructions.

## 2. Infrastructure Inventory (identity.json)
All values are marked as `NOT_VERIFIABLE` because access to the live environment Grafana/backend was not possible.

## 3. Dashboards Export
Exported 5 dashboard JSON files and generated SHA-256 hashes for each:
- `bioetl-control-plane-v1.json`
- `bioetl-overview-v2.json`
- `bioetl-dq-v2.json`
- `bioetl-incident-v1.json`
- `bioetl-run-explorer-v1.json`

## 4. Datasource Verification
Datasource querying is `NOT_VERIFIABLE` due to missing live environment access. Discrepancies with merged PRs (#12780, #12782, #12783, #12785) could not be checked against live deployment.

## 5. Panels Inventory
Total panels: 125.
Panels verified present in source dashboards:
- 9482 (canvas) - Present in `bioetl-overview-v2`
- 9481 (stat) - Present in `bioetl-overview-v2`
- 9604 (stat) - Present in `bioetl-overview-v2`

See `panels_inventory.json` for details. Expected states are marked `NOT_VERIFIABLE`.
