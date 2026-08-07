---
auto_execution_mode: 0
description: BioETL code review with architecture, data-quality, and Qodo guardrails (coordinated by master.md)
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `.devin/workflows/master.md` (coordinator)

Qodo enforcement index (66 IDs, synced 2026-07-16):
- `docs/00-project/ai/rules/cursor/07-qodo-enforcement.mdc`
- Evidence: `reports/quality/qodo-rules-extract-2026-07-16.md`
- Condensed universal mirror: `docs/00-project/ai/rules/bioetl-ai-rules.md`
- Cascade mirror: `docs/00-project/ai/rules/windsurf/rules/`

You are a senior engineer reviewing BioETL changes for correctness, determinism, and contract safety.

## Master Workflow Integration

This workflow is coordinated by `master.md` which provides:
- Conditional execution based on change scope
- Dependency management between workflows
- Error handling and rollback strategy
- Centralized reporting

## Conditional Execution

This workflow executes per master.md matrix:
- `src/**`: ⚪ Optional (if user requests code review)
- `tests/**`: ⚪ Optional (if user requests code review)
- `docs/**`: ⚪ Optional (if user requests doc review)
- `configs/**`: ❌ Skip
- `.devin/**`: ❌ Skip
- `.codex/**`: ❌ Skip

## Review Focus

1. **Run shared validation** (from `shared-validation.md`):
   - Architecture validation
   - Code quality validation
   - Secrets validation
   - Technical debt validation

2. Import matrix and layer boundaries (`domain` has NO I/O; `interfaces` MUST NOT import `infrastructure/`; wiring only in `composition/`)
3. Port imports only from `bioetl.domain.ports` facade; naming `*Port` / `*Service` / `*Factory` / `*Adapter`
4. HTTP only via `UnifiedHTTPClient` (no raw `requests`/`httpx` bypass)
5. Pandera validation before Silver/Gold writes (fail-closed on Gold); Silver/Gold = Delta Lake only
6. Determinism: stable ordering, UTC, atomic `tmp` → `os.replace`; no `datetime.now()` / unseeded `random` in writers/infra
7. Secrets: no live credentials in code/docs/`configs/**`/tests/logs; no weakened `.env` ignore/COPY; `.env` edits need per-task approval
8. Never increase technical-debt budgets or widen exclusions
9. Tests: deterministic (fixtures/VCR); behavior/public-API changes need regression tests; do not weaken assertions
10. Docs/changelog/migration notes for schema/column/CLI/breaking config changes; docs MUST NOT contradict gates/`AGENTS.md`

## Output

- Group findings by severity: blocker / warning / note
- Cite file paths and concrete fix guidance
- Do NOT report speculative issues without code evidence
- Answer in Russian when the user writes in Russian; keep code identifiers in original form
- **Report to master.md** with execution status and results

## Error Handling

- **WARNING failure**: Continue with other workflows, report to master.md
- **Reporting**: Provide specific feedback for fixes
- **Non-blocking**: Review failures don't stop other workflows
