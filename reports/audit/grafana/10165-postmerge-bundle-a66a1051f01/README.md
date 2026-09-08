# RF-002 / #10165 — post-merge layout evidence

Source commit: `a66a1051f01a6443556f60c7e972fb9f1b4792ed`.

Implementation: [PR #10237](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/10237). Merged into main on 2026-09-08. These are new post-merge captures bound to the squash commit. All four profiles pass layout and provenance validation. See validation/review.md inside the archive for manual observations, test results, scope and the separately recorded local pretest failure.

Scope: 7 dashboards × dark/light × collapsed first viewport/expanded full. Physical and CSS viewport 1366×768, browser zoom 100%, DPR 1, kiosk=full. UTC 2026-09-08 14:00–15:00, refresh off; exact URLs and variables are in immutable manifests.

[Download complete evidence](evidence.zip) · [Archive SHA-256](evidence.zip.sha256) · [File hash ledger](file-hashes.json) · [DOM and provenance verdicts](layout-audit.json)

[Panel-level DOM measurements (CSV)](panel-dom.csv)

Archive SHA-256: `b04a9d459461d268c7ff63891aa0fe6095e0206efeeed8b2a5ca6614b287c11d`.

| Dashboard | Dark first | Light first | Dark expanded | Light expanded |
|---|---|---|---|---|
| bioetl-control-plane-v1 | [PNG](1366x768-dark/bioetl-control-plane-v1.png) | [PNG](1366x768-light/bioetl-control-plane-v1.png) | [PNG](1366x768-dark-full/bioetl-control-plane-v1.png) | [PNG](1366x768-light-full/bioetl-control-plane-v1.png) |
| bioetl-dq-v2 | [PNG](1366x768-dark/bioetl-dq-v2.png) | [PNG](1366x768-light/bioetl-dq-v2.png) | [PNG](1366x768-dark-full/bioetl-dq-v2.png) | [PNG](1366x768-light-full/bioetl-dq-v2.png) |
| bioetl-incident-v1 | [PNG](1366x768-dark/bioetl-incident-v1.png) | [PNG](1366x768-light/bioetl-incident-v1.png) | [PNG](1366x768-dark-full/bioetl-incident-v1.png) | [PNG](1366x768-light-full/bioetl-incident-v1.png) |
| bioetl-overview-v2 | [PNG](1366x768-dark/bioetl-overview-v2.png) | [PNG](1366x768-light/bioetl-overview-v2.png) | [PNG](1366x768-dark-full/bioetl-overview-v2.png) | [PNG](1366x768-light-full/bioetl-overview-v2.png) |
| bioetl-provider-health-v2 | [PNG](1366x768-dark/bioetl-provider-health-v2.png) | [PNG](1366x768-light/bioetl-provider-health-v2.png) | [PNG](1366x768-dark-full/bioetl-provider-health-v2.png) | [PNG](1366x768-light-full/bioetl-provider-health-v2.png) |
| bioetl-run-explorer-v1 | [PNG](1366x768-dark/bioetl-run-explorer-v1.png) | [PNG](1366x768-light/bioetl-run-explorer-v1.png) | [PNG](1366x768-dark-full/bioetl-run-explorer-v1.png) | [PNG](1366x768-light-full/bioetl-run-explorer-v1.png) |
| bioetl-runtime | [PNG](1366x768-dark/bioetl-runtime.png) | [PNG](1366x768-light/bioetl-runtime.png) | [PNG](1366x768-dark-full/bioetl-runtime.png) | [PNG](1366x768-light-full/bioetl-runtime.png) |

## Mechanical acceptance

Every root non-row panel with source y<18 has measured bounds, client/scroll dimensions and a verdict. The actual first-screen fold is 768 px. Expanded captures preserve the viewport and stitch original scroll tiles; all rows and descendant panels must be present. PNG hashes and before/loaded/after provisioned models are verified separately from geometry. No missing surface is treated as PASS.

Run Explorer row 3098 is checked against its rendered predecessor: the static reserved descendant band is not counted as a visible gap. The JSON report retains all boxes and row expansion records.

## Reproduce

Checkout the source commit, extract the archive, then run:

```powershell
python reproduce/10165_summarize.py captures a66a1051f01a6443556f60c7e972fb9f1b4792ed
```

Run from the repository root with its locked dependencies. The source commit must be available locally. Compare file-hashes.json and the archive hash before validation. Capture paths embedded in historical manifests identify the original workspace; the verifier resolves the downloaded attachments.

## Limits and verification

This evidence evaluates layout in the recorded live states. UNKNOWN, INCOMPLETE, SELECT RUN and VALID EMPTY keep their meanings. It does not certify other browser modes, 200% zoom, data correctness, all operator scenarios or general accessibility. See validation/ in the archive for exact test results, CI identity, runtime identity and any failed/skipped checks. Historical candidate captures are not relabelled.
