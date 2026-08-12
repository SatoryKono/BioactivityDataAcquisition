---
id: prompt.audit.tests-cycle
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - LANE
  - AUDIT_MODE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/ai/prompts/library/audit/tests-system.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md
  - reports/quality/test-governance-current.json
  - configs/quality/test_matrix.yaml
anti_patterns:
  - Empty form cycles
  - Full-suite first feedback without LANE/SCOPE budget
  - Raising skip/xfail/debt budgets to greenwash
  - Retries as flaky fix
  - Confusing prompt.tests.cycle (run loop) with this audit cycle
tags: [audit, tests, cycle, quality, operator]
summary: Cyclic audit of the test system — inventory, gates, flaky, fix, re-verify
max_body_lines: 160
---

# Cyclic tests-system audit

N-итерационный **аудит тестовой системы** (regression-detection), не «просто
прогон pytest». Domain method: `prompt.audit.tests-system`. Loop shell:
`prompt.audit.orchestrator`.

Для **run → fix → retest** без audit-реестра используй `prompt.tests.cycle`.

Default **`N=10`**, **`MODE=full`**, все **`ALLOW_*=true`** (issues / push / merge / close).

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `tests/` + CI test workflows + quality configs |
| `MODE` | `full` (also: `audit` \| `audit+issues`) |
| `LANGUAGE` | `ru` |
| `LANE` | `unit` \| `arch` \| `fast` \| `full` (budget for optional focused runs) |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |

## BioETL anchors (read, do not reinvent)

- Mental model: `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md`
- Matrix: `configs/quality/test_matrix.yaml`
- Snapshot: `reports/quality/test-governance-current.json`
- Residual non-growth: `reports/quality/live-residual-snapshot.json` (+ architecture tests)
- Runners: `scripts/engineering/dev/run_pytest.sh` / `.ps1`
- Windows: only `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch; toolchain; `gh auth status` (no tokens).
2. Dirty foreign work → worktree or **read-only**.
3. `run_id = <UTC>-tests-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` (and mirror domain notes under
   `reports/audit/tests/` for the latest iteration if useful).

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Audit** | Execute `prompt.audit.tests-system` on SCOPE. Inventory pytest/CI lanes, skip/xfail/quarantine, isolation, critical-path coverage gaps, required checks. Optional: bounded LANE run for evidence only (not full suite by default). |
| **B Plan** | Dedupe findings; P0→P3; acceptance + validation command per item; no budget raises. |
| **C Issues** | Dedupe open GH issues (`test`, `quality`, flaky). Create only if `ALLOW_ISSUE_WRITE` + PROVEN. Else `issues.jsonl`. |
| **D Fix** | Minimal diff; focused tests for behavior change; no new skips/xfail as “fix”. |
| **E Validate** | Same LANE/SCOPE re-check; if `ALLOW_PUSH` → PR + required checks. No admin bypass. |
| **F Post** | Per finding: `resolved` \| `unchanged` \| `regressed` \| `new`. Update `iteration-i/delta.md`. |

## Focus checklist (each cycle)

- [ ] Clean-checkout / documented entry command still true
- [ ] Unit default has no mandatory external network
- [ ] Quarantine/skip has owner or tracked issue
- [ ] Flaky claims include re-run count N and outcomes
- [ ] CI required checks mapped to lanes (what actually blocks merge)
- [ ] `test-governance-current.json` / residual snapshot not silently diverged

## Stop

Orchestrator-guards. Also stop mutation if: unbounded full suite requested
without budget; secret in fixtures; debt/skip budget increase proposed.

## Success

- `findings.json` + `report.md` per iteration under `reports/audit-runs/<run_id>/`
- No new P0/P1 regression in post-audit
- Debt/skip budgets unchanged or reduced
- With defaults: issues / push / merge / close when acceptance is met

## Related

- Domain: `prompt.audit.tests-system`
- Run loop: `prompt.tests.cycle`, `prompt.tests.fix-retest`
- Dual-agent: `prompt.audit.dual-agent-cycle` with
  `AUDIT_PROMPT_SOURCE=prompt.audit.tests-system`
- Closeout: `prompt.closeout.grok`
