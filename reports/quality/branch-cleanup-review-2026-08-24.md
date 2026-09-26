# Branch cleanup review — 2026-08-24

**Remote:** `SatoryKono/BioactivityDataAcquisition`
**Cutoff:** `2026-08-10T13:55:44Z` (tips older than 14 days)
**Source-bound `origin/main`:** `725a1f96352ca5ae735ca70f8b76c049ebef90ae`
**Inventory:** `reports/quality/branch-cleanup-inventory-2026-08-24.json`
**Canonical dry-run:** `reports/quality/branch-cleanup-dry-run-2026-08-24.json`

## Summary

| Decision | Count | Action |
| --- | ---: | --- |
| Deleted after final tip/PR revalidation | 2 | Patch-equivalent to `main`; no unique patch remains |
| Tag first / owner decision | 6 | Preserve historical recovery points; five are protected |
| Consolidate / manual owner review | 32 | Closed-unmerged or orphan heads with unique patches |
| Keep | 20 | Unique patches and younger than the 30-day owner-review threshold |
| **Total older than cutoff** | **60** | No open PR head is selected for deletion |

The repository cleanup command was run without `--apply` for phases 1 and 2.
It planned zero actions, which is expected: the remaining candidates require
patch evidence or an explicit owner decision and are outside automatic cleanup.

## Deleted safe set

Both candidates had no open PR and exactly one commit ahead of `main`; bounded
patch comparison found zero unique patches and one equivalent patch.

- `codex/obs-audit-override-final` — `a03bacc27114fff59524e816c011e6de20c6e6b4`; PR #6313 closed unmerged.
- `fix/rf-004-final-green-closeout` — `39fbf2553e9c1db26c81e3133af58c45007976de`; PR #8523 merged, with an equivalent follow-up at the branch tip.

Immediately before deletion, both remote tips matched the recorded SHA, both
open-PR counts were zero, and neither branch was checked out in a worktree.
`git push origin --delete` then removed exactly these two refs.

## Post-cleanup verification

- Post inventory generated at `2026-08-24T18:07:32.613629+00:00`.
- Source `main` advanced concurrently to `47078f08929e12f8f4a08e1b9360a8c3b665dd02`.
- The source-bound post inventory contains 129 branches: 58 older than the
  cutoff and zero open PR heads among those 58.
- Pre/post comparison removed only the two reviewed refs and observed one
  concurrently added branch, `fix/dash-full-cycle`.
- The final phases 1/2 dry-run again planned zero automatic actions.
- `reports/quality/branch-cleanup-inventory-2026-08-24-post.json` and
  `reports/quality/branch-cleanup-dry-run-2026-08-24-post.json` contain the
  machine-readable post-cleanup evidence.

## Tag first / owner decision

Do not delete these branches before an annotated recovery tag is pushed and the
owner records an explicit `tag` or `delete` decision.

- `master_20260706` — `8ada26b201567cd63a96f928a1ada39381ca2701` (protected)
- `master_20260709` — `1ea76af7fa712cdae9ca59c94804ec1b620f223f` (protected)
- `master_20260717-2` — `4e5a3c62ad13f128e65464479ce0662fac675e80` (protected)
- `master_20260717-3` — `c9d96984a52ba2973623d46f1169fa896dfe7307` (protected)
- `master_20260720-1` — `e1ec130f26916d69e020f9058f5bd81491cf99ec` (protected)
- `master_20260806-1` — `ddc505e9dc41298270bcfe1473332dcb0cf0f11f` (dated recovery point; patch scan inconclusive)

## Consolidate / manual owner review

Each branch below retains at least one patch not proven equivalent to `main`.
Age or a closed-unmerged PR is not sufficient deletion evidence.

- `claude/architecture-review-refactor-r590e`
- `claude/audit-refactor-review-AOMLk`
- `claude/configure-setup-script-ei3rR`
- `codex/close-6449-6451`
- `consolidation-campaign-warp-setup-10891144980073298943`
- `devin/1777232744-add-wiki-pages`
- `devin/1777282924-fix-preexisting-ci-failures`
- `devin/1777793674-provider-health-l1-dashboard`
- `devin/1777795449-fix-novalue-copypaste`
- `feature/py-review-orchestrator-reports-16321445128357912329`
- `feature/semanticscholar-concurrent-batch-fetching-4855270832142738248`
- `fedor/review-reports-8398596340436730263`
- `fix-dashboard-errors-13249332482520436398`
- `fix-doi-tests-7308324249921386090`
- `fix-unused-get-resource-name-10073976247236922223`
- `fix/issue-7249-declarative-pytest-skips`
- `perf-async-metrics-server-1814537927827611323`
- `perf-crossref-fallback-9396241092094386141`
- `perf-dedup-10678796098399410738`
- `perf-list-deduplication-9066108671930857351`
- `perf-optimize-column-orderer-helpers-4503632652623781416`
- `performance-pubchem-batch-13441175631070016139`
- `review/hierarchical-code-review-13047481877801782444`
- `revert-6371-fix/remediation-f0adc0df-5c0cd8`
- `swarm-001-reports-2479479471661306667`
- `swarm-mock-reports-6166127889258653620`
- `test-ensure-registrations-3856219660841993164`
- `test-observability-resolution-15162923237048108216`
- `test-split-filter-ids-for-fallback-11889934895464523170`
- `test-swarm-reports-001-15088476181238200278`
- `test/audit-attr-shutdown-type-error-10768777861619467875`
- `testing-normalization-value-error-13101571771386145486`

## Keep until the 30-day review threshold

These heads are older than the requested 14-day cutoff but younger than the
repository policy's 30-day owner-review threshold. All retain unique patches.

- `fix/remediation-0b132bc9-064235`
- `fix/remediation-16b6cd19-0044cb`
- `fix/remediation-25ba3e25-a2dcc2`
- `fix/remediation-279e5785-8c4340`
- `fix/remediation-37e52770-0bcce3`
- `fix/remediation-38aac470-2008cb`
- `fix/remediation-3953b0e6-cdb717`
- `fix/remediation-6b0ffaaf-2d89c7`
- `fix/remediation-6c6b4fa1-888a22`
- `fix/remediation-6dd866e4-9b493c`
- `fix/remediation-8379d2f3-61207c`
- `fix/remediation-97d3a435-e84feb`
- `fix/remediation-a209659f-89cce7`
- `fix/remediation-a4bae638-8feec2`
- `fix/remediation-a71dfdf5-70acea`
- `fix/remediation-b0e5225a-7e66f4`
- `fix/remediation-c9360baa-7bbd37`
- `fix/remediation-ec14030a-a0a991`
- `fix/remediation-f70f2f12-dc9d31`
- `test-config-loader-filtering-12396991700714132425`

## Guardrails

- No branch is deleted solely because of age or count.
- Open PR heads, `main`, protected branches, and active worktrees are retained.
- Technical-debt budgets and `.env` files are not changed.
- The remediation branches target intermediate base branches; they require
  semantic consolidation before any later delete decision.
