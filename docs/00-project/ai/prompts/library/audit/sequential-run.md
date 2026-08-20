---
id: prompt.audit.sequential-run
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok]
params:
  - REPO
  - BASE_BRANCH
  - WORK_BRANCH
  - LANGUAGE
  - N
  - MODE
  - DEPTH
  - INCLUDE_PIPELINE
  - MONITORING
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_STEP
  - REQUIRE_GH_TRACKING
  - CODERABBIT
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/finding-schema.md
  - fragments/audit-scale.md
  - fragments/project-requirements-audit.md
  - fragments/reports-output.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/00-project/ai/prompts/library/audit/cycle/README.md
  - docs/00-project/ai/prompts/library/audit/cyclic-pack.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Running every file in library/audit/ including meta/role/duplicate cards
  - Skipping ISSUE/CLOSEOUT gates between domain cards
  - Recreating closed issues that already have an open fix PR
  - Closing issues against unmerged PR heads as if they were on origin/main
  - Raising debt budgets
  - Starting monitoring when MONITORING=false
tags: [audit, sequential, cycle, github, operator]
summary: Sequential library/audit run — 10 cycle cards, per-card issue/fix/close gates
max_body_lines: 280
---

# BioETL — последовательный аудит `library/audit` (v1.1)

Не runtime SSOT. Precedence: `AGENTS.md` → `docs/00-project/NORMATIVE_SOURCES.md`
→ `library/audit/cycle/` → остальные `library/audit/*` только как method cards.
Язык: `{{LANGUAGE}}`. Технические литералы не переводить.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE_BRANCH` | `main` |
| `WORK_BRANCH` | `fix/audit-seq-<shortsha>` |
| `LANGUAGE` | `ru` |
| `N` | `1` |
| `MODE` | `full` |
| `DEPTH` | `full` |
| `INCLUDE_PIPELINE` | `true` |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_STEP` | `8` |
| `REQUIRE_GH_TRACKING` | `true` |
| `CODERABBIT` | `required-then-agent` |

Примечания к дефолтам: `N` — число полных проходов карточки; `WORK_BRANCH`
никогда не `main`; `CODERABBIT=required-then-agent` действует только на шаге 10
(сначала required-проверки CI, затем агентная проверка).

## TASK / MODE

TASK: исполнить уникальные audit-карточки по порядку ниже. После **каждой**
карточки — ISSUE GATE → IMPLEMENT → CLOSEOUT GATE. К следующей карточке не
переходить, пока issues шага не `closed` или `BLOCKED` с точной причиной.
MODE: implement. Не commit/push/merge в `{{BASE_BRANCH}}`. Чужой dirty WIP —
worktree.

## Жёсткие запреты

- Не создавать/править/удалять `.env` / `.env.*`.
- Не увеличивать бюджеты техдолга.
- Не force-push, не `reset --hard`, не `down -v`.
- Не выдумывать UID/panel/метрики/live-значения.
- Не дублировать open issue / open PR с тем же outcome.
- Root scratch ban: не плодить корневые `_tmp_*.py` / ad-hoc `test_*.py`.
- ADR-010: monitoring не стартовать при `MONITORING={{MONITORING}}`, пока
  оператор явно не попросил render.
- `unset GH_TOKEN GITHUB_TOKEN` перед `gh` (не печатать секреты).

## Последовательность (обязательная)

Канон — `prompt.audit.cycle.*` 1→10 ([cycle/README.md](cycle/README.md)).
Method card читать как метод, не как второй полный прогон.

| # | Card | Файл |
| --- | --- | --- |
| 1 | `prompt.audit.cycle.docs` | `library/audit/cycle/docs.md` |
| 2 | `prompt.audit.cycle.diagrams` | `library/audit/cycle/diagrams.md` |
| 3 | `prompt.audit.cycle.agents-memory` | `library/audit/cycle/agents-memory.md` |
| 4 | `prompt.audit.cycle.configs` | `library/audit/cycle/configs.md` |
| 5 | `prompt.audit.cycle.tests` | `library/audit/cycle/tests.md` |
| 6 | `prompt.audit.cycle.tech-debt` | `library/audit/cycle/tech-debt.md` |
| 7 | `prompt.audit.cycle.architecture` | `library/audit/cycle/architecture.md` |
| 8 | `prompt.audit.cycle.telemetry` | `library/audit/cycle/telemetry.md` |
| 9 | `prompt.audit.cycle.dashboards` | `library/audit/cycle/dashboards.md` |
| 10 | `prompt.audit.cycle.coderabbit` | `library/audit/cycle/coderabbit.md` |

После шага 10 — **только если поверхность ещё не закрыта**:

| # | Card | Условие |
| --- | --- | --- |
| 11 | `prompt.audit.repo-tree-cycle` | root/tree hygiene не закрыта шагом 7 |
| 12 | `prompt.audit.github-actions` | CI/workflows не закрыты шагами 5/7 |

Не запускать отдельно (дубли / meta / роли): `orchestrator`,
`dual-agent-cycle`, `grok-audit-cycle`, `cyclic-pack`, `role-auditor`,
`role-planner`, `generic-nine/*`, старые `docs-cycle` / `tests-cycle` /
`tech-debt-cycle` / one-shot `repo-tree`.

## Протокол на каждую карточку

### 0. Preflight

Прочитай карточку + method card. Зафиксируй SHA, branch, dirty.
Memory `pre-task` (`--title` / `--task-id` / `--summary`, venv + `PYTHONPATH=src`).
Artifacts: `reports/audit-runs/<UTC>-audit-seq-<shortsha>/step-<NN>-<id>/`.

### 1. AUDIT

Исполни карточку: `MODE={{MODE}}`, `DEPTH={{DEPTH}}`, `N={{N}}`.
Findings только PROVEN. Dedupe по root cause.
Пустой PROVEN-набор → `valid-empty.md` (что проверено), issues не создавать.

### 2. ISSUE GATE (до следующей карточки)

Если `ALLOW_ISSUE_WRITE={{ALLOW_ISSUE_WRITE}}`:
- один gh issue на **кластер** PROVEN-находок;
- title `[<domain>][<REQ-id>][P#] one checkable outcome`;
- body: outcome, evidence, acceptance, verification, constraints;
- ≤ `MAX_ISSUES_PER_STEP={{MAX_ISSUES_PER_STEP}}` новых issue; хвост →
  `issues-deferred.jsonl`;
- `gh issue list` перед create; номера в `issues.jsonl`.
Если `REQUIRE_GH_TRACKING={{REQUIRE_GH_TRACKING}}` и write выключен —
STOP.

### 3. IMPLEMENT

Ветка `{{WORK_BRANCH}}` (или `fix/<issue>-<slug>`), не `{{BASE_BRANCH}}`.
Минимальный fix до acceptance. POST_CHANGE_VALIDATION.
После `.codex/**` / `.junie/**`: `bash scripts/ai/junie/check_junie_mirror.sh --check`.
После `src/bioetl/**/*.py`: refresh
`reports/quality/module-coverage-inventory.json`.
`ALLOW_PUSH={{ALLOW_PUSH}}`: PR допустим. `ALLOW_MERGE={{ALLOW_MERGE}}`.

### 4. CLOSEOUT GATE

Каждый issue шага: `closed` или `BLOCKED` (внешний сервис / аппрув `.env` /
нужен merge main / live Grafana).
`ALLOW_CLOSE={{ALLOW_CLOSE}}`: close только при доказанном acceptance в
**этом checkout**, не потому что PR существует.
Memory `post-task`. `step-<NN>/summary.md`: card, findings, numbers, status.

### 5. Stop / continue

Незакрытый P0 → STOP весь прогон.
Две подряд карточки без PROVEN и без закрытых issues → спросить оператора.
После последнего шага: `gh issue list --state open` и `final-sweep.md`.

## Старт

1. Объяви run_id, SHA, branch, dirty.
2. Шаг 1: `prompt.audit.cycle.docs`.
3. Не спрашивай разрешения между шагами, пока нет STOP/BLOCKED оператора.
4. Приступай. `REPO={{REPO}}`.
