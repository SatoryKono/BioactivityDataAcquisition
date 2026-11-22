---
id: prompt.audit.full-run
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- grok
- codex
- any
params:
- REPO
- BASE_BRANCH
- WORK_BRANCH
- LANGUAGE
- N
- MODE
- DEPTH
- DOMAINS
- MONITORING
- ALLOW_ISSUE_WRITE
- ALLOW_PUSH
- ALLOW_MERGE
- ALLOW_CLOSE
- MAX_ISSUES_PER_STEP
- REQUIRE_GH_TRACKING
- CODERABBIT
- RECONCILE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/language-ru.md
- fragments/finding-schema.md
- fragments/audit-scale.md
- fragments/project-requirements-audit.md
- fragments/orchestrator-guards.md
- fragments/issue-state-machine-v3.md
- fragments/cyclic-kernel-v3.md
- fragments/evidence-contract-v3.md
- fragments/gh-powershell.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/01-requirements/REQUIREMENTS.md
- docs/00-project/ai/prompts/library/audit/cycle.md
- docs/00-project/ai/prompts/library/audit/reconcile.md
- docs/00-project/ai/prompts/library/audit/sequential-run.md
- docs/00-project/ai/prompts/library/audit/comprehensive.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
- .codex/agents/py-audit-bot.md
anti_patterns:
- Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
- Running meta/role/duplicate cards (orchestrator, cyclic-pack, generic-nine/*)
- Skipping ISSUE/CLOSEOUT gates between domains
- Creating issues from raw findings before the RECONCILE stage
- Recreating closed issues that already have an open fix PR
- Closing issues against unmerged PR heads as if they were on origin/main
- Raising debt budgets or exemptions
- Starting monitoring when MONITORING=false (ADR-010)
- Re-scanning the repo per domain when shared inventory already proves the fact
tags:
- audit
- sequential
- full-run
- cycle
- github
- operator
summary: Full sequential audit run — bootstrap, shared inventory, 14 ordered
  domains with issue/fix/close gates, reconcile, final sweep, closeout
max_body_lines: 260
---
# BioETL — полный последовательный аудит (v1.0)

Не runtime SSOT: карточка не переопределяет runtime maps. Precedence: активные
runtime maps (`.codex/agents/CODEX-RUNTIME.md`, `.junie/agents/JUNIE-RUNTIME.md`,
`.devin/agents/DEVIN-RUNTIME.md` для Devin) → профили и skills своего дерева →
`docs/00-project/NORMATIVE_SOURCES.md` → `docs/00-project/RULES.md` →
`docs/01-requirements/REQUIREMENTS.md` → accepted ADR → mirrors
`docs/00-project/ai/**` → `prompt.audit.cycle` + `domains.yaml`.
Язык: `{{LANGUAGE}}`. Технические литералы не переводить.

Отличие от `prompt.audit.sequential-run`: shared inventory собирается один раз и
переиспользуется Evidence IDs, домены упорядочены по зависимостям DAG из
`prompt.audit.comprehensive`, добавлены стадии Reconcile и Final sweep,
поддержан memory-цикл pre/post-task из `.codex/agents/ORCHESTRATION.md`.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE_BRANCH` | `main` |
| `WORK_BRANCH` | `fix/audit-full-<shortsha>` (никогда не main) |
| `LANGUAGE` | `ru` |
| `N` | `1` (число полных проходов карточки домена) |
| `MODE` | `audit` (`implement` только с явным `--profile full-write`) |
| `DEPTH` | `full` (`differential` — delta vs origin/BASE) |
| `DOMAINS` | `core` (набор доменов Stage 2) |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `false` (fail-closed) |
| `ALLOW_PUSH` | `false` (fail-closed) |
| `ALLOW_MERGE` | `false` (fail-closed) |
| `ALLOW_CLOSE` | `false` (fail-closed) |
| `MAX_ISSUES_PER_STEP` | `8` |
| `REQUIRE_GH_TRACKING` | `true` |
| `CODERABBIT` | `required-then-agent` (действует только на доменe `coderabbit`) |
| `RECONCILE` | `true` |

## TASK / MODE

Исполнить Stage 0→5 строго по порядку. После **каждого** домена Stage 2 —
ISSUE GATE → IMPLEMENT GATE → CLOSEOUT GATE; к следующему домену не переходить,
пока issues домена не `closed` или `BLOCKED` с точной причиной. Не commit/push/
merge в `{{BASE_BRANCH}}`. Чужой dirty WIP — worktree.

## Жёсткие запреты

- Не создавать/править/удалять `.env` / `.env.*`.
- Не увеличивать бюджеты техдолга, exemptions, thresholds, hotspot caps.
- Не force-push, не `reset --hard`, не `down -v`.
- Не выдумывать UID/panel/метрики/live-значения; секреты не печатать
  (`unset GH_TOKEN GITHUB_TOKEN` перед `gh`).
- Root scratch ban: никаких корневых `_tmp_*.py` / ad-hoc `test_*.py`.
- Не дублировать open issue / open PR с тем же outcome.
- pwsh `gh`: fragment `prompt.fragment.gh-powershell` (`--body-file`, quoted
  `--jq`, `'@{u}'`).

## Stage 0 — Bootstrap

1. Объяви `run_id = <UTC>-audit-full-<shortsha>`; зафиксируй SHA, branch, dirty,
   toolchain versions.
2. Memory `pre-task` в read-only режиме (`--skip-refresh-if-missing
   --skip-session-note`, `PYTHONDONTWRITEBYTECODE=1`); отсутствующие артефакты
   retrieval — DEGRADED, сверять с исходником напрямую.
3. Артефакты прогона: `reports/audit-runs/<run_id>/`. Skips и DEGRADED
   фиксируй сразу, не в конце.

## Stage 1 — Shared inventory (один раз)

Собери и положи в `evidence-ledger.json` с Evidence IDs:

- топология пакетов/импортов и публичные entrypoints;
- configs/providers/entities/pipelines/workflows/composites;
- registries (contract/schema/normalization/DQ);
- тесты/markers/coverage/governance-артефакты со свежестью;
- CI workflows/actions и package/build metadata;
- docs/ADRs/runbooks;
- manifests/ledgers/checkpoints/lineage;
- dashboards/rules/alerts;
- debt/generated-отчёты с revision-привязкой producer;
- scripts/root allowlist и compatibility surfaces.

Каждый следующий этап переиспользует Evidence IDs. Повторный полный скан факта,
уже доказанного inventory, запрещён.

## Stage 2 — Домены по порядку

Порядок уважает зависимости DAG из `prompt.audit.comprehensive`:

| # | Домен (`domains.yaml`) | Заметка |
| --- | --- | --- |
| 1 | `repo-hygiene` | быстрый, на базе Stage 1 |
| 2 | `configs` | SSOT/прецедентность до кода |
| 3 | `security-secrets` | рано: дешёвые P0 |
| 4 | `docs` | |
| 5 | `diagrams` | после docs |
| 6 | `requirements-trace` | REQ-* binding |
| 7 | `agents-memory` | runtime-зеркала |
| 8 | `architecture` | после configs+docs |
| 9 | `scripts-inventory` | |
| 10 | `tests` | baseline/final |
| 11 | `tech-debt` | improved/unchanged/worsened |
| 12 | `telemetry` | |
| 13 | `dashboards` | audit поверх сохранённых данных; render только по явному запросу оператора |
| 14 | `coderabbit` | `CODERABBIT` default применяется здесь |

`DOMAINS=core` → строки 1–12 без `security-secrets`, `scripts-inventory`,
`requirements-trace`; `DOMAINS=full` → все 14; `DOMAINS=docs,tests` → только
перечисленные. Один домен = один прогон `prompt.audit.cycle` (его Stage 0–3).

### Протокол на домен

**AUDIT** — `MODE={{MODE}}`, `DEPTH={{DEPTH}}`, `N={{N}}`. Findings только
PROVEN с `path:line` или результатом команды; dedupe по root cause; пустой
PROVEN-набор → `valid-empty.md` (что проверено), issues не создавать.

**ISSUE GATE** — при `ALLOW_ISSUE_WRITE={{ALLOW_ISSUE_WRITE}}`: один gh issue на
**кластер** PROVEN-находок; title `[<domain>][<REQ-id>][P#] one checkable
outcome`; body: outcome, evidence, acceptance, verification, constraints;
`gh issue list` перед create; ≤ `MAX_ISSUES_PER_STEP={{MAX_ISSUES_PER_STEP}}`
новых issue, хвост → `issues-deferred.jsonl`; номера в `issues.jsonl`. Если
`REQUIRE_GH_TRACKING={{REQUIRE_GH_TRACKING}}` и write выключен — STOP.

**IMPLEMENT GATE** — ветка `{{WORK_BRANCH}}` (или `fix/<issue>-<slug>`), не
`{{BASE_BRANCH}}`. Минимальный fix до acceptance. POST_CHANGE_VALIDATION. После
`.codex/**` / `.junie/**`: `bash scripts/ai/junie/check_junie_mirror.sh --check`.
После `src/bioetl/**/*.py`: refresh
`reports/quality/module-coverage-inventory.json`.
`ALLOW_PUSH={{ALLOW_PUSH}}`: PR допустим. `ALLOW_MERGE={{ALLOW_MERGE}}`.

**CLOSEOUT GATE** — каждый issue шага: `closed` или `BLOCKED` (внешний сервис /
аппрув `.env` / нужен merge main / live Grafana). `ALLOW_CLOSE={{ALLOW_CLOSE}}`:
close только при доказанном acceptance в **этом checkout**, не потому что PR
существует. `step-<NN>-<domain>/summary.md`: card, findings, numbers, status.

## Stage 3 — Reconcile (`RECONCILE={{RECONCILE}}`)

Собери `raw-findings.json`, `root-cause-clusters.json`, coverage-matrix. Запусти
`prompt.audit.reconcile` как независимую сверку всех P0/P1 и sample P2/P3.
Канонические findings — только после reconcile; raw findings issues не создают.

## Stage 4 — Final sweep

`gh issue list --state open`. `final-sweep.md`: по каждому домену — findings,
issues, статус; debt-исход `improved | unchanged | worsened`; все skipped checks
с причиной и точной follow-up командой; DEGRADED memory-статусы.

## Stage 5 — Closeout

Memory `post-task` только в авторизованном read-write режиме; иначе skip и
отчёт об evidence/skips. Отчёт агента: проверки, skips, mirror-статус,
debt-исход. Незакрытый P0 → STOP весь прогон. Две подряд карточки без PROVEN и
без закрытых issues → спросить оператора.

## Stop / continue

- Незакрытый P0 → STOP весь прогон.
- STOP так же по guards-фрагменту: secret/data-loss, budget, dirty tree,
  missing perms, CI infra loop, unknown base.
- Между шагами разрешение оператора не спрашивать, пока нет STOP/BLOCKED.

## Старт

1. Объяви run_id, SHA, branch, dirty.
2. Stage 0 → Stage 1 → домены по порядку → Reconcile → Final sweep → Closeout.
3. Приступай. `REPO={{REPO}}`.
