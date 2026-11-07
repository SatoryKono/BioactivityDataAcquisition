# LF1-01 Live Environment Snapshot Report

## 1. Environment Identity & Context
- **Base SHA:** `e54596f903e0b280e2b7e572a1c32ab831590b54` (current main)
- **Time (UTC):** `2026-11-06 18:48:37 UTC`
- **Environment Access:** The live monitoring stack failed to start via docker compose.
Error encountered:
```
failed to extract layer (application/vnd.docker.image.rootfs.diff.tar.gzip sha256:f01933c9ecefeeaabda6d58934c0fc92cf62b43ba50600c658db2474bf84bf61) to overlayfs as "extract-249568770-SuXn sha256:7ece827647fdd796982087e16218222f0c2606ce4e80695976f63a518f4b55b1": failed to convert whiteout file "usr/share/grafana/public/.wh.build": operation not permitted
```
Marked NOT_VERIFIABLE for live components per instructions.

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
