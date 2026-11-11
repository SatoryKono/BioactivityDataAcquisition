# BioETL Wrapper Skill Contract

Use this contract for thin BioETL profile and maintenance wrapper skills. Keep
profile-specific facts in each `SKILL.md`; keep shared runtime behavior here.

## Required Entry Contract

Every wrapper skill must state:

- trigger scope: when the wrapper is the right entrypoint
- canonical profile or workflow file
- required memory loop
- expected output artifact or final report shape
- validation command family
- fallback behavior when the profile, tool, or environment is unavailable

## Standard Workflow

1. Resolve scope and confirm the wrapper is the right entrypoint.
1. Apply `AGENTS.md` Instruction Scope and Required AI Context; read only
   the normative/memory package selected by that task tier.
1. Run `python -m memory.tooling.workflow pre-task ...` when the root tier
   requires it. V1 memory is read-only optional; hash-only work uses
   `BIOETL_AI_MEMORY_MODE=off`. This wrapper cannot broaden those obligations.
   Strict read-only tasks must not refresh repository files implicitly.
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

