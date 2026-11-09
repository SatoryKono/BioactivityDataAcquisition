# LF1-23: bioetl-dq-v2 Panels Status Check

- **Offline verification source SHA**: `e48c5d7531cf31a43723900d4918bd9f36a88e47`
- **UTC time of offline contract check**: 2026-11-09T05:49:46+00:00

## Overview
This report records the static inventory and an isolated check of the required 9403 audit contract.

## Checked Panels & Matrix
Based on `bioetl-dq-v2.json`, the status panels identified and verified are:
* **9406 (Review Selected Run Status)**: Table panel, mappings: `[]`, `UNKNOWN` noValue.
* **9403 (Inspect Processed Records)**: Table panel, mappings: `[]`, `SELECT RUN — no exact Run ID selected. Choose this run in Run Explorer.` noValue.
* **9460 (Inspect Selected Run Stages)**: Table panel, mappings: `[]`, `UNKNOWN` noValue.
* **9451 (Inspect Selected Run Domains)**: Table panel, mappings: `[]`, `UNKNOWN` noValue.

Panels 9481 and 9604 are not present in this dashboard (they exist in other scopes such as bioetl-overview-v2 and bioetl-incident-v1), so they are intentionally skipped.

## Offline contract and live verification

The isolated contract check used the corrected 9403 specification (`Inspect
Processed Records`, required HTTP panel). With an explicitly blocked backend
input, the helper returned `error/blocked_backend_unavailable`, as expected.
This is an offline result. The live matrix for these panels is `NOT_RUN` in
this verification, and the deployment SHA and live acceptance remain
`NOT_VERIFIABLE`.
