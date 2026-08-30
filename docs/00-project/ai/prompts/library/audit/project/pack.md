---
id: prompt.audit.project.pack
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, any]
params: [TASK, MODE, LANGUAGE, N, WORK_BRANCH]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/ai/prompts/library/audit/cycle/README.md
  - docs/00-project/ai/prompts/library/audit/cyclic-pack.md
  - docs/00-project/ai/prompts/library/audit/sequential-run.md
  - docs/00-project/ai/prompts/library/audit/project/README.md
anti_patterns:
  - Editing materialized-v3 snapshots by hand
  - Running every file in library/audit including role/meta duplicates
  - Raising tech-debt budgets
  - Committing to main
tags: [audit, project, pack, tech-debt, tests, docs, diagrams, operator]
summary: Full project-audit paste pack — tech-debt, tests, docs, diagrams, and the 10-domain cycle
max_body_lines: 140
---

# BioETL — полный аудит проекта (pack)

Не runtime SSOT. Язык: `{{LANGUAGE}}`. Редактируемые карточки находятся в
`../cycle/` и соседних `../*.md`; полный неизменяемый снимок опубликован в
[materialized-v3](materialized-v3/README.md).

## Params

| Param | Default |
| --- | --- |
| `TASK` | последовательный аудит 10 доменов + method cards |
| `MODE` | `full` |
| `LANGUAGE` | `ru` |
| `N` | `10` |
| `WORK_BRANCH` | `fix/audit-project-<shortsha>` |

## Куда вставлять

| Нужно | Полный текст | Source id |
| --- | --- | --- |
| Весь прогон 1→10 с ISSUE/FIX/CLOSE | [sequential-run source](../sequential-run.md) | `prompt.audit.sequential-run` |
| Router 10 доменов | [cyclic-pack source](../cyclic-pack.md) | `prompt.audit.cyclic-pack` |
| Документы | [cycle/docs source](../cycle/docs.md) | `prompt.audit.cycle.docs` |
| Диаграммы | [cycle/diagrams source](../cycle/diagrams.md) | `prompt.audit.cycle.diagrams` |
| Тесты | [cycle/tests source](../cycle/tests.md) | `prompt.audit.cycle.tests` |
| Техдолг | [cycle/tech-debt source](../cycle/tech-debt.md) | `prompt.audit.cycle.tech-debt` |
| Архитектура | [cycle/architecture source](../cycle/architecture.md) | `prompt.audit.cycle.architecture` |
| Конфиги / агенты / telemetry / dashboards / CR | [cycle index](../cycle/README.md) | `prompt.audit.cycle.*` |
| Полные operator-paste snapshots | [materialized-v3 index](materialized-v3/README.md) | 24 frozen prompts + master |

Порядок доменов: docs → diagrams → agents-memory → configs → tests →
tech-debt → architecture → telemetry → dashboards → coderabbit.

## Запреты

Не править `materialized-v3/*.md` руками. Не commit в `main`.
Не увеличивать бюджеты техдолга. Не трогать `.env`. Чужой dirty WIP —
worktree.

## Done when

- [ ] Выбран sequential **или** один домен
- [ ] Артефакты в `reports/audit-runs/<run_id>/`
- [ ] Evidence против текущего checkout / `origin/main`
