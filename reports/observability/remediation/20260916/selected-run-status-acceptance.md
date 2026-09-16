# Selected Run status acceptance — issues 10486–10489

## Implementation and scope

The exact-run endpoint reads persisted reports and content-addressed revisions. Six domains share one deterministic assessment. Execution outcome, checks, evidence completeness, present availability, live heartbeat and replay readiness are distinct. No wall clock or graph range is an input to terminal assessment. CURRENT retains the existing recording rules.

The source implementation was first committed as `5f1aedf5698`; subsequent changes move imports to module scope, keep the Postrun module below its existing size budget, and project the Trust summary from the same frozen snapshot. This report belongs to the accompanying commit/PR, not the production Docker image.

Candidate deployment: native health API on 127.0.0.1:8001, seven candidate Grafana dashboard UIDs prefixed `sr-`, folder `selected-run-10486`, datasource `selected-run-10486-http`. Production dashboard UIDs and the shared Docker main image were not replaced. The candidate API reads isolated acceptance reports.

## Real observations (2026-09-16)

| Run | Source | Execution | Saved assessment | Revision |
| --- | --- | --- | --- | --- |
| `3432761e-d4eb-511e-a62c-b186b301c758` | Actual historical chembl_assay workflow report, completed 2026-09-15 14:21:30 UTC; byte-identical copy of original report | SUCCESS | INCOMPLETE, legacy_no_snapshot | `dfc38e5badcc13a0d74a68dd6ed4f6ab26cb8fbad180bbc62a28750f40bb1b50` |
| `2c5ce6e4-c31d-56d9-bbaf-ed1c9175614b` | Actual one-record cached-Bronze execution from clean commit 5f1aedf5698, completed 2026-09-16 08:24:55 UTC | SUCCESS | ERROR; Control Plane lineage_closure_gap, Data Validation INCOMPLETE because no Gold schema check executed | `d2bad8ca2ac8add4c4cddbc479f6d3c0ef5caf9e162506ac628d75e6fa084caa` |

The new execution wrote one Bronze and one Silver record. Its single Gold candidate was excluded by the existing contract. This is not evidence of a successful Gold schema validation. Provider remote probing and Workflow are N/A for this standalone cached-Bronze run. DQ is OK. The recorded Control Plane failure is not hidden by processing success.

The new report survived termination and restart of the candidate API with the same revision and assessment. Both real runs were queried through Grafana's Infinity datasource for an entirely outside range, a relative six-hour range and an absolute run interval. All returned summary fields were identical per run. Machine evidence is retained locally in `reports/selected-run-acceptance/grafana-api-matrix.json`.

Browser observations: Overview rendered the old and new run identities and their distinct assessments. At 1280x900 and 1440x1000, new summary/domain values were legible. Changing the range to 1970-01-01 did not alter the selected result. Navigation to Trust retained Run ID and the absolute interval. CURRENT remained UNKNOWN and did not inherit historical Runtime OK. A transient ERR_NETWORK_CHANGED was resolved by creating a fresh tab in the same browser. An additional 768px mobile-width probe exposed pre-existing/reflow limitations and is not a mobile acceptance pass.

## Automated evidence

- Age/range matrix: 300, 899, 900, 901, 86400, 604800 seconds and four graph ranges.
- Exact identities, missing/empty selection, corrupt report/revision, lost revision, unsupported rules, legacy reports, success/failed/shutdown/cancelled/running.
- Atomic interrupted publication, idempotent finalization, retained late workflow revisions, concurrent observation isolation and late prior-request response identity.
- Actual cancellation through PipelineRunnerService persists a verified shutdown snapshot.
- Archive/restore identity, hashes and corruption detection.
- Final related unit/integration/domain architecture suite: 372 passed in 20.04 seconds, including the dry-run context-isolation regression, saved Trust projection, mandatory operator-readability and first-window no-scroll checks. JUnit: reports/quality/selected-run-tests.xml.
- Import-linter: six contracts kept, zero broken (workspace-local cache). The architecture wrapper's hard-coded /tmp cache is not writable in this Windows sandbox.
- Module inventory contains all 2484 modules, including the nine new modules. Newly added capture modules have measured coverage; existing measured rows were not lowered by partial coverage refreshes.
- Seven-dashboard generation is reproducible. No runtime agent/skill source was edited; runtime mirror synchronization is not applicable.

The updated Trust panel was verified after re-upload (candidate version 3): processing success, Trust ERROR, lineage_closure_gap and the saved completion time remained visible with the 1970 outside range. Trust to Overview navigation preserved the exact run and range. After recovery, Docker/Grafana became unavailable again during the empty-selection browser check; that browser scenario is not recorded as passed.

## Remaining acceptance boundaries

This is local_single_host evidence, not a production/release acceptance or authorization to replay. The broader panel audit and visual acceptance remain with 10433/10440. The matrix proves backend response isolation, but does not independently simulate a delayed browser response or all CURRENT publisher recovery sequences.

Full docs verification (`python -m scripts.docs verify --skip-build`) passed after repairing six pre-existing broken archive-reference redirects, adding the missing navigation entries, and adding three missing module docstrings. No baseline waiver or budget increase was added. Broad bootstrap testing also reproduced two pre-existing failures on the original checkout (policy-loader cache and tracing-import ordering).

Do not close unfinished acceptance criteria merely because targeted tests pass. Production rollout, required CI disposition and the complete browser/error matrix must be recorded before final closure.
