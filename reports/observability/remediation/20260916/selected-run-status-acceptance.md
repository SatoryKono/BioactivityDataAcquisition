# Selected Run status acceptance — issues 10486–10489

## Implementation and scope

The exact-run endpoint reads persisted reports and content-addressed revisions. Six domains share one deterministic assessment. Execution outcome, checks, evidence completeness, present availability, live heartbeat and replay readiness are distinct. No wall clock or graph range is an input to terminal assessment. CURRENT retains the existing recording rules.

The source implementation was first committed as `5f1aedf5698`; subsequent changes move imports to module scope, keep the Postrun module below its existing size budget, and project the Trust summary from the same frozen snapshot. This report belongs to the accompanying commit/PR, not the production Docker image.

Candidate deployment: native health API on 127.0.0.1:8001, seven candidate Grafana dashboard UIDs prefixed `sr-`, folder `selected-run-10486`, datasource `selected-run-10486-http`. Production dashboard UIDs and the shared Docker main image were not replaced. The candidate API reads isolated acceptance reports.

## Real observations (2026-09-16)

| Run | Source | Execution | Saved assessment | Revision |
| --- | --- | --- | --- | --- |
| `3432761e-d4eb-511e-a62c-b186b301c758` | Actual historical chembl_assay workflow report, completed 2026-09-15 11:21:30 UTC; byte-identical copy of original report | SUCCESS | INCOMPLETE, legacy_no_snapshot | `dfc38e5badcc13a0d74a68dd6ed4f6ab26cb8fbad180bbc62a28750f40bb1b50` |
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

The updated Trust panel was verified after re-upload (candidate version 3): processing success, Trust ERROR, lineage_closure_gap and the saved completion time remained visible with the 1970 outside range. Trust to Overview navigation preserved the exact run and range. After a later recovery, empty selection was verified: all six domains display SELECT RUN and CURRENT remains UNKNOWN. Candidate dashboards version 4 were uploaded from the final generator. A deliberate outage of the candidate API produced UNKNOWN plus an explicit Infinity connection-refused error, with no stale OK. After restarting the API from the refactored source, the same saved revision and six-domain assessment returned. The 1280x900 screenshot clearly shows the complete summary and all six domains. This checks API outage/recovery, not the CURRENT metrics publisher recovery lifecycle.

## Remaining acceptance boundaries

This is local_single_host evidence, not a production/release acceptance or authorization to replay. The broader panel audit and visual acceptance remain with 10433/10440. The matrix proves backend response isolation, but does not independently simulate a delayed browser response or all CURRENT publisher recovery sequences.

Full docs verification (`python -m scripts.docs verify --skip-build`) passed after repairing six pre-existing broken archive-reference redirects, adding the missing navigation entries, and adding three missing module docstrings. No baseline waiver or budget increase was added. Broad bootstrap testing also reproduced two pre-existing failures on the original checkout (policy-loader cache and tracing-import ordering).

Do not close unfinished acceptance criteria merely because targeted tests pass. Production rollout, required CI disposition and the complete browser/error matrix must be recorded before final closure.

## Final refactor validation and external blockers

The refactor removes introduced size/complexity violations and import cycles, reuses the canonical clock seam, and moves repository-schema validation into integration tests. Application-core LOC is 23444 (baseline 23445); no debt budget increased. New module line coverage: workflow observations 94.00%, archive reports 92.45%, active diagnostics 93.55%, selected status API 87.06%. The focused measurement ran 147 tests with zero failures/skips. Six refactored modules passed mypy. Additional regression checks and the final source-bound architecture recheck are recorded in the follow-up PR evidence.

The initial full architecture scan ran 4751 cases: 4651 passed, 30 failed, 70 skipped. Its failures prompted the refactor and artifact regeneration; it is not a passing final acceptance result. Known baseline issues include two oversized unchanged modules, an unclassified lazy export, a direct clock call in an unchanged test, and a pre-existing bootstrap helper-ratio mismatch (0.338 baseline versus the older 0.330 residual bound; current ratio improved to 0.337). These are not waived.

PR Gate run 35081004469 for commit 7947bb75a4f540efb7651b9375a9c22d4bfa70c3 failed before executing steps: "The job was not started because your account is locked due to a billing issue." This is an external blocker to CI acceptance. Historical telemetry still attributes coverage to Tests run 34618841349 / db7cc9283e3fb49b0e5766489b7abacf9a775cd9; its coverage-verify succeeded, but that whole workflow failed governance. Rebinding its test-tree fingerprint does not claim a green CI run for this PR.

## Review remediation and repeated checks

The report root contract is now `pipeline_run_report_v2`; the original strict v1
schema is restored unchanged. Dual-version readers precede new writers. Rules v1
remain verifiable, while v2 records explicit skip-Gold as N/A. The change-specific
[ADR and migration/rollback procedure](../../../../docs/02-architecture/decisions/ADR-061-persisted-selected-run-assessment.md)
remain proposed pending acceptance.

Review regressions cover Pipeline=All, ambiguous exact-run IDs, workflow manifest
ownership, parent/child publication retry, foreign archive revisions, a second archive
version after late evidence, timezone-less ledger rejection and delegated Gold validation.
Malformed snapshot serialization returns false. Overview summary reuses its domain
response, so both show one revision and the first-paint HTTP budget remains unchanged.
All panel links, row caps, inventory counts and active panel docs are synchronized.

The expanded related suite ran 1095 cases: 1087 passed, 8 skipped, zero failures
(`reports/quality/selected-run-reviewed-final.xml`). Skips are retired dashboard
fixtures (5), POSIX bootstrap on Windows (2), and the opt-in live panel-fill gate (1).
A subsequent Gold preparation refactor preserves the existing zero-large-files
budget; its focused tests and final source-bound checks are recorded separately.
Twelve changed modules passed mypy, followed by both refactored Gold modules.

The 35-case code/architecture/metric check passed 33 and reproduced only the two
unchanged module-size baseline failures. No new import-cycle, complexity or size
violation was found. These local results do not clear the previously recorded CI
billing lock or the 93-expired-notes pre-test governance blocker.

Gold preparation refactor: 156 passed, zero skipped/failed
(`reports/quality/selected-run-gold-refactor.xml`). The family budget is again met:
zero application-core files at or above the governed threshold. Measured family LOC
is 23455 and helper ratio is 0.373; these are measurements, not increased budgets.
Docs verification passed, including links, drift, docstrings and cleanup inventory.

Remote main advanced during verification. Commit
`10f80c2404d4a74f572b35af66aa435b09969764` contains actual conflict markers
(`<<<<<<< HEAD` / `>>>>>>> codex/issue-10469-full-coverage-final`) in both
architecture-quality-scorecard.json and module-coverage-inventory.json. The local
artifacts have been regenerated cleanly. Debt gates now report 44 pass / 1 fail
for this remote-main blocker; this supersedes earlier green debt snapshots.


## Post-merge follow-up on main

PR #10490 was merged by the repository owner at 2026-09-16 11:31:35 UTC,
merge commit f69e37a45cd8be728d624ccf646cc428d09a8439. Follow-up fixes use a new
branch on that merge and preserve the independently merged changes. The earlier
remote-main conflict blocker was repaired by #10491/#10492; the refreshed debt
gates report 45 pass / 0 fail. This does not clear hosted CI or browser boundaries.

A third real cached-Bronze run, `45111bfa-3adb-5cc3-9258-3f5662f20b9f`,
completed at 2026-09-16T11:22:58.013543+00:00 from clean commit
`4f2cbb5b50842489621e752285156e5cc20690b2`. Its v2 revision is
`150a7ac3293200a95ae3814844b1ddade394a62b25251b941ca344c79547361e`.
Execution SUCCESS remains distinct from checks ERROR and evidence INCOMPLETE:
Control Plane records lineage_closure_gap; no Gold validation executed after the
single candidate was excluded. API restart preserved this exact revision.

Grafana datasource comparisons passed all 36 combinations: these three real runs,
concrete/All/glob-list pipeline selectors, and full/partial/outside/relative graph
ranges. Every summary field matched the exact API result. The machine evidence is
`reports/selected-run-acceptance/grafana-api-matrix-selector-final.json`.
Browser navigation exposed Grafana's `{unknown,chembl_assay}` All expansion on
Trust. The API now resolves only owners in that list; foreign or ambiguous IDs
remain unavailable/error. Trust displays the saved reason and completion with
the 1970 outside range; CURRENT remains separately UNKNOWN.

The first follow-up suite on main ran 1024 cases: 1016 passed, 8 skipped,
zero failures (`reports/quality/selected-run-main-followup-tests.xml`).
The eight skips retain the documented retired/POSIX/opt-in reasons.
Gold helper cleanup reduces application-core LOC to 23440, below the historical
23445 bound. V2 reuses immutable v1 field definitions through local JSON Schema
references; offline schema tests pass and config duplication returns to six
baseline clusters. No budget or exemption was increased.

The expanded saved-evidence tables now select operator fields instead of all
22 API fields. Long evidence values use the standard wrapped, paginated layout.
A final dashboard-only rerun and final proof bundle follow this UI adjustment.

Final dashboard-only rerun: 752 passed, 8 skipped, zero failures
(`reports/quality/selected-run-details-tests.xml`). Candidate version 7 was
visually checked at 1280x900: both domain pages, full Run ID, completion, rules
and revision are visible. A stale tab with ERR_NETWORK_CHANGED was replaced
with a fresh tab in the same browser. No browser security settings changed.


Latest review fixes also bind archived reports and every revision to manifest_id
when present, persist probe_fallback_reason, and record cancellation shutdown in
the run ledger and terminal audit before publishing its snapshot. The 414-case
measured suite passed with no skips or failures. Full coverage inventory refresh
includes all 2486 source modules. Main's additional coverage measurements and
regression tests from #10491/#10492 were preserved during the follow-up merge.
Final application-core LOC is 23443 (historical bound 23445), with no budget growth.
