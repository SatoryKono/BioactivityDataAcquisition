# LF1-28 Live Fixes Receipt Matrix

## Environment & Context
- **Pass ID:** LF1-28
- **Source SHA (exact):** 3f2808e6eeeb6570fdac3e125e7be16d6cc9d2f9
- **Deploy SHA:** NOT_VERIFIABLE (compose stack unavailable)
- **Environment:** compose (NOT production)
- **Time (UTC):** 2026-11-09T12:35:00Z
- **Status:** BLOCKED / NOT_VERIFIABLE
- **Reason:** `docker compose` execution is not permitted in the environment; backend is `blocked_backend_unavailable`.

## Separation of Verification States
- **Local Tests:** N/A
- **CI:** N/A
- **Deployment:** NOT_VERIFIABLE
- **Live:** NOT_VERIFIABLE

## L-01…L-09 Mapping
All live verification scenarios for L-01 through L-09 are `NOT_VERIFIABLE` because the live compose stack is unavailable. No actual evidence links exist.
- L-01: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-02: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-03: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-04: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-05: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-06: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-07: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-08: NOT_VERIFIABLE (blocked_backend_unavailable)
- L-09: NOT_VERIFIABLE (blocked_backend_unavailable)

## Reopened F-findings Mapping
All live F-findings are `NOT_VERIFIABLE` due to the backend being unavailable.
- F-findings: NOT_VERIFIABLE (blocked_backend_unavailable)

## UUID and Timestamp Coverages (B/C Pipeline)
While local unit tests verify the UUID resolution and timestamp handling (as shown in LF1-13), live coverage verification for two saved UUIDs, manifest/stages, UUID-branch timestamp, missing UUID, and historical UUID without manifest is `NOT_VERIFIABLE` due to the unavailability of the live stack.

## Required Matrix from Receipts
- **Source:** reports/observability/live-fixes-r6/LF1-22/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: N/A
  - Evidence: reports/observability/live-fixes-r6/LF1-22/machine_readable_receipt.json
- **Source:** reports/observability/live-fixes-r6/LF1-04/machine-readable-receipt.json
  - UID: grafana/dashboards/bioetl-incident-v1.json
  - Panel ID: 9701
  - UUID: N/A
  - Expected: N/A
  - Actual: PASS
  - Evidence: reports/observability/live-fixes-r6/LF1-04/machine-readable-receipt.json
- **Source:** reports/observability/live-fixes-r6/LF1-13/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: NOT_VERIFIABLE
  - Evidence: N/A (blocked)
- **Source:** reports/observability/live-fixes-r6/LF1-31/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: N/A
  - Evidence: reports/observability/live-fixes-r6/LF1-31/machine_readable_receipt.json
- **Source:** reports/observability/live-fixes-r6/LF1-06/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: NOT_VERIFIABLE
  - Evidence: N/A (blocked)
- **Source:** reports/observability/live-fixes-r6/LF1-25/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: N/A
  - Evidence: reports/observability/live-fixes-r6/LF1-25/machine_readable_receipt.json
- **Source:** reports/observability/live-fixes-r6/LF1-26/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: N/A
  - Evidence: reports/observability/live-fixes-r6/LF1-26/machine_readable_receipt.json
- **Source:** reports/observability/live-fixes-r6/LF1-24/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: N/A
  - Evidence: reports/observability/live-fixes-r6/LF1-24/machine_readable_receipt.json
- **Source:** reports/observability/live-fixes-r6/LF1-28/machine-readable-receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: NOT_VERIFIABLE
  - Evidence: N/A (blocked)
- **Source:** reports/observability/live-fixes-r6/LF1-30/machine_readable_receipt.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: N/A
  - Evidence: reports/observability/live-fixes-r6/LF1-30/machine_readable_receipt.json
- **Source:** reports/observability/live-fixes-r6/LF1-11/contract-evidence.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: 6da492a7-cc24-5adf-88f0-b9c2ad0e8df2
  - Expected: N/A
  - Actual: compatible
  - Evidence: reports/observability/live-fixes-r6/LF1-11/contract-evidence.json
- **Source:** reports/observability/live-fixes-r6/LF1-21/live-panel-audit.json
  - UID: N/A
  - Panel ID: N/A
  - UUID: N/A
  - Expected: N/A
  - Actual: N/A
  - Evidence: reports/observability/live-fixes-r6/LF1-21/live-panel-audit.json
