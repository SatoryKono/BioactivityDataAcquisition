______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-13'

______________________________________________________________________

# Branch hygiene wave

## Trigger

Run when local worktrees or branches exceed the budget (worktrees > 25, branches
> 60), before long-running agent campaigns, or weekly as routine maintenance.
Do not run during active release work — the wave deletes idle agent artifacts.

## Impact

Execution can remove local branch names and clean idle worktrees, or move
unregistered directories into quarantine. Review every candidate with its owner;
this procedure does not authorize removing another running agent's work.

## Preconditions

Keep a full checkout inside the governed `D:\github` workspace. Resolve source
and quarantine paths before acting; retain foreign hooks and machine-local files.
Do not proceed when GitHub PR state, worktree status or complete archives cannot
be verified. This is a manual maintenance utility, not an automatic runtime job.

## Tool

[`scripts/engineering/repo/branch_hygiene.py`](../../../scripts/engineering/repo/branch_hygiene.py)

- `classify` — scans worktrees, on-disk orphans, root clutter (`D:\github`),
  and local branches; writes `classification.json` + summary. Does not change Git state; writes only the requested report.
- `apply` — executes the safe classes below and writes `apply-actions.json`.
  Requires `--out <classification-dir>`; defaults to a no-change preview.
  Actual mutations require `--execute`. Re-classification always runs immediately
  before applying, with another state check before each worktree or branch action.

## Cutoffs (defaults, override with flags)

| Class | Condition | Action in `apply` |
| --- | --- | --- |
| Detached review tree | detached HEAD, idle > 2 days | `git worktree remove` (Git rejects dirty or locked trees) |
| Tree on gone branch | upstream gone, idle > 3 days | remove tree |
| Tree dirt | tracked or untracked changes | Complete WIP archive first; Git still refuses dirty trees until their owner clears them |
| Orphan / root clutter | dir not in `git worktree list` under the worktrees root or `D:\github` matching project prefixes | quarantine `.__trash_<yyyymmdd>/` |
| Trash older than 7 days | `.__trash_<yyyymmdd>` quarantine dir | hard delete (Access denied → reported as stuck) |
| Branch, PR finished | upstream gone, or `gh pr view` MERGED/CLOSED | `git branch -D` |
| Branch, no unique work | local-only and `git cherry main` empty | `git branch -D` |
| Branch, unique work stale | local-only, unique commits, tip > 3 days | `git branch -D` |

Every deleted branch tip is bundled first:
`git bundle create branches-backup-<ts>.bundle refs/heads/<name>...`.
Restore with `git fetch <bundle> refs/heads/<name>:refs/heads/<name>`.

## Never touched

- Locked worktrees (recovery state, `missing-wip-recovery.json`);
- the main checkout, trees/branches in active use (age under cutoffs);
- branches checked out in surviving worktrees, branches with live upstream and
  open PRs (including reused branch names), trees whose `git status` is unavailable.
- Trees containing `.env*`, symlinks or junctions; excluded inputs are never copied.
- Quarantine directories without a valid creation date or younger than the TTL.
- Any tree whose complete archive cannot be read or saved.

## Procedure

1. `python scripts/engineering/repo/branch_hygiene.py classify`
2. Review the summary table; inspect `classification.json` when unsure.
3. `python scripts/engineering/repo/branch_hygiene.py apply --out <dir>` previews only.
4. After reviewing exact candidates, use the same command with `--execute`.
5. Check `apply-actions.json` for kept, FAIL or stuck entries. Ask the tree owner
   to preserve and clear their changes; do not bypass Git protections or force deletion.

## Verification

Inspect `apply-actions.json` and the command exit code. Confirm every retained
candidate is still present, every deleted branch tip is included in its bundle,
and every WIP archive is readable. A failed archive or changed live state must
stop removal. Never treat a partial run as evidence that all work was cleaned.

## Rollback/Recovery

Restore a branch from its recorded bundle with
`git fetch <bundle> refs/heads/<name>:refs/heads/<name>` after checking the intended
name is free. Restore quarantined directories to the verified original path
only after confirming it is free and inside the governed workspace. Preserve the
archive and action ledger; ask the work owner to review archived changes before
applying them. Do not overwrite a newer worktree or reactivate a weaker helper.

## Post-incident

Retain the original classification, action ledger, bundles and WIP archives.
Record the exact failed operation and recovery outcome. Stop subsequent cleanup
until the owner verifies that their work is complete and recoverable.

## Compliance

Preserve `.env*`, unknown-date quarantine, active or locked trees and open PR
branches. Use the existing seven-day quarantine and age cutoffs; never bypass
Git protections, increase debt budgets or remove foreign hooks. Template and
local data changes require their own user authorization.

## Prevention

- Agent loops (`open-pr-*`, `mcp-*`, `nightly-*`, `pr-campaign-*`) must remove
  their own worktrees and branches after each run.
- Worktree names must carry the `-YYYYMMDD` suffix via
  [create_worktree.py](../../../scripts/engineering/repo/create_worktree.py).
- Do not run agents elevated: admin-owned pytest caches are the root cause of
  the Access denied stuck directories.
- Retain `branches-backup-*.bundle` and `wip-archive/` until their owner explicitly
  approves disposal; the tool does not purge these recovery originals.

## Evidence

- 2026-11-12 wave (ad-hoc scripts, superseded by this tool): worktrees ~85 → 54,
  branches 175 → 116, root clutter ~58 → 7 dirs. Report:
  `reports/local/branch-cleanup-20261112-105508/branch-cleanup-20261112-105508.md`.
