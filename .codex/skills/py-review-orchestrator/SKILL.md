---
name: "py-review-orchestrator"
description: "Execute BioETL hierarchical code review orchestration (L1/L2/L3) across sectors S1-S8 with delegated sub-reviews, scoring, and consolidated reporting in `reports/{LLM}/review_py-review-orchestrator_{YYYYMMDD}_{HHMM}_FINAL.md`. Use when a full-project audit or broad multi-layer review is requested."
---

# py-review-orchestrator

## Objective

Run the role-specific workflow as defined in the py-review-orchestrator profile.

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../docs/02-architecture/decisions`
- Canonical runtime entrypoint: this `SKILL.md`
- Team orchestration: `../../../.codex/agents/ORCHESTRATION.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role-specific memory: `../../../docs/00-project/ai/memory/memory-py-review-orchestrator.md`

## Workflow

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the review task.
1. Read `MEMORY_USAGE.md`, `agent-memory.md`, and
   `memory-py-review-orchestrator.md`; then add delegated role-memory sheets
   for sector-specific reviewers.
1. Treat this skill file as the canonical Codex runtime profile for the workflow.
1. Execute hierarchical review orchestration (Wave 1, then Wave 2) and respect sector dependencies.
1. Aggregate sector reports into `reports/{LLM}/review_py-review-orchestrator_{YYYYMMDD}_{HHMM}_FINAL.md` (LLM = caller) with complete critical/high issue rollup.
1. Keep scoring and status thresholds aligned with the profile and BioETL rules.
1. After the review, run `python -m memory.tooling.workflow post-task ...` and promote only durable review knowledge.
