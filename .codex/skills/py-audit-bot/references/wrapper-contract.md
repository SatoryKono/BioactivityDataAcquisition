# BioETL Wrapper Skill Contract

Use this contract for thin BioETL profile and maintenance wrapper skills. Keep
profile-specific facts in each `SKILL.md`; keep shared runtime behavior here.

## Required Entry Contract

Every wrapper skill must state:

- trigger scope: when the wrapper is the right entrypoint
- canonical profile or workflow file
- task-tier-selected memory loop
- expected output artifact or final report shape
- validation command family
- fallback behavior when the profile, tool, or environment is unavailable

## Standard Workflow

1. Resolve scope and confirm the wrapper is the right entrypoint.
1. Select context through the `AGENTS.md` Required AI Context table, the single
   task-class matrix. V1 memory retrieval is optional; V2 uses the matching
   profile/skill and required pre-task; V3/V4 retain the full package and
   required pre-task. Hash-only work uses `BIOETL_AI_MEMORY_MODE=off`.
1. Reuse already-read current sources; re-read on content change, expanded scope,
   or conflicting evidence. A source list is navigation, not a mandatory dump.
1. Select memory mode within user authority. For selected pre-task under a strict
   ban on file changes, use read-only with `--skip-refresh-if-missing --skip-session-note` and set
   `PYTHONDONTWRITEBYTECODE=1` before starting Python (direct or wrapper invocation);
   do not rebuild even temporary artifacts. Report missing retrieval as DEGRADED
   and verify claims against source; never downgrade a V3/V4 task to skip checks.
1. Read the primary profile or workflow file named by the wrapper.
1. Use repo search to find related tests, docs, configs, contracts, mirrors,
   evidence, and validation gates.
1. Produce the wrapper-specific output.
1. Run the smallest sufficient validation set for the touched surface.
1. Run `python -m memory.tooling.workflow post-task ...` only in authorized
   `read-write` memory mode. In `off` or `read-only` mode, skip post-task and
   session-note creation; report the selected mode in the closeout.

## Output Requirements

The closeout must include:

- scope handled
- files or surfaces inspected/changed
- validation commands and outcomes
- skipped checks with exact follow-up commands
- memory post-task status
- whether docs mirrors were synced when runtime guidance changed

## Fallback Rules

- If the primary profile file is missing, stop using the wrapper and report a
  runtime drift finding.
- If required tools are unavailable, continue only with a clearly equivalent
  local command or mark the validation as skipped with a reason.
- If the task would increase technical-debt budgets, stop and report the
  governance conflict.

