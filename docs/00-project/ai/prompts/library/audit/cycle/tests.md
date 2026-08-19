---
id: prompt.audit.cycle.tests
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N = `10`
  - SCOPE = `tests/ configs/quality/ pyproject.toml` 
  - MODE = `full`
  - LANGUAGE = `ru` 
  - LANE = `full`
  - AUDIT_MODE = `full`
  - ALLOW_ISSUE_WRITE = `true` 
  - ALLOW_PUSH = `true` 
  - ALLOW_MERGE = `true` 
  - ALLOW_CLOSE  = `true` 
  - MAX_ISSUES_PER_ITERATION = `10`
  - BASE_BRANCH = `main`
  - REPO = `SatoryKono/BioactivityDataAcquisition` 
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
  - docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md
  - docs/00-project/ai/prompts/library/audit/tests-system.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - configs/quality/test_matrix.yaml
  - reports/quality/test-governance-current.json
anti_patterns:
  - Empty form cycles
  - Full-suite first feedback without LANE/SCOPE budget
  - Raising skip/xfail/debt budgets to greenwash
  - Retries as a flaky fix
  - Confusing prompt.tests.cycle (run loop) with this audit cycle
  - Inventing a coverage target the project does not define
tags: [audit, tests, cycle, quality, operator]
summary: Cyclic audit of the test system — lanes, gates, flaky, fix, re-verify
max_body_lines: 240
---

# Cyclic test-layer audit

N-итерационный аудит **тестового слоя** как системы regression-detection,
не «просто прогон pytest». Domain method: `prompt.audit.tests-system`.
Loop shell: `prompt.audit.orchestrator`.

Для **run → fix → retest** без audit-реестра используй `prompt.tests.cycle`.

Default **`N=10`**, **`MODE=full`**, все **`ALLOW_*=true`**. Пустые циклы запрещены.
**УВЕЛИЧИВАТЬ skip/xfail/debt бюджеты ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `tests/ configs/quality/ pyproject.toml` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `LANE` | `unit` (`unit` \| `arch` \| `fast` \| `full`) |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |

## BioETL anchors

- Mental model: `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md`
- Matrix: `configs/quality/test_matrix.yaml`
- Snapshot: `reports/quality/test-governance-current.json`
- Residual: `reports/quality/live-residual-snapshot.json`
- Runners: `scripts/engineering/dev/run_pytest.sh` / `.ps1`
- Windows: only `.\.venv-win\Scripts\python.exe -m pytest …`
- Do not invent a coverage fail-under the project does not define

## Preflight

1. `git status --porcelain`; SHA; branch; toolchain; `gh auth status` (no tokens).
2. Dirty foreign work → worktree or **read-only**.
3. `run_id = <UTC>-tests-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` + optional mirror `reports/audit/tests/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | pytest/CI lanes, markers, skip/xfail/quarantine, isolation, required checks. Classify unit / integration / contract / e2e / smoke / architecture / security. Map what actually blocks merge. |
| **B Risk gaps** | Critical product paths → tests. Note negative/auth/schema gaps. Optional bounded LANE run for evidence only — not a full suite by default. |
| **C Flaky / disabled** | Suspected flaky: re-run **N** times; record N and outcomes. Quarantine/skip must have owner or tracked issue. Retries are not a fix. |
| **D Plan / Issues** | P0→P3; acceptance + validation command per item. Create if ALLOW_ISSUE_WRITE + PROVEN. No budget raises. |
| **E Fix** | Minimal diff. Focused tests for behavior change. No new skips/xfail as “fix”. |
| **F Validate** | Same LANE/SCOPE re-check. If ALLOW_PUSH → PR + required checks. No admin bypass. Delta: resolved / unchanged / regressed / new. |

## Focus checklist (each cycle)

- [ ] Clean-checkout / documented entry command still true
- [ ] Unit default has no mandatory external network
- [ ] Isolation of temp dirs / ports / time / random
- [ ] Quarantine/skip has owner or tracked issue
- [ ] Flaky claims include re-run count N and outcomes
- [ ] CI required checks mapped to lanes
- [ ] `test-governance-current.json` / residual snapshot not silently diverged
- [ ] Skip/xfail/debt budgets unchanged or reduced

## Stop

Unbounded full suite without budget → STOP. Secret in fixtures → P0.
Proposed skip/xfail/debt budget increase → reject. Orchestrator hard-stop.

## Success

- `findings.json` + `report.md` per iteration under `reports/audit-runs/<run_id>/`
- No new P0/P1 regression in post-audit
- Debt/skip budgets unchanged or reduced
- With defaults: issues / push / merge / close when acceptance is met

## Related

- Domain: `prompt.audit.tests-system`
- Run loop: `prompt.tests.cycle`, `prompt.tests.fix-retest`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.tests-system`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.configs` · Next: `prompt.audit.cycle.tech-debt`
