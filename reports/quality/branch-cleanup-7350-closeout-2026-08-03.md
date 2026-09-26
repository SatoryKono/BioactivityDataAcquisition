# Branch cleanup closeout — issue #7350

**Date:** 2026-08-03  
**Operator:** Stream B (repo & test infrastructure)  
**Remote:** `SatoryKono/BioactivityDataAcquisition`

## Summary

| Metric | Value |
| --- | ---: |
| Branches before this closeout (API inventory) | 195 |
| Open PR head branches retained | 27 |
| Safe deletes (merged PR heads) | 9 |
| Safe deletes (closed unmerged bot/jules/bolt heads) | 62 |
| **Total remote branches deleted this session** | **71** |

## Policy applied

1. **Never delete** `main` or heads of **open** PRs.
2. **Auto-delete allowed** only when a remote branch is still present as the head of a **merged** PR, or as the head of a **closed unmerged** PR that matches ephemeral bot prefixes (`bolt-*`, `jules-*`, closed `add-py-test-swarm-*`, etc.).
3. **Deferred for manual review:** remaining closed-unmerged non-bot heads and orphan branches without PR association.

## Deleted: merged PR heads (9)

- `audit/ai-memory-5-cycles-r2` (PR #7284)
- `audit/ci-actions-3-cycles` (PR #7285)
- `bolt-optimize-collect-columns-13801393632892711024` (PR #4694)
- `codex/obs-program-6247-6268-latest` (PR #6301)
- `devin/1777217389-test-quality-improvements` (PR #3198)
- `fix-skill-creator-todo-3495655612695235095` (PR #4729)
- `jules-2845814033682854815-2165a7a7` (PR #4082)
- `master` (PR #2495)
- `test-extract-response-text-8991647446678882575` (PR #4732)

## Deleted: closed unmerged bot/ephemeral heads (62)

Prefixes: `add-py-test-swarm*`, `add-pytest-swarm*`, `agent-py-test-swarm*`, `bolt-*`, `bolt/*`, `jules-*`, `chore/test-swarm*`, `coderabbitai/*`.

Full list was produced from the 2026-08-03 classification inventory
(`review_closed_unmerged_pr_heads` filtered by prefix) and deleted via
`git push origin :refs/heads/<branch>` over SSH.

## Residual risk / follow-up

- Remaining remote branches include open Dependabot/Jules/agent PR heads (must wait for PR merge/close) and historical closed-unmerged non-bot branches.
- A second pass can target additional closed-unmerged heads after human review of the residual list.
- Local-only cleanup from 2026-07-31 (`reports/branch-cleanup-results-2026-07-31.md`) is superseded for remote scope by this closeout.

## Acceptance vs #7350

| Criterion | Status |
| --- | --- |
| Remove merged remote clutter | Done (9 + prior local work) |
| Remove stale experimental bot heads | Done (62) |
| Preserve active work / open PR heads | Done |
| Document residual | This closeout |

Issue #7350 can close when residual non-bot closed/orphan branches are either deleted after review or explicitly accepted as retained.
