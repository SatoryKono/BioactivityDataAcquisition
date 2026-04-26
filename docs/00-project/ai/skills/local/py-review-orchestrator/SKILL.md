______________________________________________________________________

## name: py-review-orchestrator description: Execute BioETL hierarchical code review orchestration (L1/L2/L3) across sectors S1-S8 with delegated sub-reviews, scoring, and consolidated reporting in `reports/{LLM}/review_py-review-orchestrator_{YYYYMMDD}_{HHMM}_FINAL.md`. Use when a full-project audit or broad multi-layer review is requested.

# py-review-orchestrator

## Objective

Run the role-specific workflow as defined in the py-review-orchestrator profile.

## Source Of Truth

- Primary profile: `../../../.codex/agents/py-review-orchestrator.md`
- Team orchestration: `../../../.codex/agents/ORCHESTRATION.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Workflow

1. Open and follow `../../../.codex/agents/py-review-orchestrator.md`.
1. Execute hierarchical review orchestration (Wave 1, then Wave 2) and respect sector dependencies.
1. Aggregate sector reports into `reports/{LLM}/review_py-review-orchestrator_{YYYYMMDD}_{HHMM}_FINAL.md` (LLM = caller) with complete critical/high issue rollup.
1. Keep scoring and status thresholds aligned with the profile and BioETL rules.
