# Live Grafana data-integrity audit — 2026-09-07

The live audit is **not globally PASS**. Exact requests and independent comparisons
were executed; remaining unavailable references are kept BLOCKED. Issues #10163
and #10164 are not interchangeable: the window fix is verified by engine cases,
while full numerical acceptance of the audit still requires the missing samples.

Endpoint: `http://127.0.0.1:3000`, Grafana **12.0.0**, bootstrap **full**.
Datasources: `prometheus` → `http://prometheus:9090`; `bioetl-ops-http` →
`http://bioetl:8000`. Report bind and expected/actual source identity align.
No service was started for capture and no `.env` or live metric data was changed.

Fixed normal windows: **2026-09-07 06:45–07:00 UTC** and
**2026-09-07 01:00–07:00 UTC**. Scrape-anomaly window:
**2026-09-07 07:05–07:10 UTC**; one failed scrape is recorded at 07:08:30.
The selected run is `chembl_assay` / `backfill` /
`a72f6bc0-d3cb-5e9f-bd7d-00763ec963c8`.
HTTP identities and disk indexes do not become range-filtered because Grafana
sends from/to. Source captures record their actual request time separately.

## Evidence and independence

Prometheus references fetch named source series and calculate max, grouping,
counter-reset-aware extrapolation, ranking, and counts in independent Python.
The source series/recording-rule definitions are still the same Prometheus
installation; this proves panel processing, not independent upstream collection.
HTTP accounting and index rows are compared to independently read, hashed
pipeline/workflow report files. The selected RunManifest and its 17 ledger events
are separately projected with source file hashes. Bronze=1000, Silver=1000,
Gold=983, exclusions=17 reconcile with zero integer error and balanced layers.

Transformation replay uses `@grafana/data@12.0.0` and the unmodified Prometheus
`result_transformer.ts` from Grafana tag v12.0.0. Typed field editors use identity
processors; Grafana's real matchers, reducers, units and value mappings execute.
This is numerical/configuration replay, not a browser screenshot or visual
acceptance. The library needs installing under `runtime/node_modules`; its code
is not vendored. The original transformer is also not vendored; its URL and SHA-256 are recorded in `grafana-transformer-source.json`. Original source:
[Grafana v12.0.0 result transformer](https://github.com/grafana/grafana/blob/v12.0.0/packages/grafana-prometheus/src/result_transformer.ts).

`*.json.gz` files are ordinary gzip-compressed JSON arrays; evidence fragments
after `#` name an object's `id`. `evidence-manifest.json` hashes every published
artifact. `captures.json.gz` includes exact request payloads, variable values,
intervalMs=30000, maxDataPoints=720, status, raw response schema and values.
`transformed.json.gz` records each presentation stage and separate synthetic
null/NaN/zero probes. No credentials or auth headers are saved.

## Confirmed findings

1. Runtime/205: rolling 15m conflicted with selected-window copy, and universe
   fallback returned 0 without failed-counter samples. Candidate uses instant
   `$__range` increase and UNKNOWN for absence. Ten promtool cases cover both
   15m and 6h, older failures, resets, measured zero, missing/single/stale samples
   and a foreign pipeline. Live failed-counter samples are absent: no nonzero
   live agreement is claimed.
2. Incident/2010: three table queries create Value #A/#B/#C, so sortBy(Value)
   misses its field. One short union restores Priority. Actual candidate rows
   match the independent source union. A separate synthetic Grafana 12 replay
   verifies provider/DQ priorities 2,2 precede runtime priorities 1,1,0.
3. Identity/3022 and Trust/9402: Cached Bronze is No although the selected
   manifest has cached_bronze.enabled=true. The candidate reads nested launch
   evidence and preserves explicit false precedence. HTTP/unit regressions pass;
   the currently deployed backend still needs a fresh post-deployment capture.

## Remaining acceptance limits

- DQ, stage-lag and freshness source samples are absent in the fixed live windows.
  UNKNOWN/empty behavior was observed; empty vs empty is not numeric PASS.
- Exact alert-history reconstruction from source range vectors cannot reproduce
  omitted stale markers; the retained request/raw frame proves execution only.
- Control-plane identity rows beyond the projected manifest/ledger anchors are
  not fully independently reconstructed. The cached-Bronze contradiction is
  explicit rather than hidden by a transport-only comparison.
- Pipeline index latest-ten membership and order match an independent sort of all
  persisted reports for the selected pipeline. For the workflow index, the 19
  dated rows match; membership of the remaining undated row is unproved. Its T7
  remains BLOCKED. See `index-membership-reconciliation.json`.
- Default/empty/invalid and multi/All selectors are recorded. Invalid HTTP scopes
  can return 400; this remains an explicit query error, not a healthy value.
- A single scrape outage and empty annotation API do not establish a known
  DQ/run anomaly dataset. No artificial production telemetry was inserted.

## Historical supplement

A seven-day availability search found earlier observed samples. Nine additional
exact requests were replayed and independently reconciled (all absolute errors
0; tolerance 1e-9). On 2026-09-04 at 09:30 UTC, panel 205 has a measured zero
for both 15m and 6h, including the candidate. Stage lag is measured zero on
2026-09-01 17:30–17:45 UTC. DQ state is 1 on 2026-09-03 21:01:40–21:16:40
and 0 on 21:31:40–21:46:40, for chembl_activity. These are additional fixed
windows, not substitutes for missing data in the initial scope. No freshness
samples were found in seven days; no nonzero failed counter was found.
`historical-*.json.gz` holds requests, frames, and independent calculations;
`extended-reference-availability.json.gz` records the exploratory search.

## Critical-panel matrix

Panels: {'PASS': 9, 'FAIL': 4, 'BLOCKED': 12, 'NA': 1}. All 26 critical panels have lineage and T1–T10 entries.

| Dashboard | Panel | Verdict | Independent reference |
| --- | ---: | --- | --- |
| bioetl-control-plane-v1 | 891 | PASS | PASS |
| bioetl-control-plane-v1 | 130 | PASS | PASS |
| bioetl-control-plane-v1 | 9402 | FAIL | FAIL |
| bioetl-control-plane-v1 | 9403 | BLOCKED | PASS |
| bioetl-control-plane-v1 | 9401 | PASS | PASS |
| bioetl-overview-v2 | 214 | PASS | PASS |
| bioetl-overview-v2 | 215 | BLOCKED | PASS |
| bioetl-overview-v2 | 1000 | NA | NA |
| bioetl-runtime | 9401 | PASS | PASS |
| bioetl-runtime | 205 | FAIL | FAIL |
| bioetl-runtime | 237 | PASS | PASS |
| bioetl-runtime | 9102 | PASS | PASS |
| bioetl-provider-health-v2 | 9101 | BLOCKED | PASS |
| bioetl-provider-health-v2 | 9103 | BLOCKED | NOT_VERIFIABLE |
| bioetl-dq-v2 | 9401 | PASS | PASS |
| bioetl-dq-v2 | 9101 | PASS | PASS |
| bioetl-dq-v2 | 9102 | BLOCKED | NOT_VERIFIABLE |
| bioetl-dq-v2 | 8 | BLOCKED | NOT_VERIFIABLE |
| bioetl-incident-v1 | 2010 | FAIL | FAIL |
| bioetl-incident-v1 | 2005 | BLOCKED | PASS |
| bioetl-incident-v1 | 2006 | BLOCKED | NOT_VERIFIABLE |
| bioetl-run-explorer-v1 | 3022 | FAIL | FAIL |
| bioetl-run-explorer-v1 | 3023 | BLOCKED | PASS |
| bioetl-run-explorer-v1 | 3010 | BLOCKED | PASS |
| bioetl-run-explorer-v1 | 3020 | BLOCKED | PASS |
| bioetl-run-explorer-v1 | 3011 | BLOCKED | PASS |

Full T1–T10 decisions and evidence IDs are in integrity-tests.json. Table-field null/NaN behavior remains BLOCKED unless independently established. These audit verdicts are distinct from CI validation of the fixes.

## Final per-scope coverage guard

The final candidate query requires at least two failed-counter samples for every
(pipeline, run_type) scope recorded by the selected-window universe. Five live
requests and independent raw-counter/universe calculations are retained in
`coverage-guard-captures.json.gz`, `coverage-guard-transformed.json.gz`, and
`coverage-guard-reconciliation.json.gz`. The two historical windows returned
measured zero (absolute error 0); the two initial windows and the historical
multi-scope selection correctly returned UNKNOWN (ABSENCE_MATCH, not numerical
PASS). The multi-scope request has backfill samples but no qualifying incremental
counter. These captures supersede the earlier candidate query for panel 205;
earlier captures remain versioned evidence of the intermediate query. This
supplement does not alter unresolved live backend, freshness, null/NaN, or
annotation acceptance gaps.

## Deployed and candidate verdict binding

The critical-panel matrix describes the captured deployed configuration and
backend. Runtime/205 and Incident/2010 remain FAIL there. Their original raw
requests and independent reconciliation show the failures. Candidate API replay
and engine tests prove the proposed corrections and are retained separately;
they do not replace live acceptance. `live_panel` is copied from the immutable
dashboard API capture. `candidate_panel` is bound to source commit
`36e26ee121a990707e565c63ba0a1970f5b274ca`. No deployment was performed.

## Historical helper source packaging

`capture_live.py.txt`, `check_rank_replay.py.txt`, and `reconcile.py.txt` are
inert source snapshots from the capture session, not maintained executable
repository tools. Their original bytes and SHA-256 digests are unchanged;
the manifest records each original filename. To inspect or replay a historical
helper, copy the snapshot into a separate working directory using its original
filename, review its machine-specific paths, and install the documented
dependencies first. The live snapshots and numerical verdicts are unchanged.
The initially published package remains available at commit
`191d4bf5e309ad21f460d0cb87f940441753a55e`; this publication corrects packaging.
