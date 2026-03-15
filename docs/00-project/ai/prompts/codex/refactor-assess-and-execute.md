# Codex Prompt: Refactor Orchestration, Planning, and Early Execution

Source: `docs/00-project/ai/prompts/refactor_orchestration_prompt_1-2.md`
Purpose: Codex adaptation of the earlier phase-focused refactor workflow.

## Prompt

You are Codex acting as the BioETL refactor orchestrator.

This version is for a controlled cycle that starts with architecture assessment and then moves into limited execution. Use the repository as truth and keep every claim evidence-backed.

### Phase 1. Architecture review

Produce a structured architecture review with:

- 10 evaluation categories
- weight per category, total weight exactly `1.0`
- score per category from `1` to `10`
- weighted total score
- concise justification per score

Cover at minimum:

- layer boundaries
- Ports and Adapters alignment
- DDD and domain purity
- dependency clarity
- naming and structure consistency
- test safety signal
- documentation support
- composition correctness
- operational clarity
- debt concentration

### Phase 2. Refactoring plan

Create a prioritized plan that includes:

- critical blockers
- medium-priority improvements
- low-priority cleanup

For each task include:

- goal
- target files or modules
- proposed change
- risk
- mitigation
- definition of done
- validation plan

### Phase 3. Limited execution

Implement only tasks that fit a controlled fix cycle:

- minimal diff
- no unnecessary decomposition
- verification after every change-set

### Stop rules

Stop if:

- tests regress
- architecture boundaries are violated
- the task requires behavior change not already approved
- the refactor expands into unrelated modules

### Final output

1. Architecture scorecard
2. Prioritized refactor plan
3. Executed subset, if any
4. Verification results
5. Explicit continue/stop decision
