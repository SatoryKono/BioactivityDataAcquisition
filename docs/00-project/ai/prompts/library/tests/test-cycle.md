---
id: prompt.tests.cycle
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - REPO
  - BASE
  - WORK_BRANCH
  - SCOPE
  - LANE
  - MODE
  - CYCLE_COUNT
  - MAX_FIXES_PER_CYCLE
  - PYTEST_EXTRA
  - REQUIRE_GH_TRACKING
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - LANGUAGE
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
  - configs/quality/test_matrix.yaml
  - scripts/engineering/dev/run_pytest.ps1
  - scripts/engineering/dev/run_pytest.sh
anti_patterns:
  - Empty cycles for form
  - Full suite as first feedback without LANE=full or SCOPE=all
  - Raising debt budgets / xfail / skip to greenwash
  - Retries as flaky “fix”
  - Expanding SCOPE without evidence
  - Infinite fix loops without MAX_FIXES_PER_CYCLE
  - Confusing MODE=full (run+fix+issues) with LANE=full (all tests)
tags: [tests, cycle, pytest, quality, operator]
summary: Cyclic testing — baseline run, triage, fix, retest, delta per cycle
max_body_lines: 180
---

# Cyclic testing (run → triage → fix → retest)

Итеративный цикл **тестирования** BioETL: baseline → triage failures →
minimal fix → same-scope retest → delta. Не путать с audit-cycle (docs/code
review) и dashboard-audit-cycle.

Default **`CYCLE_COUNT=1`**. Пустые циклы «для формы» запрещены.

Связанные cards:

| Card | Когда |
| --- | --- |
| `prompt.tests.fix-retest` | узкий run→fix→run без multi-cycle reporting |
| `prompt.tests.speed-optimization` | ускорение suite без ослабления coverage |
| `prompt.audit.tests-system` | аудит тестовой системы (не run loop) |
| `prompt.closeout.grok` | закрытие issues после merge evidence |

Lanes: `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md` +
`configs/quality/test_matrix.yaml` (link only).

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `WORK_BRANCH` | `fix/test-cycle` (never `main`) |
| `SCOPE` | path/nodeids, or **`all`** (весь `tests/`) |
| `LANE` | `unit-fast` \| `architecture-fast` \| `scripts` \| `repo_backed` \| `custom` \| **`full`** |
| `MODE` | `full` \| `run+fix` \| `run+issues` \| `full` |
| `CYCLE_COUNT` | `5` |
| `MAX_FIXES_PER_CYCLE` | `5` |
| `PYTEST_EXTRA` | e.g. `-q --maxfail=1` (optional) |
| `REQUIRE_GH_TRACKING` | `false` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `LANGUAGE` | `ru` |

`MODE=full` = run+fix+issues (mutation fail-closed via `ALLOW_*`).  
**Не путать** с `LANE=full` / `SCOPE=all` (полный прогон тестов).

## Full-project suite

Любой из вариантов означает **запуск всех тестов проекта** под `tests/`:

| Param | Value | Resolved command |
| --- | --- | --- |
| `LANE` | `full` | `pytest tests` (SCOPE defaults to `tests` if empty or `all`) |
| `SCOPE` | `all` | `pytest tests` (LANE may be `full` or ignored for path resolution) |

Equivalents: `SCOPE=tests`, `SCOPE=tests/`.  
Prefer recording in run metadata: `lane=full`, `scope=all` → `pytest tests`.

**Caution:** full suite is heavy (unit + architecture + integration + e2e + …).
Use for release/regression cycles, not as default local feedback. Still no
budget growth / blanket skip to greenwash. Consider `PYTEST_EXTRA` for
reporting only (e.g. `-q`); do not use `--lf` alone as a substitute for full
baseline when `SCOPE=all` / `LANE=full` was requested.

## Lane → default command (если SCOPE пуст или `all` только с LANE≠full)

| LANE | Command sketch |
| --- | --- |
| `unit-fast` | `pytest tests/unit -m "not repo_backed and not subprocess_backed and not slow and not benchmark and not memory" --ignore=tests/unit/scripts --ignore=tests/unit/repo_backed` |
| `architecture-fast` | `pytest tests/architecture -m "architecture and not slow and not benchmark and not memory"` |
| `scripts` | `pytest tests/unit/scripts` |
| `repo_backed` | `pytest tests/unit/repo_backed -m "repo_backed and not slow"` |
| `full` | `pytest tests` — **all project tests** |
| `custom` | **require** explicit `SCOPE` (not `all` unless intentional full suite) |

**SCOPE resolution:**

| SCOPE | Meaning |
| --- | --- |
| `all` | → `tests` (full tree) |
| path / nodeid | as given (must exist) |
| empty + `LANE=full` | → `tests` |
| empty + `LANE=custom` | **STOP** |
| empty + other LANE | use lane default command above |

Windows: `.\.venv-win\Scripts\python.exe -m pytest …`  
или `.\scripts\engineering\dev\run_pytest.ps1 <scope> …`  
Linux/WSL: `bash scripts/engineering/dev/run_pytest.sh …`

## Preflight

1. Dirty tree с чужой работой → worktree/clone или **run-only**.
2. Resolve SCOPE / LANE as above; empty + LANE=custom → **STOP**.
3. If `LANE=full` or `SCOPE=all`: confirm operator intent (heavy run); still proceed when explicitly set.
4. `run_id = <UTC>-<shortsha>-test`
5. Artifacts: `reports/audit/test-cycle/<run_id>/`

## Cycle i = 1..CYCLE_COUNT

### Stage 1 — Baseline run

- Run resolved command; record: command, duration, exit, fail count, first N failures (`nodeid`, short traceback).
- Write `cycle-i/baseline.json` + log path.

### Stage 2 — Triage

For each failure (cap by priority):

| Field | Rule |
| --- | --- |
| class | `product` \| `test-bug` \| `fixture` \| `env/infra` \| `flaky-suspect` \| `out-of-scope` |
| evidence | path:line or nodeid + snippet |
| action | `fix-now` \| `issue` \| `block` \| `narrow-scope` |

Rules:

- Do **not** mark flaky without re-run count (record N attempts).
- Retry ≠ fix.
- Do not raise debt budgets, add blanket skip/xfail, or weaken gates to greenwash.
- Infra/env blockers → `BLOCKED` + exact missing precondition.

### Stage 3 — Fix (optional)

Only if `MODE` includes fix and failures are `fix-now`:

- Minimal diff; same product surface; no drive-by.
- At most `MAX_FIXES_PER_CYCLE` distinct root causes.
- Branch `fix/<slug>`; push only if `ALLOW_PUSH`.

### Stage 4 — Retest

- Re-run **same SCOPE** (or narrowed subset of failed nodeids, then full SCOPE once green).
- Compare to baseline: fixed / remaining / new / regressed.

### Stage 5 — Issues (optional)

If `REQUIRE_GH_TRACKING` or `MODE` includes issues:

- PROVEN product/test-bug only; dedupe open issues.
- `ALLOW_ISSUE_WRITE=false` → payloads in `issues.jsonl` only.

### Stage 6 — Cycle closeout

| Metric | Value |
| --- | --- |
| exit | 0 / non-zero |
| fails_before / fails_after | counts |
| state | `green` \| `partial` \| `blocked` \| `regressed` |
| surface_score | 0–3 (3=green stable; 0=critical path red / false-green risk) |

**Stop after cycle if:** green; `CYCLE_COUNT` exhausted; blocker non-actionable;
secret/destructive risk; max fixes hit with remaining red.

## Outputs

```text
reports/audit/test-cycle/<run_id>/
  run.json
  cycle-<i>/
    baseline.json
    triage.md
    retest.json
    issues.jsonl
    summary.md
  final-summary.md
```

## Final summary (required)

| Cycle | Lane/Scope | Before | After | State | Issues | Notes |
| --- | --- | --- | --- | --- | --- | --- |

Language: `LANGUAGE=ru` for narrative; paths/commands/nodeids original.
