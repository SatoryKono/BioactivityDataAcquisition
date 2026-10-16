# Grafana security/UI candidate evidence — 2026-10-03

Issues: #11888, #11889, #11895. Status: BLOCKED; this evidence does not authorize closure or production rollout.

The candidate is based on main 1a3cb433b3e02f5cf09d796627a6f07e75c53e8e and pinned Grafana 6193dc03311b631b9727b560d24369e683dc396e. acceptance-summary.json binds the patches, locks, dashboard JSON and plugin bundles. The shared Grafana host was not replaced.

Verified locally:
- 292 focused Python tests, zero failures/errors/skips; focused-tests-summary.json.
- Full docs verify and Ruff on the five touched Python files; five dashboard generator checks.
- Scenes: 9 real tests; SelectorShell: 12 real tests; typecheck, lint, Windows production module builds. Their gate receipts preserve failing audits.
- Bridge: eight tests, typecheck, zero audit findings and packed archive/source parity.
- Patched upstream Canvas: two query failure/recovery integration tests passed; 37 other tests were outside that focused filter. Production Grafana and Swagger compilers both completed with zero errors and two warnings each.
- Real browser: SELECT RUN, UNKNOWN, saved-run excluded 14%, TREE_MISSING fully visible in a 1024×768 full dashboard, a real datasource connection failure rendered QUERY ERROR, then successful recovery. Six Scenes routes and link/Back/Forward navigation passed.

Remaining acceptance:
- Both plugin audits contain 31 High package entries, one unique braces advisory GHSA-vfj7-8cjw-p6xm. The original Router advisories are absent from these checked dependency graphs. An unsuppressed failing audit is not PASS.
- CI jobs on the checked main SHA did not start because of an account billing lock. Exact candidate SHA CI still needs successful execution.
- Baseline governance fails: catalog 337 active scripts against cap 336; composition_bootstrap_runtime has one file at least 250 LOC against budget zero. Allowances were not increased.
- SSR assessment is explicitly bounded to two pinned source files; host-wide constructor injection rejection and malicious navigation runtime fixtures remain pending.
- Selector context for the copied saved pipeline report lacks a matching control-plane manifest. No successful context was fabricated.
- Complete image delivery, source/runtime parity, backup/rollback, SBOM and post-merge acceptance remain pending. Local build overlays do not constitute a shipped host image.
- A Proof-or-Stop done/ready_to_merge claim must remain STOP while mandatory receipts fail. Local digest-only evidence cannot establish full-trust merge acceptance.

Screenshots are actual browser captures; they are not renders inferred from JSON or HTTP status. Private provisioning, credentials, local PIDs, copied run reports and large build outputs are intentionally excluded from publication.

Publication constraint: GitHub rejected the workflow write because the existing root-env tokens lack workflow scope. The checked workflow change is preserved in workflow-canvas-acceptance.patch; it must be applied with an already authorized workflow-capable credential before acceptance. The original local commit b8d5b70c53 remains in the reflog and an ignored patch backup.
