______________________________________________________________________

Version: 1.0.3
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-09-10'

______________________________________________________________________

# CI / GitHub Actions Workflow Map

The active PR/default-main provider is CircleCI `.circleci/config.yml`, workflow
`pr-gate`, with GitHub required context `ci/circleci: pr-gate-complete`.
The canonical applicability catalog is `configs/quality/github_required_checks.yaml`.
Its `deployment` block identifies CircleCI; retained `coordinator_workflow` and
`owner_workflow` fields describe the retained legacy Actions definitions.
The owner cancelled deletion in #11930; its status is not_planned.
GitHub Actions are disabled; billing restoration is out of scope.

The legacy inventory below contains 52 tracked workflow files, including 13
scheduled and 34 manual surfaces. These categories overlap. Retained YAML defines
the behavior to preserve; presence in the repository does not prove a running lane.
Optional CodeQL and inactive OpenCode stubs remain separate from required checks.

Production rulesets `main` (13643213) and `root-hygiene-required-check` (15730586)
are active as of 2026-10-05 after three consecutive successful main PR-gate
pipelines 218, 219 and 220: all 81 jobs passed on source
`a34558b918b56984a185c0e4956d735b43483780`. The main ruleset requires
`ci/circleci: pr-gate-complete`; the companion also requires
`ci/circleci: root-hygiene`. Both retain strict SHA freshness, main-only scope and
no bypass actors; API readback matched the submitted settings exactly.
The negative acceptance in isolated PR #11954 proved missing, failed, stale-SHA
and canceled CircleCI workflow results block merge (HTTP 405); its test ruleset
was disabled and the PR closed without merge. No App binding is claimed: this
CircleCI integration publishes legacy commit statuses without an App identity.

## CircleCI migration preparation (#11929 / #11931)

Acceptance evidence on 2026-10-05: CircleCI job
[2302](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2302)
produced a complete canonical 17-shard coverage manifest for source commit
`0eabda84e6716d5720132c4f3c3c3b6e5c00f953`: all shard exits and both
coverage gates were zero, with 99.70% line and 94.35% branch coverage.
The canonical telemetry export passed and its XML/JUnit digests were verified
before adoption. Module inventory uses the canonical additive, nonregressing
refresh; retained historical measurements are not new measurements from this run.
The overall job remained failed: architecture found two stale telemetry hashes
and one missing VCR catalog owner. Those artifacts were refreshed after the run;
this is not a claim of green main or successful Proof-or-Stop closeout.
The temporary coverage-producer branch filter was removed after this measurement;
normal architecture and test gates remain required for the next PR/main runs.
The repository permits squash merges only. Since a squash does not preserve the
branch producer as a main ancestor, final main adoption uses the isolated
`ci-lane=coverage-closeout` on `main`, then a separate baseline-only change.
This explicit lane runs the canonical 17-shard producer and Proof-or-Stop checks;
it is not part of a normal PR/default-main run. Do not rewrite source identity
to a squash SHA or weaken the ancestor guard to avoid this measurement.

The map above records the legacy Actions inventory; it is not evidence that
Actions are running. Actions are disabled and billing restoration is out of scope.
CodeQL is excluded from required checks; optional analysis and workflow retirement
remain separate decisions. The CircleCI default-branch matrix reads the canonical
required-check catalog instead of maintaining a second gate list.

The isolated preparation branch adds a `ci-lane` pipeline parameter with default
`pr-gate`. Setting `ci-lane=docs-kpi` selects only the Docs KPI workflow on `main`;
it does not start the PR gate, mutation testing or Docker publication. The job
preserves the existing KPI limits (target 120, hard limit 135, zero orphans),
freshness validation and report artifacts. Run it through a CircleCI pipeline
trigger after the config is integrated; `type: approval` is not a trigger.
Other prepared opt-in lanes are `memory-retention` (check-only), `port-contracts`
(property checks enabled by default through `include-hypothesis`),
`skills-consistency` (verify-only, no approved runtime sync), and
`github-settings-review` (requires the restricted `bioetl-github-read-only`
context). All are main-only and isolated from the normal PR workflow. Context
registration was completed on 2026-10-05: `bioetl-github-read-only` is restricted
to this project and `main`, excludes SSH and API config sources, and contains
`GITHUB_TOKEN`. Token permissions and job authentication still require run evidence.
Remaining event parity and external acceptance are pending.
The prepared `performance` lane preserves benchmark budgets and the five-sample
window, emits JUnit/observations/JSON/Markdown artifacts, and fails on missing,
empty or over-budget evidence. Main job 3365 passed 70 tests and all five budgets.
`bioetl-performance-nightly` is registered for 03:00–03:59 UTC daily. Its first
scheduled pipeline 272 failed the CrossRef median budget (0.479 ms against
0.4125 ms); a single diagnostic rerun on the same main SHA passed all 70 tests
with CrossRef at 0.268 ms. Both attempts are retained; scheduling is demonstrated,
but stable performance acceptance remains pending. The prepared evidence gate
requires all five registered benchmarks, rejects duplicate/missing/failed rows,
and records CPU identity, quota and throttling counters for diagnosis.
The prepared `replay-parity` lane retains the determinism, idempotency, composite
resume and independent determinism recheck, with nonempty checksum comparison
and replay artifacts. `memory-freshness` checks and publishes evidence without
GitHub write credentials; its schedule-failure notification and PR event parity
remain pending. Both lanes are opt-in and main-only.
On 2026-10-05, CircleCI confirmed creation of `bioetl-memory-freshness-weekly`:
branch `main`, `ci-lane=memory-freshness`, Monday, every month, one run during
05:00–05:59 UTC, Scheduled Actor. This replaces the legacy 05:17 minute with
an hourly window. Scheduled pipeline352/job6375 on main c644f2e4 passed all four freshness checks.
Failure-notification parity remains pending.

The main-only `e2e-replay` lane retains the five legacy replay commands:
three matrix runs, the ChEMBL activity smoke, the 15% skip SLO, zero recurrent
infra/code failures, and a final check of every pytest exit code. Execution is
bounded to 25 minutes and retains JUnit and diagnostic artifacts. This lane has
no credential context and cannot record new cassettes. Live/nightly credentials,
PR event parity still requires acceptance. Scheduled main replay acceptance is recorded below.

The prepared `mutation` lane additionally requires `pipeline.trigger.type=schedule`;
manual/API/PR triggers cannot start its four jobs. It preserves the existing four
targets and 70/60/60/60 score thresholds, fails on missing, empty or invalid stats,
and retains reports. `bioetl-mutation-weekly` was registered on 2026-10-05
with an initial Monday 13:00–13:59 UTC acceptance window on `main`. Scheduled
pipeline 187 started on main `95ca0a67f21a7055ad1b671f9ff57bd5ff39b1fb`;
the trigger was then restored to Sunday 00:00–00:59 UTC, one run per hour,
all months and Scheduling System attribution. Workflow-runner job 2885 passed
with 163/222 mutants killed (73.42%, threshold 60%); export-manifests job 2886
passed with 201/313 killed (64.22%, threshold 60%). Control-plane job 2888
failed its unchanged 60% gate: 4,020 killed, 5,673 survived, 3 timeouts
(41.49% under the existing formula), plus 2,787 mutants without tests.
The control-plane test selector is expanded to `tests/unit/application/` so
existing manifest/caller regression tests participate; source target and threshold
are unchanged. A fresh scheduled run is required. Domain job 2887 was interrupted before terminal statistics/report generation;
it is not accepted. Each job retains its own target report directory.

On 2026-10-05, `bioetl-docs-kpi-weekly` was registered for `main`,
`ci-lane=docs-kpi`, Monday 04:00–04:59 UTC, one run, all months, Scheduled Actor.
Manual pipeline 264/job 4453 passed on `303ced3b8e5c6fff04b061bfa5caf4b1674893af`
on 2026-10-06: 118 documents outside navigation (target 120, hard limit 135),
zero orphan candidates, no breaches. The JSON and Markdown artifacts were
downloaded and verified. Scheduled pipeline351/job6374 on main c644f2e4 repeated those passing KPI
results with three verified artifacts. Notification parity remains pending;
the legacy 04:30 minute is represented by an hourly window.
On 2026-10-05, the CircleCI UI confirmed creation of
`bioetl-memory-retention-weekly`: branch `main`, `ci-lane=memory-retention`,
Monday, every month, one run during 04:00–04:59 UTC, Scheduled Actor.
The hour-based trigger replaces the legacy 04:17 minute with a weekly window.
Scheduled pipeline356/job6383 on main c644f2e4 passed with apply=false,
zero candidates/removals and no policy violation; its artifact was verified.

The `consolidation` lane preserves the manual canonical source/test hash artifacts
with a ten-minute command limit. `branch-hygiene` preserves the report-only branch
inventory with a fifteen-minute limit and the `bioetl-github-read-only` context;
it does not delete branches. Both are opt-in and main-only. The branch inventory's
`bioetl-branch-hygiene-weekly` trigger was created in CircleCI on 2026-10-05:
`main`, `ci-lane=branch-hygiene`, Monday, every month, one run during
03:00–03:59 UTC, Scheduled Actor. This replaces the legacy 03:15 minute with
an hourly window. Authenticated scheduled pipeline357/job6382 on main c644f2e4 passed and
its read-only inventory was verified. PR branch-name event handling remains pending. The organization storage controls were verified on 2026-10-05: artifacts are
retained for thirty days, satisfying these lanes' fourteen-day minimum.

The `architecture-docs` lane preserves passport generation/validation, class-diagram
checks, dependency-map regeneration and the failing drift check, with JUnit and
generated-document artifacts. `provider-contract-drift` preserves replay-only
contract tests, xwalk/normalization checks and the canonical breaking-drift report.
Both are isolated main-only preparations with fifteen-minute command limits.
`bioetl-architecture-docs-nightly` and `bioetl-replay-parity-nightly` were registered
on 2026-10-05 for 02:00–02:59 UTC daily. All three nightly triggers use `main`,
Scheduling System, all months and one run per selected hour. Registration is
confirmed; scheduled execution and provider push/PR event parity still need
acceptance. Verified thirty-day artifact retention covers both lanes.

Independent phase-3 jobs may be prepared in parallel with phase A. Publishing
requires successful build/security/baseline gates and separate approval. Final
badges require the verified phase-B contract. Do not integrate this preparation
into the active coverage acceptance branch or run heavy jobs alongside its producer.

The prepared acceptance fixes use the architecture marker expression `not slow and
not benchmark and not memory`; pytest exit 5 remains a failure. Matrix workers
are capped at two, and the complete duplication scan uses a medium runner with
a 3072 MiB Node heap. Existing quality thresholds and scan paths are preserved.

### External phase-3 acceptance, 2026-10-05

The first four runs below used main `2d4507f595d03591c3db72b2aa554d7f41329ce3`.
Skills, performance and replay acceptance used main
`886a32e8bd71abf88616879b46390a716b13059c`.
Artifact digests and terminal job evidence were collected before recording results.

| Lane | CircleCI job | Result and remaining work |
| --- | --- | --- |
| Docs KPI | [2576](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2576) | SUCCESS; JSON, Markdown and summary artifacts; scheduled execution pending |
| Memory retention | [2604](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2604) | SUCCESS; check-only report, no pruning; scheduled execution pending |
| Memory freshness | [2605](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2605) | SUCCESS; report and contract checks; notifications and scheduled execution pending |
| Port contracts | [2606](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2606) | SUCCESS; 188 tests including Hypothesis, both JUnit artifacts; event parity pending |
| Skills consistency | [3364](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/3364) | SUCCESS; verify-only drift report has no drift, Junie parity passes; approved synchronization and event parity pending |
| Performance | [3365](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/3365) | SUCCESS; 70 tests, zero skips/failures; all five hotspot budgets pass, CrossRef median 0.243 ms; budgets unchanged; first scheduled pipeline 272 failed, diagnostic rerun 4566 passed; stability pending |
| Replay parity | [3366](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/3366) | SUCCESS; four runs and nine artifacts; independent determinism checksum inventories match; schedule pending |

On main `95ca0a67f21a7055ad1b671f9ff57bd5ff39b1fb`, GitHub settings job
[2773](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2773)
passed with authenticated read-only collection. Its report still records settings
drift, including disabled rulesets; collection success is not policy acceptance.
E2E replay job [2829](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/2829)
passed three 11-case matrix runs with zero skips/failures, plus ChEMBL smoke;
recurrent infrastructure and code failures were both zero. Nine artifacts were
collected with SHA256 digests.

Read-only branch hygiene job
[3084](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/3084)
passed on the same main SHA: 52 branches inventoried, `mode=dry-run`,
`deletion_applied=false`; its artifact digest was retained. No branch was deleted.
Provider-contract drift job
[3112](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/3112)
passed on the same main SHA: seven providers, twenty replay probes, zero skips,
zero warnings and zero breaking changes; report and JUnit digests were retained.
Architecture-docs job
[3113](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/3113)
passed on the same main SHA: 27 passport tests, no skips/failures, with generated
passports, dependency-map artifacts and retained JSON/JUnit digests.
Consolidation job [3170](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/3170)
passed on the same main SHA; both canonical source/test hash artifacts were retained.
The organization storage controls show thirty-day artifact retention and
fifteen-day workspace/cache retention; no settings were changed.

The opt-in `ci-lane=docker-baseline` runs only on `main` with the existing
`bioetl-github-read-only` context. It builds the exact source SHA, verifies the
runtime identity and health endpoint, preserves the canonical twelve-file
security baseline, and exports the scanned image with checksums only after the
strict vulnerability gate succeeds. Diagnostic artifacts are retained on failure.
This lane has no registry write credentials or publication step; protected
promotion, approval, SARIF transport and release acceptance remain pending.

Manual successes do not establish scheduler, notification or release acceptance.

## Migration disposition ledger (#11930 / #11931)

On 2026-10-06 the owner cancelled GitHub Actions deletion. Issue #11930 is
closed as `not planned`; all 52 workflow definitions and composite actions are
retained. Actions remain disabled. CircleCI implementation and acceptance under
#11931 continue independently. Retention does not establish functional parity,
authorize public OpenSSF channel retirement, or enable legacy workflows.

Current source inventory contains 52 workflows. Every row records the intended
replacement or retained local/disabled policy; "prepared" is not external acceptance.
No pending replacement authorizes deleting its source workflow. Scheduled entries
are UTC cron expressions from the source definitions, not registered CircleCI triggers.

| Source workflow | UTC schedule | Successor / disposition | Remaining acceptance |
| --- | --- | --- | --- |
| `architecture-docs-nightly.yml` | `15 2 * * *` | CircleCI architecture-docs | Scheduled pipeline 267/job 4482 SUCCESS on main 303ced3: 27 tests, 54 complete passports, zero blocking diagnostics; 118 artifacts independently downloaded and hashed |
| `architecture.yml` | `20 2 * * *` | CircleCI architecture-metrics | Main-only typed run-heavy=false fast baseline; run-heavy=true keeps heavy coverage 85% and Windows stress; daily 02 UTC window registered with run-heavy=true; Windows6874 passes2/2 without skips. Linux6873 on38433be0 completes36859 passed/177 skipped/1 failure (stale script inventory); canonical inventory repair is in PR11967. Full post-repair and scheduled heavy acceptance remain pending |
| `branch-hygiene.yml` | `15 3 * * 1` | CircleCI branch-hygiene inventory | Scheduled pipeline357/job6382 succeeds on main c644f2e4 with authenticated read-only branch inventory; Monday03UTC restored and verified. PR branch-name validation is part of the accepted main379 gate on38433be0; no branches deleted |
| `chembl-baseline-smoke.yml` | — | `dq-consistency` validates configurations; `arch-tests` and unit/integration groups cover all nine legacy test selectors; manual `ci-lane=pr-gate` | Nine test selectors and configuration steps accepted on main (DQ jobs 3488, 3505, 3554); legacy event parity acceptance pending |
| `codeql.yml` | `17 4 * * 1` | Retain disabled Actions definition | Not required; optional analysis lifecycle remains explicit |
| `coderabbit.yml` | — | Local CodeRabbit launcher | Retain local; external integration/event policy pending |
| `commit-lint.yml` | — | CircleCI commit-lint | Main gates 218–220 accepted; locked tooling refresh in #11955 merged as 303ced3 after all 27 CircleCI checks passed |
| `compiled-artifacts-block.yml` | — | CircleCI compiled-artifacts | Main gates 218–220 accepted; remaining legacy trigger parity must be checked for CircleCI acceptance |
| `consolidation-gates.yml` | — | CircleCI consolidation | Main run 3170 passes with both hash artifacts; artifact retention verified at 30 days |
| `contract-governance-fast-check.yml` | — | CircleCI schema-governance | Six canonical contract checks and diagnostics folded into the schema gate; any failure blocks the aggregate; main gates 218–220 accepted |
| `contract-tests.yml` | — | Local live-provider contract runner | Retain local-only policy #11190; preserve inputs and failure evidence |
| `dashboard-first-window-noscroll.yml` | — | CircleCI integration matrix | Nine static dashboard contract cases passed without skips in producer 4282 on 84524a90deab; no Grafana host is required for this source workflow. Retain legacy workflow-path assertions; browser/render acceptance remains separate |
| `dashboard-render-host.yml` | — | Local render host runner | Retain local host; Grafana/render secrets never on ordinary PR |
| `dependency-review.yml` | — | Dependency diff security review | Prepared combination: required uv lock check, every tracked npm manifest/lock parity check, all-lockfile OSV HIGH/CRITICAL gate and Docker security baseline. Remote acceptance pending; no advisory threshold reduction |
| `diagram-nightly.yml` | — | Diagram lint plus local full render | Keep disabled full-render surface; port only active checks |
| `docker.yml` | — | CircleCI docker-build plus opt-in main-only `docker-baseline` | Main eb265863 pipeline 310/job5420 SUCCESS: build/runtime/health and strict Trivy audit with zero findings; all15 artifacts downloaded,12 baseline checksums and scanned archive digest independently verified. Protected GHCR promotion and SARIF publication remain pending |
| `docs-kpi-weekly.yml` | `30 4 * * 1` | CircleCI docs-kpi | Scheduled pipeline351/job6374 succeeds on main c644f2e4:118 outside navigation,zero orphans,no breaches; three artifacts verified. Monday04UTC restored. The source docs-kpi workflow has no issue-notification job; no additional writer is required for its parity |
| `docs.yml` | — | CircleCI docs-governance | Prepared required gate; full docs/render parity pending |
| `duplication-complexity.yml` | — | CircleCI duplication | Prepared required gate; full scan thresholds preserved |
| `e2e-matrix-health.yml` | `30 2 * * *` | E2E replay and controlled live lanes | Scheduled pipeline353 on main c644f2e4 SUCCESS:full6377 passes159,prompt6376 passes52,matrix6378 passes3x11+1,live6379 passes11; zero errors/skips and14verified artifacts. Daily02UTC restored with run-live=true; required PR smoke accepted in pipeline362/job6470 (3x11+1, no skips); main event acceptance passed in pipeline371 on 8291d29c |
| `github-settings-quarterly-review.yml` | `23 6 1 1,4,7,10 *` | CircleCI github-settings-review | Scheduled pipeline355/job6381 succeeds on main c644f2e4; JSON/Markdown report verified and policy drift remains explicit. First-day Jan/Apr/Jul/Oct06UTC restored with Scheduling System attribution |
| `import-linter.yml` | — | CircleCI lint-arch and arch-tests | Prepared gates; full external architecture acceptance pending |
| `labeler.yml` | — | Retain disabled label maintenance | Preserve #10263/#11234; taxonomy reconciliation is required before any future trusted replacement |
| `memory-freshness.yml` | `17 5 * * 1` | CircleCI memory-freshness | Scheduled pipeline352/job6375 succeeds on main c644f2e4:all four freshness checks pass. Monday05UTC restored; required PR/main freshness checks accepted in main371. Scheduled failure issue-notification remains pending |
| `memory-retention.yml` | `17 4 * * 1` | CircleCI memory-retention | Scheduled pipeline356/job6383 succeeds on main c644f2e4:apply=false,zero candidates/removals,no policy violation. Monday04UTC restored; no pruning |
| `mutation-testing.yml` | `0 0 * * 0` | Scheduled-only mutation lane | Actual scheduled pipeline340 on main d9f5b026 SUCCESS, all four targets: domain6140 72.01%, control-plane6139 78.26%, workflow-runner6138 73.42%, export-manifests6141 64.22%. All eight artifacts and complete statistics independently verified. Large targets use large4CPU/8GB and four workers; small targets retain medium/one worker. Sunday00UTC restored and read back; full scope,60-minute timeout and70/60/60/60 thresholds unchanged |
| `nightly-replay-parity.yml` | `30 2 * * *` | CircleCI replay-parity | Main job 3366 passes four-run checksum parity; daily 02 UTC trigger accepted by scheduled pipeline 266/job 4481 on main 303ced3 (16 tests, no skips, repeated checksum files identical) |
| `no-partial-tree-commits.yml` | — | Full-tree guard in root governance | Integrated into root-hygiene; main jobs 3500, 3529, 3549 passed the full-tree guard alongside strict root checks |
| `opencode-pr-review.yml` | — | Retain disabled review stub policy | Do not activate unpinned installer or write paths |
| `opencode-triage.yml` | — | Retain disabled triage stub policy | Do not activate unpinned installer or write paths |
| `performance-nightly.yml` | `0 3 * * *` | CircleCI performance | Scheduled pipeline 272 on 303ced3: job 4565 failed CrossRef latency; diagnostic4566 and manual361 pass. Scheduled370/job6640 on main ba9c80e7 passes70 tests/0 skips and all five unchanged budgets; all six artifacts verified, daily03UTC restored. Prior failed observation retained; this is not five independent samples |
| `port-contracts.yml` | — | CircleCI port-contracts | Main run 2606 passed 188 tests including 24 Hypothesis cases; run 4425/pipeline 262 passed 164 tests with include-hypothesis=false on 303ced3; push/PR event parity pending |
| `pr-hygiene.yml` | — | Retain disabled PR maintenance | Preserve #10263; canonical 21-day draft/report-noise policy remains manual |
| `pr-required.yml` | — | CircleCI classify/pr-gate-complete | Main pipelines 218–220 pass all 81 jobs on a34558b918b5; both production rulesets active/read back; legacy owner references retained by the owner decision cancelling #11930 |
| `provider-contract-drift.yml` | — | CircleCI provider-contract-drift | Main run 3112 passes replay, matrix/xwalk and breaking-drift gates; push/PR parity pending; artifact retention verified at 30 days |
| `quality-debt-weekly.yml` | — | Retain disabled debt review policy | Do not activate job with existing if:false; local audits retained |
| `release.yml` | — | CircleCI release-validation plus protected promotion | Main pipeline339 on d9f5b026 SUCCESS, all five jobs: security6133, tests6136 (182 passed, no skips), build6134, install6135 and gate6137. Syft1.54.0 completes in1.556s; wheel/sdist/SPDX2.3 digests and source identity independently verified, install consumes the same archives. Signed provenance, TestPyPI/PyPI and release assets remain pending; published=false |
| `reusable-mermaid-setup.yml` | — | Shared pinned Mermaid tooling | Pending consumer migration; keep lockfile scanned by OSV |
| `reusable-setup.yml` | — | CircleCI setup-python-uv | Checksum-pinned uv 0.11.26 and explicit UV_PYTHON prepared; remote runtime/cache parity pending |
| `root-hygiene.yml` | — | CircleCI root-hygiene | Main full-tree/strict checks accepted; cleanup diagnostic artifacts and dedicated legacy regression selectors added for next acceptance; structure-audit port is blocked by six tracked Python paths outside allowed roots |
| `router-v7-bridge.yml` | — | Router bridge candidate acceptance | Manual main Router lane accepted in pipeline374; automatic PR/main path-filtered workflow prepared, remote event acceptance pending; managed host evidence remains separate |
| `schema-governance.yml` | — | CircleCI schema-governance | Prepared required gate; canonical generation/parity preserved |
| `scorecard.yml` | `30 7 * * 1` | CircleCI scorecard plus SARIF publication | Scheduled pipeline354/job6380 on main c644f2e4 succeeds with all18 checks; five artifacts and source/JSON/SARIF digests independently verified. Monday07UTC restored. sarif_uploaded=false and public_results_published=false; restricted writer credentials and publication acceptance pending; legacy public-results workflow retained |
| `security.yml` | — | CircleCI security-scans | Main security gates 218–220 passed; all tracked lockfiles remain scanned; SARIF publication parity pending |
| `semantic-governance.yml` | — | CircleCI `semantic-governance` | Seven canonical checks and four regression suites in the PR/main aggregate and an opt-in main lane; main gates 218–220 accepted |
| `skills-consistency.yml` | — | CircleCI skills-consistency | Main run 3364 passed static doctor, MCP wrapper pairs, mirror checks and drift=false artifact; typed `approve-runtime-sync=false` prepares a separate approval-gated report/patch job without push; approved no-op sync364/job6514 and required PR job6476 accepted; main event acceptance passed in pipeline371 on 8291d29c; artifact retention verified at 30 days |
| `stale.yml` | — | Retain disabled stale maintenance | Preserve #10263; legacy 14/7-day automation contradicts the canonical draft-only policy |
| `tests.yml` | — | CircleCI test-fast/test-integration | Main gates 218–220 accepted; historical producer 3363 completed 17 shards with overall STOP; test-tree changes require a new complete 17-shard producer, followed by another main producer after squash integration |
| `type-checking.yml` | — | CircleCI mypy | Strict mypy gate accepted in main pipelines 218–220 |
| `vacuum.yml` | — | Local maintenance command | Retain manual/local operation; no automatic destructive schedule |
| `validate-vendored-mermaid-assets.yml` | — | CircleCI docs-governance | Both legacy MkDocs asset existence checks folded into docs-governance and accepted in main371 on8291d29c |
| `zizmor.yml` | — | Remaining Actions YAML audit | Retained Actions audit: pinned zizmor1.29.0, unchanged high severity/confidence and config; required credential-free offline PR audit plus protected main online audit with read-only context. Offline PR audit accepted in pipeline378; protected online main audit6839 accepted on38433be0, with three downloaded and hashed artifacts. GitHub SARIF upload remains separate |

Local-only and intentionally disabled surfaces retain their operating policy;
disabled Actions stubs are not treated as missing credentials to be bypassed.
Triggers, contexts, approved publication and exact-SHA evidence remain CircleCI
acceptance gates; workflow deletion is no longer a completion criterion.

## How to use

1. Find the concern in the **active** table.
2. Open the workflow file for `on:`, jobs, and required secrets.
3. Prefer existing reusable/local scripts over inventing parallel gates.
4. Do not dispatch or wait on a `keep-disabled` lane; it does not run.

## Active workflow catalog

| Workflow file | Display name | Purpose (summary) |
| --- | --- | --- |
| `architecture.yml` | Architecture Metrics | Architecture debt gates, scorecard, hotspots |
| `branch-hygiene.yml` | Branch Hygiene | PR branch-name policy and periodic branch-cleanup inventory |
| `codeql.yml` | CodeQL | Advanced Python CodeQL SAST to GitHub code scanning; default setup stays off |
| `commit-lint.yml` | Commit Lint | Conventional commit message lint |
| `compiled-artifacts-block.yml` | Block Compiled Python Artifacts | Fail on committed bytecode/build junk; `pr-required.yml` owner (re-enabled #10263) |
| `consolidation-gates.yml` | consolidation-gates | Consolidation / cleanup governance gates |
| `dashboard-first-window-noscroll.yml` | Dashboard first-window no-scroll | First-window no-scroll gate for all seven shipped dashboard UIDs (DASH-FIT-004) |
| `dependency-review.yml` | Dependency review | PR-time HIGH/CRITICAL lockfile/manifest review |
| `docker.yml` | Docker Build & Compose Validation | Optional Docker contract (ADR-010 adjunct), reproducible Trivy/SBOM baseline, blocking CRITICAL+HIGH+MEDIUM image gate, and no-rebuild promotion of the scanned image |
| `docs.yml` | Docs & Diagrams | MkDocs, links, Mermaid lint, targeted ChEMBL render, drift; `pr-required.yml` owner (re-enabled #10263) |
| `duplication-complexity.yml` | Duplication and Complexity Checks | Dup/complexity quality gates |
| `e2e-matrix-health.yml` | E2E Matrix Health | End-to-end matrix health |
| `github-settings-quarterly-review.yml` | Quarterly GitHub Settings Review | Read-only quarterly GitHub settings review |
| `import-linter.yml` | Lint and Architecture Gates | import-linter + layer architecture |
| `no-partial-tree-commits.yml` | No partial-tree commits | Reject incomplete Git trees (#11709) |
| `opencode-pr-review.yml` | opencode-pr-review | Dispatch-only stub (#11012); remote OpenCode installer removed |
| `opencode-triage.yml` | opencode-triage | Dispatch-only stub (#11012); remote OpenCode installer removed |
| `pr-required.yml` | PR Gate Complete | Retained legacy coordinator; active CircleCI context `ci/circleci: pr-gate-complete` is enforced by rulesets 13643213 and 15730586 (#11928) |
| `root-hygiene.yml` | Root Hygiene | Root allowlist / clutter gates |
| `router-v7-bridge.yml` | Router 7 bridge candidate | Candidate plugin, frontend and image parity checks; managed host acceptance remains separate |
| `schema-governance.yml` | Schema Governance | Schema governance checks |
| `scorecard.yml` | OpenSSF Scorecard | Weekly non-blocking OpenSSF Scorecard baseline |
| `security.yml` | Security Scans | Secrets, pip-audit, Bandit, Gitleaks, OSV-Scanner |
| `tests.yml` | Tests | Primary unit/integration test matrix |
| `type-checking.yml` | Type Checking (Strict) | basedpyright / type gates |
| `zizmor.yml` | zizmor | High-confidence GitHub Actions YAML audit |

## Keep-disabled catalog (#10263)

These files exist in git but GitHub `state` is `disabled_manually`. They are
not operator routing targets. Reasons live in
[github-actions-workflows.md](../04-reference/github-actions-workflows.md).

| Workflow file | Display name | Decision |
| --- | --- | --- |
| `architecture-docs-nightly.yml` | Architecture Docs Nightly | `keep-disabled` |
| `chembl-baseline-smoke.yml` | ChemblBaseline Smoke | `keep-disabled` |
| `coderabbit.yml` | CodeRabbit | `keep-disabled` |
| `contract-governance-fast-check.yml` | Contract Governance Fast Check | `keep-disabled` |
| `contract-tests.yml` | Monthly Contract Tests | `keep-disabled` |
| `dashboard-render-host.yml` | Dashboard render release evidence | `keep-disabled` |
| `diagram-nightly.yml` | Diagram Nightly Regression | `keep-disabled` |
| `docs-kpi-weekly.yml` | Docs KPI Weekly | `keep-disabled` |
| `labeler.yml` | Labeler | `keep-disabled` |
| `memory-freshness.yml` | Memory freshness | `keep-disabled` |
| `memory-retention.yml` | Memory Retention Policy | `keep-disabled` |
| `mutation-testing.yml` | Mutation Testing | `keep-disabled` |
| `nightly-replay-parity.yml` | nightly-replay-parity | `keep-disabled` |
| `performance-nightly.yml` | Performance Nightly | `keep-disabled` |
| `port-contracts.yml` | Port Contract Tests | `keep-disabled` |
| `pr-hygiene.yml` | PR Hygiene | `keep-disabled` |
| `provider-contract-drift.yml` | Provider Contract Drift | `keep-disabled` |
| `quality-debt-weekly.yml` | Quality Debt Weekly | `keep-disabled` |
| `release.yml` | Release | `keep-disabled` |
| `reusable-mermaid-setup.yml` | [DEPRECATED] Reusable Mermaid setup | `keep-disabled` |
| `reusable-setup.yml` | [DEPRECATED] Reusable CI setup | `keep-disabled` |
| `semantic-governance.yml` | Semantic Pipeline Governance | `keep-disabled` |
| `skills-consistency.yml` | Skills Consistency | `keep-disabled` |
| `stale.yml` | Stale | `keep-disabled` |
| `vacuum.yml` | Weekly VACUUM | `keep-disabled` |
| `validate-vendored-mermaid-assets.yml` | Validate vendored Mermaid assets | `keep-disabled` |

## Docs-critical path

For documentation PRs, start with **`docs.yml`** (GitHub-`active` after #10263):

| Job (typical) | Role |
| --- | --- |
| docs-governance / validate-mkdocs | Strict MkDocs + excludes |
| validate-mermaid | ADR-040 Mermaid syntax and changed-source lint |
| check-diagram-drift | Source vs SVG on diagram PRs |
| link checks | `scripts.docs check-links` |

See also: [05-github-policy.md](../00-project/governance/05-github-policy.md),
[docs-verification.md](../03-guides/docs-verification.md),
[github-actions-workflows.md](../04-reference/github-actions-workflows.md).

## Maintenance

When adding a workflow:

1. Add a row here in the same PR (active vs keep-disabled).
2. Prefer extending an existing gate over a new always-on workflow.
3. Mark deprecated reusables clearly; do not reference them from new jobs.
4. Record GitHub live `state` and a keep-disabled or active decision in the
   canonical inventory.


The replay lane loads the
[`replay_parity_inputs.py` pytest plugin](../../scripts/engineering/ci/replay_parity_inputs.py)
with `-p scripts.engineering.ci.replay_parity_inputs` for the determinism suite only. It fixes input occurrence seeds, SystemClock,
checkpoint history nanoseconds and storage metadata duration counters. Async
scheduler/timeout clocks remain real. Both processes use the same working path;
their complete outputs are copied separately before byte-level comparison.
No output keys or files are filtered, normalized or rewritten, and within-run
occurrence/checkpoint uniqueness remains exercised by the existing tests.


The protected `docker-publish` successor is prepared as an opt-in main-only lane:
security baseline and exact scanned-image workspace, explicit approval, then
serialized publication through `bioetl-ghcr-publish`. That context was created
with project and main-only restrictions on 2026-10-05; registry credentials and
remote publication acceptance remain pending. The draft rejects incomplete
manifests, mismatched SHA/workflow/image identities, failed or missing approvals,
blocking vulnerabilities, changed SHA tags, and substituted signed predicates.
Local guard checks do not qualify as registry or attestation acceptance.


Architecture Metrics retains its manual fast default through the boolean
`run-heavy` parameter. The heavy profile preserves the legacy pytest selection,
85% coverage threshold and 25-minute execution limit; it uses a 16 GiB Linux
executor with four pytest workers and one numerical-library thread per worker.
Main pipeline347/job6307 reached the full 8 GiB limit during worker startup with
`-n auto`. Job6702 on main8291d29c also reached the 8 GiB limit with four
workers and lost one worker. The follow-up retains four workers on 16 GiB,
unsets BASH_ENV after step initialization so child shells preserve their PATH,
and separates JUnit from coverage XML; full heavy acceptance remains pending. Windows
job 6308 on f36e2c27 passed both stress tests with zero skips/errors; both artifacts
were downloaded and the JUnit independently verified. The Windows Server 2022
job installs checksum-pinned uv
0.11.26 and frozen Python 3.12 dependencies, runs both atomic lock stress tests,
and rejects missing, failed or skipped JUnit cases. The nightly trigger must set
`ci-lane=architecture-metrics` and `run-heavy=true`. The daily 02 UTC window is
registered; Linux heavy and scheduled execution acceptance remain pending.


The `scorecard` lane runs the complete default OpenSSF check set on main and
validates the resolved report commit against `CIRCLE_SHA1`. It deliberately does
not use `--commit=<sha>`, which excludes checks unsupported for historical
commits. The tool remains informational, preserving negative and unsupported
results in the JSON artifact. The pinned Linux v5.5.0 archive is verified against
its published release checksum. SARIF uses the upstream formatter and the pinned
policy from scorecard-action v2.4.4. Project-wide placeholder paths are URI-encoded
because GitHub strict validation rejects their raw spaces; finding content is
preserved. A local Linux transport acceptance on main `303ced3b` completed upload
`d500be9a-c0fe-11f1-8779-79f1b989bac0` with processing status `complete`.
CircleCI security-write credentials, remote SARIF upload, and public Scorecard
result publication remain separate unfinished requirements; the CI artifact
identity records both publication flags as false until its transports run.

The separate `scorecard-publish` lane prepares the GitHub SARIF transport:
read-only analysis, explicit approval, then a serialized writer using
`bioetl-security-events-write`. Its dedicated `SARIF_GITHUB_TOKEN` must have
repository Contents read and Code scanning alerts write permissions, restricted
to this repository; the context must enforce the same project/main/no-SSH/no-API-
config restrictions as the Docker publication context. The writer verifies the
producer job and approval through CircleCI, checks the source and report hashes,
rejects stale main, and waits for GitHub ingestion to complete. A saved upload ID
alone is not acceptance. This does not publish to the OpenSSF public results API;
that upstream transport requires GitHub Actions identity and remains unresolved
under the repository's Actions-disabled policy.

The `release-validation` lane prepares the non-publishing release path on main.
It preserves version/passport checks, wheel and sdist build, Twine validation,
Python 3.13 smoke/supply-chain tests, and the existing security-scans job. Wheel
installation runs in a fresh environment using hash-locked runtime dependencies
and the local wheel only; its import and CLI checks cannot resolve the editable
checkout. The aggregate records the successful same-workflow job numbers and
explicitly leaves `publication_ready` and `published` false. Syft 1.54.0 (archive SHA-256 pinned) inventories the safely expanded exact
distributions; empty catalogs fail, and the SBOM hash is bound to the build
identity and verified during installation. Signed provenance, protected
TestPyPI/PyPI promotion and release assets remain
required before release migration acceptance. This lane does not re-enable the
KEEP-DISABLED Actions release workflow.

The disabled label-maintenance and PR-maintenance workflows are retirement
candidates for their Actions transport, not activation requirements for CircleCI.
`labeler.yml` explicitly retains #10263/#11234 until live labels match the
canonical taxonomy. `stale.yml` and `pr-hygiene.yml` both have `if: false` and
remain disabled under `.github/PULL_REQUEST_HYGIENE.md`: only draft report-noise
PRs inactive for at least 21 days may qualify for closure. The legacy stale
workflow's 14-day stale/7-day close settings must not be copied into an active
replacement. Preserve `.github/labeler.yml`, the label taxonomy, and the manual
hygiene policy alongside the retained disabled workflow transports. Any future
write automation needs its own policy-aligned implementation and acceptance.

Publication implementations are supporting backends of the existing
`python -m scripts.engineering.ci` router: `publish-docker` and
`publish-scorecard`. CircleCI invokes these canonical commands. Their lifecycle
entries retain named ownership and a review date; their safety checks and tests
remain unchanged. This keeps the public script inventory within its existing
335-entry limit without raising the cap or retiring an unrelated command.

The inventory scanner treats `.circleci/` as a CI caller and recognizes pytest
`-p scripts...` plugin loading as well as `python -m scripts...` modules. This
preserves the real replay fixture ownership when Actions workflows are retired.
The current security job verifies the Gitleaks binary checksum and redacts
findings in logs. Git-history scan parity remains pending: directory scanning
alone does not replace the legacy commit-range scan. A local pinned Gitleaks
8.30.1 diagnostic covered 52 first-parent, non-merge commits from main
`303ced3b8e5c6fff04b061bfa5caf4b1674893af` through
`8f4ce4bc4a154ef77545ebc06e0188d400a3c0c4`: exit 0, zero findings,
unchanged rules and no OOM. This is evidence for that PR range only. The legacy
manual security entry can scan full history; its earlier resource failures and
the unimplemented CircleCI history transport remain open requirements.

Context boundary acceptance: [CircleCI pipeline 257](https://app.circleci.com/pipelines/github/SatoryKono/BioactivityDataAcquisition/257)
on disposable full-tree source `55a943181692bf8a891c13db5af489c6bfd1ea20`
requested `bioetl-github-read-only`, `bioetl-ghcr-publish`, and
`bioetl-security-events-write` from a non-`main` branch. All three jobs
(4366, 4368, 4367) returned `unauthorized` with zero duration; the probe never
reads or prints environment variables. This proves the tested non-main denial,
not successful publication or acceptance of every fork/trigger combination.


Manual E2E parity preserves the legacy 40-minute full-playback, 15-minute prompt,
and 30-minute strict-live limits. `ci-lane=e2e-replay` always runs the three smoke
reruns, full non-smoke replay, and prompt contracts on main. `run-live=true`
additionally selects `e2e-live`, with test mode false, strict health checks,
new-episode VCR mode and the unchanged 15% skip-rate SLO. The daily 02 UTC
schedule is registered with `run-live=true`; scheduled pipeline353 on main c644f2e4 passed full159,prompt52,
matrix3x11+1 and live11 without errors or skips. The ordinary PR workflow
now includes only the bounded three-run smoke job; full replay, prompts and
live checks remain in the explicit nightly/manual lane. Remote PR smoke
acceptance is recorded in pipeline362/job6470 (three runs of 11 tests plus one
smoke case, without skips or failures); main event acceptance is recorded in
pipeline371 on 8291d29c (all 32 jobs succeeded).

`ci-lane=skills-consistency` retains read-only checks. Setting the typed
`approve-runtime-sync=true` additionally exposes `runtime-sync-approval` and
then produces the canonical one-way sync report plus a binary patch. The job
runs Codex–Junie and skill mirror checks after sync, has a five-minute execution
limit, and never commits or pushes. Both the parameter and approval are required;
non-main branches cannot select this workflow. Approved no-op synchronization passed on main c644f2e4 in pipeline364/job6514: drift_before/drift_after and Devin issues are empty, Junie mirror parity passes. The JSON report is verified; no binary patch is produced when the tree is unchanged.


E2E smoke replay acceptance: [pipeline 261](https://app.circleci.com/pipelines/github/SatoryKono/BioactivityDataAcquisition/261),
job 4424 on main `303ced3b8e5c6fff04b061bfa5caf4b1674893af`, completed
successfully. All nine artifacts were retrieved: each of the three matrix
JUnit reports contains 11 passing cases and no skips; the representative ChEMBL
activity report contains one passing case. All three pytest exits are zero,
recurrent infra/code failures are zero, and the final skip rate is zero against
the unchanged 15% SLO. This accepts the existing smoke replay lane; the newly
prepared full replay, prompt, live and approved-sync jobs still need remote
acceptance after integration.


Router candidate preparation uses `ci-lane=router-bridge` on main only. The
bridge and two plugin jobs retain the legacy Node 24 commands, moderate npm
audit gate, committed archive and bundle digest checks, and 10/15-minute
limits. The dependent host job fetches the exact Grafana source commit, applies
the same three patches, runs the Canvas regression, builds the complete image
and validates filesystem/artifact parity within 45 minutes. Verified plugin
outputs cross jobs through the workspace; build/parity receipts and logs are
retained as artifacts. The Node 24.21.0 executor is digest-pinned. Its local
bridge acceptance passed all 26 tests, typecheck, build and vulnerability audit;
actual CircleCI plugin/host and automatic path-trigger acceptance remain pending.

OSV scan failures cannot reach the HIGH/CRITICAL severity policy: only exit 0
or 1 from the checksum-verified v2.6.0 binary is accepted as a completed scan.
Infrastructure, network, and no-package exits fail the job before the policy
reads a partial or empty report. Severity thresholds are unchanged.


Performance schedule diagnostic: [pipeline 272](https://app.circleci.com/pipelines/github/SatoryKono/BioactivityDataAcquisition/272)
on main `303ced3b8e5c6fff04b061bfa5caf4b1674893af` was genuinely scheduled.
Jobs 4565 and 4566 used the same source, tests, lockfile, Python 3.13.16 and
performance job configuration as the earlier successful job 3365. Four
artifacts from each attempt were downloaded and hashed. The failed JUnit
contains 69 passes and one failure; the rerun contains 70 passes and zero skips.
The first JSON omitted the failed CrossRef observation because budget assertions
run before observation recording; its four passing entries cannot qualify as
complete evidence. The stricter CircleCI evidence gate rejects that actual
partial report without changing benchmark thresholds. CPU variability is a
working diagnosis, not a proven code regression or a stability closeout.

Scheduled acceptance on 2026-10-06 used actual Scheduling System pipelines
351–357 on main `c644f2e4f347ed6642bc22b8fece33bbb829386d`. The temporary
acceptance hours were reverted; API readback matched all twelve original
timetables, parameters and actors. The quarterly review produced a report with
explicit drift/unavailable controls; successful collection does not certify
that all repository settings satisfy policy. Router main pipeline359 passed the
bridge and both plugin jobs; host6414 built the image but failed because the
verifier could not inspect the pinned base image in the Docker image store.
The candidate now explicitly pulls that same manifest-pinned base before
verification; BuildKit cache availability alone does not register its image ref.
Remote host acceptance succeeded in pipeline374 on main8291d29c:
bridge6703, scenes6704, selector6705 and host6706 all passed. All 66 artifacts
were downloaded and checksummed; automatic path-trigger acceptance is separate.

The ordinary `pr-gate` workflow now also requires the existing `port-contracts`,
`provider-contract-drift`, `memory-freshness`, `skills-consistency` and
`e2e-matrix-replay` jobs. These use no credential context and preserve their
existing commands, defaults, assertions and artifacts. The workflow dependency
DAG prevents `pr-gate-complete` from succeeding if any of them fails or is
cancelled. Running them for every triggered PR/default-branch pipeline is a
conservative superset of the retained Actions path filters. Nightly full/live,
mutation, performance, publication and approved runtime sync stay opt-in.
Remote PR and main event acceptance is still required for this wiring.


Acceptance continuation on 2026-10-06: PR11963 merged as main
`8291d29c236459f19344c581d1fb676819442240` after pipeline367 passed
32/32 jobs and exact-head Sonar/review/required-status checks. PR pipeline362
independently accepted the five supplemental jobs, including port contracts
164+24, provider replay48 and E2E smoke3x11+1, all without errors or skips.
Main event pipeline371 and heavy pipeline373 are the post-merge checks.

Actual scheduled performance pipeline370/job6640 on main
`ba9c80e7b8e1007e984851ea2b40aa6818df3645` passes70 tests without skips;
all five budget rows pass, with CrossRef median0.242484ms. All six artifacts
were downloaded and hashed. The schedule was restored to daily03UTC and API
readback matched all twelve original timetables, parameters and actors.
The earlier failing scheduled272 result remains part of the evidence; neither
thresholds nor the existing observation-window contract changed.

The next event-parity candidate validates PR head names using the exact retained
branch-hygiene patterns. Dependency review combines the existing required full
HIGH/CRITICAL OSV scan with Python lock validation and `npm ci --dry-run
--ignore-scripts` for every tracked npm lockfile. Seven real manifests pass;
a deliberately incomplete lockfile is rejected. Retained Actions receive a
checksum-pinned zizmor1.29.0 audit at the same high severity/confidence. PRs
receive no context; the additional online main audit uses only the already
restricted read-only context. SARIF artifact generation and SARIF publication
are separate; publication is still not accepted.


PR11966 merged as main `38433be0c32be9fe70a489173f153c773e214916`
after pipeline378 passed33/33 jobs, exact-head Sonar and resolved review.
The main online Actions audit6839 passed. Heavy acceptance continues in
pipeline380 with four workers,16GiB, unchanged scope and85% coverage threshold;
this launch does not establish acceptance.

The diagram event candidate restores the three active retained docs checks:
syntax with embedded diagrams and owned lint, targeted ChEMBL rendering with
artifact/visibility checks, and PR source-to-SVG byte drift. Canonical commands
and the Mermaid10.6.1 lockfile are retained; Node20 uses a digest-pinned browser
image. Tool installation is outside the artifact directory. Full-corpus nightly
rendering remains disabled by its existing policy. All three jobs gate PRs,
with path-based early exits; drift runs only for pull requests. Remote acceptance
is pending.

The Router event workflow applies the retained Router/plugin paths to PRs and
main pushes, including CI configuration changes for acceptance. It runs without
credential contexts, and skips unrelated changes before dependencies or Docker.
The host check requires bridge and both plugin jobs. Manual Router execution
continues to enforce main. Event acceptance is separate from pipeline374.
