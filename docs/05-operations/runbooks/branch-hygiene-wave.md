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

## Workflow

1. `python scripts/engineering/repo/branch_hygiene.py classify`
2. Review the summary table; inspect `classification.json` when unsure.
3. `python scripts/engineering/repo/branch_hygiene.py apply --out <dir>` previews only.
4. After reviewing exact candidates, use the same command with `--execute`.
5. Check `apply-actions.json` for kept, FAIL or stuck entries. Ask the tree owner
   to preserve and clear their changes; do not bypass Git protections or force deletion.

## Prevention

- Agent loops (`open-pr-*`, `mcp-*`, `nightly-*`, `pr-campaign-*`) must remove
  their own worktrees and branches after each run.
- Worktree names must carry the `-YYYYMMDD` suffix via
  [create_worktree.py](../../../scripts/engineering/repo/create_worktree.py).
- Do not run agents elevated: admin-owned pytest caches are the root cause of
  the Access denied stuck directories.
- Retention: keep `branches-backup-*.bundle` and `wip-archive/` for 30 days,
  then delete (bundle is the only recovery path after `git gc`).

## Evidence

- 2026-11-12 wave (ad-hoc scripts, superseded by this tool): worktrees ~85 → 54,
  branches 175 → 116, root clutter ~58 → 7 dirs. Report:
  `reports/local/branch-cleanup-20261112-105508/branch-cleanup-20261112-105508.md`.
