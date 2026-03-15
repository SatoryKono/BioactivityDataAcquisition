# Codex Prompt: AI Docs Audit and Improvement Cycle

Source: `docs/00-project/ai/prompts/docs_ai_audit_planning_codex_prompt.md`
Purpose: Codex-optimized version of the AI-docs audit workflow.

## Prompt

You are Codex acting as the technical orchestrator for the BioETL AI documentation workspace.

Audit and improve `docs/00-project/ai/` using the strict cycle:

`baseline -> plan -> change -> verify -> final review`

### Scope

- `docs/00-project/ai/**`
- directly related docs navigation or docs config

Do not touch production code.

### Rules

1. Start with a baseline audit before editing.
2. After every docs change-set, run verification.
3. If documentation quality becomes worse than baseline, stop immediately.
4. Support findings with commands and file paths.
5. Keep scope limited to docs, links, navigation, and mirrors.

### Required phases

#### Phase 1. Discovery

Inventory:

- directory structure
- duplicates and stale aliases
- broken links
- files missing from navigation
- drift across `guides/`, `runtime/`, `policy/`, and snapshots

#### Phase 2. Baseline

Audit:

- consistency with project rules
- navigation correctness
- absence of legacy-path drift
- naming and structure consistency

#### Phase 3. Plan

Build an RF backlog with:

- goal
- scope
- risk
- mitigation
- definition of done

#### Phase 4. Execute

Apply RF tasks one by one. After each task, run the smallest sufficient docs verification set. If a failure appears, fix it in the same iteration.

#### Phase 5. Final review

Compare final state to baseline and state whether the workspace improved, stayed flat, or regressed.

### Required report

1. Findings matrix
2. Prioritized RF plan
3. Executed changes
4. Verification log
5. Metrics before vs after
6. Explicit stop/continue decision
