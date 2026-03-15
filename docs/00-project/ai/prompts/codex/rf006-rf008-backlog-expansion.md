# Codex Prompt: Expand RF-006 and RF-008 into an Execution Backlog

Source: `docs/00-project/ai/prompts/tmp.md`
Purpose: convert the stored refactor ideas into a concrete Codex-friendly task breakdown.

## Prompt

You are Codex acting as a refactor planner for two BioETL initiatives:

- `RF-006`
- `RF-008`

The source text contains strategy-level intent. Turn it into an implementation backlog without editing code.

### Goal

Expand the two refactor plans into concrete, file-level tasks with verification strategy and sequencing.

### Constraints

- Read-only analysis only.
- Preserve the intent and non-goals from the source plans.
- Do not introduce speculative redesigns unsupported by the repository.

### Required output for each RF item

1. Objective
2. Non-goals
3. Suspected target files and modules
4. Recommended execution order
5. Task breakdown with stable IDs
6. Required characterization tests
7. Required targeted unit, integration, and architecture checks
8. Key risks and mitigations
9. Exit criteria

### Special instructions

For `RF-006`, focus on:

- dependency coordinator seams
- runtime factory decomposition
- keeping the runner thin
- characterization coverage before movement

For `RF-008`, focus on:

- restoring a trustworthy high-level test signal first
- thinning `run_all.py`
- removing hidden composition from provider clients
- aligning OpenAlex and CrossRef patterns without needless churn

### Final section

Provide a combined dependency-aware roadmap showing which RF-006 and RF-008 tasks can proceed in parallel and which must remain sequential.
