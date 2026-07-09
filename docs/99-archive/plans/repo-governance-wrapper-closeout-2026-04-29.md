# Repo Governance Wrapper Closeout

*Status: supporting_context*
*Date: 2026-04-29*

## Scope

This note closes the bounded wrapper cleanup wave for
`scripts/engineering/repo/*` compatibility shells.

## Outcomes

Completed:

- added canonical router command
  `python -m scripts.engineering.repo cleanup-branch-candidates`
- retained
  `scripts/engineering/repo/cleanup_branch_candidates.sh`
  as the shell transport / compatibility facade
- removed governance-only wrappers:
  - `scripts/engineering/repo/split_testing_roadmap_issue.sh`
  - `scripts/engineering/repo/sync_docs_issues.sh`

## Evidence

- canonical router mapping lives in
  `scripts/engineering/repo/__main__.py`
- current wrapper status is recorded in
  `docs/plans/scripts-cli-wrapper-caller-matrix-2026-04-28.md`
- branch-cleanup router contract is covered by
  `tests/architecture/test_repo_cleanup_branch_router.py`

## Retained Surface

The remaining shell path in this cluster is:

- `scripts/engineering/repo/cleanup_branch_candidates.sh`

It is retained because:

- it now has a canonical Python route
- it still carries explicit shell-friendly workflow value
- deletion was not part of this wave

## Non-Goals

- This note does not reopen `ops/codex` launcher parity.
- This note does not change `scripts.ai.vibe` status.
- This note does not modify `scripts/ai/mcp/*_wrapper.*`.
