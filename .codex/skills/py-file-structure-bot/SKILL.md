______________________________________________________________________

## name: py-file-structure-bot description: Audit and optimize BioETL project file structure: inventory tree metrics, detect orphan/stale files, verify canonical layout compliance (hexagonal layers), analyze directory depth and naming drift, and generate actionable restructuring recommendations. Use when asked to audit file layout, find orphan files, check naming conventions in file paths, prepare a structure baseline before refactoring, or optimize directory organization.

# py-file-structure-bot

## Objective

Run the role-specific workflow as defined in the py-file-structure-bot profile.

## Source Of Truth

- Primary profile: `../../agents/py-file-structure-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role-specific memory: `../../../docs/00-project/ai/memory/memory-py-file-structure-bot.md`

## Workflow

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the current task.
1. Read `MEMORY_USAGE.md`, `agent-memory.md`, and `memory-py-file-structure-bot.md`.
   If the memory sheet does not yet exist, record that and continue with project
   memory plus repo search.
1. Read evidence packs before structural conclusions:
   - `docs/reports/evidence/project-file-structure/SUMMARY.md`
   - `docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md`
   - `docs/reports/evidence/project-package-topology/SUMMARY.md`
1. Open and follow `../../agents/py-file-structure-bot.md`.
1. Keep output artifacts and scope aligned with `../../agents/ORCHESTRATION.md`.
1. Respect BioETL architecture rules from `AGENTS.md` and project constraints.
1. After the audit, run `python -m memory.tooling.workflow post-task ...` and promote only durable findings.
