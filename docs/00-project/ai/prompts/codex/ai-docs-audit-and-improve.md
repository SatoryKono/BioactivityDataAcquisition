# Codex Prompt: Audit and Improvement Plan for `docs/00-project/ai`

Source: `docs/00-project/ai/prompts/docs_ai_audit_planning_claude_prompt.md`
Purpose: Codex-native orchestration prompt for the AI docs workspace.

## Prompt

You are Codex acting as the documentation orchestrator for BioETL.

Audit `docs/00-project/ai/`, build a plan, and execute safe documentation improvements in a controlled cycle.

### Scope

- `docs/00-project/ai/**`
- closely related navigation or docs config when the same fix requires it

Do not edit `src/bioetl/**`.

### Operating model

Work in this order:

1. discovery
2. baseline audit
3. prioritized plan
4. one change-set at a time
5. verification after each change-set
6. final audit
7. independent double-check

### Discovery

Build an evidence-backed inventory for:

- directory structure
- deprecated aliases and stale duplicates
- broken links
- nav drift
- files outside expected navigation
- inconsistencies between `guides/`, `runtime/`, `policy/`, and snapshots

### Baseline audit

Evaluate:

- consistency with project rules
- consistency with MkDocs nav
- legacy-path drift
- naming and structure coherence

Summarize baseline issues as `must` and `should`.

### Planning

Create RF-style tasks with:

- objective
- file scope
- risk
- mitigation
- definition of done

### Execution rules

- Apply one RF task at a time.
- After each docs change-set, run the relevant verification.
- If a check fails, fix the current change-set before moving on.
- If quality worsens relative to baseline, stop and report why.

### Final output

1. Findings table: `Problem | Severity | File | Status | Evidence`
2. RF plan with priorities
3. Completed changes
4. Checks run and outcomes
5. Metrics before and after
6. Explicit verdict:
   - `continue`
   - or `stop: <reason>`
