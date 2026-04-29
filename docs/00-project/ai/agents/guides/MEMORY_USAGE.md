# MEMORY_USAGE.md

*Status: internal-published (AI runtime guidance)*

## Purpose

Define how AI agents should use BioETL memory surfaces without treating memory
as a replacement for runtime truth.

## Mandatory Read Order

1. `docs/00-project/ai/memory/agent-memory.md`
1. matching `docs/00-project/ai/memory/memory-py-*.md` file when a role-specific
   sheet exists
1. `src/memory/DAILY_WORKFLOW.md` for the canonical pre-task/post-task loop

## Required Workflow

1. Run `python -m memory.tooling.workflow pre-task ...` before substantial work.
1. Read retrieved context in the order `catalog -> graph -> rag -> source`.
1. Cross-check important claims with repo search, active docs, configs, tests,
   and accepted ADRs.
1. Run `python -m memory.tooling.workflow post-task ...` after the task.
1. Promote only durable lessons, incidents, or decisions.

## Conflict Priority

When memory disagrees with the repository, use this priority:

1. active code, configs, tests, workflows
1. `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, accepted ADRs
1. runtime maps and active runtime profiles in `.codex/**` or `.gemini/**`
1. `agent-memory.md` and `memory-py-*.md`
1. machine-readable memory artifacts such as `mcp-memory.json`

Memory is a navigation and evidence layer, not the source of truth for runtime
behavior or project rules.

## Stale Memory Handling

If a memory claim looks stale:

1. verify it against repository evidence
1. prefer repository truth over memory text
1. update the affected memory/doc surface or record the drift explicitly in the
   final report

## Expected Evidence Usage

- Use memory to find likely tests, docs, contracts, workflows, and ownership
  surfaces faster.
- Do not make behavior claims from memory alone when a file can be checked
  directly.

## Related Files

- `docs/00-project/ai/memory/README.md`
- `src/memory/DAILY_WORKFLOW.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
