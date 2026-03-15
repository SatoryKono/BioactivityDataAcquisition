# Codex Prompt: Architecture Debt Reduction Orchestrator

Source: `docs/00-project/ai/prompts/architecture_debt_reduction_orchestration.md`
Purpose: reduce architecture-metric debt from generated JSON task files.

## Prompt

You are Codex acting as the architecture-debt reduction orchestrator for BioETL.

Take the latest `tasks_architecture_metric_exemptions_*.json` in the repository root and work through: `classify -> plan -> change -> verify -> audit -> continue or stop`.

### Phase 1. Load and classify work

1. Find all `tasks_architecture_metric_exemptions_*.json` files in the repository root.
2. If several exist, choose the latest by timestamp in the filename.
3. Read `tasks[]` and classify each task into:
   - `STALE_EXEMPTION`
   - `GOD_OBJECT`
   - `COMPLEXITY`
   - `NEAR_LIMIT`
   - `REDUCE_TO_LIMIT`
   - `SAFE_MARGIN`

### Base limits

Use these default limits, not exemption-specific limits, to decide whether an exemption is stale:

```yaml
file_size_limits:
  domain: 305
  application: 500
  composition: 350
  infrastructure: 650
  interfaces: 400

class_size: 300

function_complexity:
  domain: 5
  application: 10
  infrastructure: 15

god_object:
  min_delegation: 3
```

### Processing order

Handle work in this order unless a clear dependency requires otherwise:

1. `STALE_EXEMPTION`
2. `GOD_OBJECT`
3. `COMPLEXITY`
4. `NEAR_LIMIT`
5. `REDUCE_TO_LIMIT`
6. `SAFE_MARGIN`

### Codex execution rules

- Main agent edits `src/bioetl/**` directly.
- Use `spawn_agent` only for bounded support work such as read-only investigation or narrow verification.
- For `STALE_EXEMPTION`, prefer registry cleanup and scorecard updates.
- Preserve behavior and public interfaces.
- Prefer minimal diffs unless the task explicitly requires decomposition.

### Verification after each task

Run the smallest relevant set from:

- targeted unit tests
- relevant architecture metric tests
- `mypy --strict` for touched files when applicable
- docs/docstring sync if public behavior or guidance changed

If verification fails:

1. diagnose root cause
2. fix it
3. rerun verification
4. stop if the regression persists

### Final audit

After the batch:

- run architecture checks
- run a focused review pass for regressions and boundary violations
- confirm the exemptions registry and debt scorecard remain internally consistent

### Stop conditions

Stop immediately if:

- tests regress relative to baseline
- architecture boundaries are newly violated
- scope grows beyond the debt task without strong justification
- a task requires behavior change or public API drift

### Required report

1. Selected task file and classification summary
2. Task execution log:
   - task ID
   - category
   - change made
   - checks run
   - result
3. Final audit summary
4. Updated risk list
5. Explicit decision:
   - `continue`
   - or `stop: <reason>`
