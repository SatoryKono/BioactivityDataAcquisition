## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`
- `.devin/agents/DEVIN-RUNTIME.md`

# ORCHESTRATION.md — Оркестрация команды subagent-ов BioETL (Devin CLI)

*Версия: 1.0 | Дата: 2026-07-30 | Платформа: Devin CLI*

## 1. Обзор

Команда из **6 активных субагентов** (ровно шесть tracked `.devin/agents/*/AGENT.md` профилей) обеспечивает полный жизненный цикл задачи разработки BioETL. Основной агент (Devin) выступает оркестратором, делегируя работу субагентам через custom subagent profiles с использованием `run_subagent` tool. Production-код пишется напрямую оркестратором (без отдельного `py-code-bot`). Бывшие иерархические review/debt/swarm роли — **режимы** `py-audit-bot` (`review`, `debt`) и `py-test-bot`, а не отдельные профили.

**Запуск логического профиля в Devin runtime:**

```python
run_subagent(
    title="py-audit-bot baseline audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for task_id=AUD-001, phase=baseline, scope=src/bioetl/application/.",
    profile="py-audit-bot",
    is_background=False,
)
```

> Runtime mapping: см. `.devin/agents/DEVIN-RUNTIME.md`.

| # | Субагент (`profile`) | Model | Роль | Артефакт | Execution Mode |
| :---: | --- | --- | --- | --- | --- |
| I | **py-audit-bot** | parent | Baseline/final/targeted audit, review, debt, reproducibility (read-only) | `review_py-audit-bot_{YYYYMMDD}_{HHMM}_{phase}.md` | Foreground |
| II | **py-plan-bot** | parent | Планирование, декомпозиция, composite design (read-only) | `review_py-plan-bot_{YYYYMMDD}_{HHMM}.md` | Foreground |
| III | **py-test-bot** | default subagent model | Тестирование, flake triage, broad campaign | `review_py-test-bot_{YYYYMMDD}_{HHMM}.md` | Foreground/background |
| IV | **py-config-bot** | default subagent model | Конфигурации (pipeline, DQ, filter, composite) | `review_py-config-bot_{YYYYMMDD}_{HHMM}.md` | Foreground |
| V | **py-debug-bot** | parent | Reproduce / isolate / remediation guidance (read-only; fixes пишет оркестратор) | `review_py-debug-bot_{YYYYMMDD}_{HHMM}.md` | Foreground |
| VI | **py-doc-bot** | default subagent model | Документация, ADR, диаграммы (Mermaid) | `review_py-doc-bot_{YYYYMMDD}_{HHMM}.md` | Foreground |

> **Note:** `py-code-bot` removed — production code is written directly by the orchestrator. `py-diagram-bot` merged into `py-doc-bot`. Repo-wide documentation audits now route through the `py-doc-bot` / `py-doc-bot` skills rather than a dedicated documentation-only subagent profile.

### Разделение ответственности (файловые зоны)

| Субагент | Зона записи | Только чтение |
| --- | --- | --- |
| orchestrator (direct) | `src/bioetl/`, `tests/` | `configs/`, `docs/` (delegated) |
| py-audit-bot | — (read-only) | всё |
| py-plan-bot | — (read-only) | всё |
| py-debug-bot | — (read-only; implementation stays with orchestrator) | всё |
| py-config-bot | `configs/` | `src/bioetl/`, `docs/` |
| py-doc-bot | `docs/`, docstrings | `configs/`, `tests/` |
| py-test-bot | — (exec only; `AGENT.md` denies write/edit) | `src/bioetl/`, `configs/`, `tests/` |

### Определения субагентов

Файлы: `.devin/agents/<profile-name>/AGENT.md` — каждый содержит YAML-frontmatter (`name`, `description`, `model`, `allowed-tools`, `permissions`) + полную спецификацию с инлайнированными знаниями.

## 1.0 Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- Это правило обязательно для оркестратора и для всех `py-*` subagent profiles.
- Под запрет попадают `scorecard budgets`, exemption limits, hotspot thresholds, hotspot family caps и любые аналогичные budget/threshold поверхности.
- Если очередная волна работ упирается в лимит, оркестратор обязан декомпозировать scope, уменьшить объём изменения или эскалировать, а не повышать лимит.

## 1.1 Evidence Calibration

Перед repo-wide structural выводами, hotspot-программами и package-reorg инициативами сверяйся только с активными evidence surfaces:

- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/02-architecture/current-state-inventory.md`
- `reports/quality/architecture-quality-scorecard.json`
- `reports/quality/debt-governance-gates.json`

Operational defaults:

- package count сам по себе не является refactor trigger;
- family-level topology важнее whole-layer breadth;
- topology показывает, где смотреть, а governance signals — где реально действовать.

## 1.2 Memory-Enabled Task Loop

Перед стандартным subagent workflow оркестратор и role-specific profiles должны использовать canonical memory loop из `src/memory/DAILY_WORKFLOW.md`.

Минимальный порядок:

1. `python -m memory.tooling.workflow pre-task --task-id <id> --title "<task>"`
1. retrieval order: `catalog -> graph -> rag -> source`
1. baseline/profile-specific work
1. `python -m memory.tooling.workflow post-task --task-id <id> --title "<task>" --summary "<result>"`
1. promotion только для durable knowledge

Это не заменяет runtime source или `.devin/agents/*.md`, а стандартизует:

- pre-task retrieval
- session-note creation
- post-task summary
- refresh rebuild-only memory artifacts
- optional promotion into curated memory
- periodic curated review via `python -m memory.tooling.workflow review-curated`
- archive of superseded curated notes вместо silent stale accumulation

Regular ritual rule:

- run `review-curated` on a recurring engineering cadence
- run it again before release-readiness, governance, или architecture-review checkpoints
- treat `due` notes как verification work и `stale` notes как review-or-archive candidates

______________________________________________________________________

## 2. Стандартный workflow задачи

```
┌─────────────────────────────────────────────────────────────────────┐
│                        СТАРТ ЗАДАЧИ                                 │
│                     task_id назначен                                │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ① py-audit-bot (baseline)   │──→ review_py-audit-bot_{YYYYMMDD}_{HHMM}_baseline.md
│  Аудит целевого фрагмента   │  (foreground)
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ② py-plan-bot (initial)     │──→ review_py-plan-bot_{YYYYMMDD}_{HHMM}.md
│  Формирование плана RF-*    │  (foreground)
│  (+консолидация с user plan)│
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ③ py-test-bot (baseline)    │──→ review_py-test-bot_{YYYYMMDD}_{HHMM}.md
│  Фиксация состояния тестов  │  (foreground/background)
└─────────────┬───────────────┘
              │
         ┌────┴────┐
         │  FAIL?  │
         └────┬────┘
        yes   │   no
         ▼    │    │
┌─────────────┤    │
│ py-debug-bot│    │
│→ py-test-bot│    │
│ (цикл)      │──→ review_py-debug-bot_{YYYYMMDD}_{HHMM}.md
└──────┬──────┘    │
       │           │
       ▼           │
┌──────────────┐   │
│ py-plan-bot  │   │
│ (update)     │──→ review_py-plan-bot_{YYYYMMDD}_{HHMM}.md
└──────┬───────┘   │
       │           │
       ◄───────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  ④ РЕАЛИЗАЦИЯ (параллельно по зонам ответственности) │
│                                                       │
│  orchestrator ─→ src/bioetl/ ──→ direct edits in scope │
│       │                                                │
│       ├─ (entity scaffolding?) ──→ py-config-bot        │
│       │                                                │
│  py-config-bot → configs/  ──→ review_py-config-bot_{YYYYMMDD}_{HHMM}.md │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────┐
│  ⑤ py-test-bot (final)       │──→ review_py-test-bot_{YYYYMMDD}_{HHMM}.md
│  Финальный прогон тестов    │  (foreground/background)
└─────────────┬───────────────┘
              │
         ┌────┴────┐
         │  FAIL?  │
         └────┬────┘
        yes   │   no
         ▼    │    │
┌─────────────┤    │
│ py-debug-bot│    │
│→ py-test-bot│    │
│ (цикл ≤5)  │    │
└──────┬──────┘    │
       │           │
       ◄───────────┘
       │
       ▼
┌─────────────────────────────┐
│  ⑥ py-doc-bot                │──→ review_py-doc-bot_{YYYYMMDD}_{HHMM}.md
│  Обновление docs/docstrings │  (foreground)
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ⑦ py-audit-bot (final)      │──→ review_py-audit-bot_{YYYYMMDD}_{HHMM}_final.md
│  Финальная верификация       │  (foreground)
└─────────────────┬───────────┘
                  │
         ┌────────┴────────┐
         │ MUST findings?  │
         └────────┬────────┘
           yes    │    no
            ▼     │     │
┌───────────┤     │     │
│ Возврат к │     │     │
│ py-debug-bot│     │     │
│ / pyPlan  │     │     │
└───────────┘     │     │
                  │     │
                  ◄─────┘
                  │
                  ▼
┌─────────────────────────────┐
│          ЗАДАЧА ЗАВЕРШЕНА    │
└─────────────────────────────┘
```

______________________________________________________________________

## 3. Матрица взаимодействий

||   Отправитель →   |   py-plan-bot    |  py-test-bot   | py-config-bot | py-debug-bot |    py-doc-bot     |   py-audit-bot    |
|| :---------------: | :--------------: | :------------: | :-----------: | :----------: | :---------------: | :---------------: |
|| **py-audit-bot**  | findings → RF-*  |       —        |  config gaps  |      —       |  drift findings   |         —         |
||  **py-plan-bot**  |        —         |  scope RF-*   | config RF-*  |      —       |         —         |       scope       |
||  **py-test-bot**  |        —         |       —        |       —       | FAIL report  |         —         |         —         |
|| **py-config-bot** |        —         |  config tests  |       —       |      —       | DQ migration docs |         —         |
|| **py-debug-bot**  |   plan update    | retest trigger |  fix config   |      —       |     fix → doc     |  fix → re-audit   |
||  **py-doc-bot**   |        —         |       —        |       —       |      —       |         —         | terminology check |

### Ключевые потоки данных

```
py-plan-bot (RF-*)
    ├──→ orchestrator (type=refactor|feature|bugfix → src/)
    ├──→ py-config-bot (type=config → configs/)
    └──→ py-test-bot (test impact → tests/)

orchestrator (entity scaffolding)
    └──→ py-config-bot (pipeline + DQ + filter configs)

py-audit-bot (config findings)
    └──→ py-config-bot (gap remediation)

py-config-bot (DQ migration)
    └──→ py-doc-bot (update DQ documentation)
```

______________________________________________________________________

## 4. Структура артефактов

```
reports/{LLM}/review_{agent}_{YYYYMMDD}_{HHMM}[_{phase}].md
```

Правило: любой агент/субагент формирует итоговый отчёт только по этому пути (LLM = вызывающая модель, agent = профиль/skill, `phase` — опциональный суффикс для baseline/final/targeted, если это закреплено в contract конкретного `py-*` профиля). Дополнительные артефакты (телеметрия, метрики, промежуточные планы) сохраняйте рядом в той же директории, но итоговый отчёт должен соответствовать шаблону `reports/{LLM}/review_{agent}_{YYYYMMDD}_{HHMM}[_{phase}].md`.

Требования к каждому файлу (минимум):

- Дата/время создания (UTC), LLM, agent
- Scope (файлы/модули)
- Команды верификации
- Ссылки на `RF-*` / `DBG-*` / `AUD-*` / `DOC-*` / `CFG-*` идентификаторы
- Severity (если применимо): `MUST` / `SHOULD` / `MAY`
- Статус: `done` / `in_progress` / `blocked` / `escalated`

______________________________________________________________________

## 5. Протоколы принятия решений

### 5.1. Когда пропустить шаг

|| Шаг                   | Можно пропустить если                                 |
|| --------------------- | ----------------------------------------------------- |
|| py-audit-bot baseline | Задача = чистый bugfix одного файла, scope очевиден   |
|| py-plan-bot           | Задача = single-file doc update                       |
|| py-test-bot baseline  | Нет существующих тестов для scope (→ сразу new_tests) |
|| orchestrator code     | Задача = чистый config/doc change                     |
|| py-config-bot         | Задача не затрагивает configs/                        |
|| py-debug-bot          | Все тесты проходят                                    |
|| py-doc-bot            | Задача не меняет публичный API / поведение            |
|| py-audit-bot final    | Задача = чистый doc update без code changes           |

### 5.2. Маршрутизация RF-* по типу

|| RF type    |      Primary subagent       |                Secondary                |
|| ---------- | :-------------------------: | :-------------------------------------: |
|| `refactor` |        orchestrator         |   py-config-bot (если config impact)    |
|| `feature`  |        orchestrator         |    py-config-bot (если новый entity)    |
|| `bugfix`   | orchestrator / py-debug-bot | py-config-bot (если config-related bug) |
|| `config`   |        py-config-bot        |                    —                    |
|| `doc`      |         py-doc-bot          |                    —                    |

### 5.3. Эскалация

|| Ситуация                                 | Действие                                           |
|| ---------------------------------------- | -------------------------------------------------- |
|| py-debug-bot: 5 итераций без fix         | → `Requires Manual Review`, уведомить пользователя |
|| py-audit-bot final: новый MUST           | → Блокер, возврат к py-debug-bot/py-plan-bot       |
|| py-test-bot: coverage < 85%              | → MUST: разработка тестов (phase=new_tests)        |
|| py-plan-bot: цикл зависимостей RF-*      | → Пересмотр декомпозиции задачи                    |
|| py-config-bot: gap_analysis critical > 0 | → Блокер, возврат к py-config-bot/py-plan-bot      |

### 5.4. Параллелизация

В Devin CLI субагенты могут запускаться как параллельно (`is_background=True`), так и последовательно (`is_background=False`). Допустимые параллельные запуски:

- `py-test-bot` (baseline, background) ∥ `py-audit-bot` (baseline, foreground) — оба read-only
- `orchestrator` (direct) ∥ `py-config-bot` (foreground) — разные файловые зоны (src/ vs configs/)
- `py-doc-bot` (foreground) ∥ `py-audit-bot` (final, foreground) — если doc changes не влияют на code audit scope
- `py-test-bot` (background) для иерархического тестирования L1/L2/L3
- `py-audit-bot` (background) для иерархического code review

**Note:** Background subagents не могут запрашивать новые permissions — они используют только уже предоставленные в текущей сессии.

______________________________________________________________________

## 6. ID-системы

|| Prefix  | Subagent      | Формат     | Пример   | Описание                |
|| ------- | ------------- | ---------- | -------- | ----------------------- |
|| `RF-`   | py-plan-bot   | `RF-001`   | RF-001   | Рефакторинг / изменение |
|| `DBG-`  | py-debug-bot  | `DBG-001`  | DBG-001  | Debug-итерация          |
|| `AUD-`  | py-audit-bot  | `AUD-001`  | AUD-001  | Audit finding           |
|| `DOC-`  | py-doc-bot    | `DOC-001`  | DOC-001  | Обновление документации |
|| `FAIL-` | py-test-bot   | `FAIL-001` | FAIL-001 | Упавший тест (в отчёте) |
|| `CFG-`  | py-config-bot | `CFG-001`  | CFG-001  | Изменение конфигурации  |

Все ID уникальны в пределах `task_id`. Cross-references: `DBG-001 → RF-002`, `DOC-003 → RF-001`, `CFG-001 → RF-003`.

______________________________________________________________________

## 7. Гарантии и инварианты

1. **Traceability**: каждое изменение в коде привязано к `RF-*`, каждый fix — к `DBG-*`, каждый doc update — к `DOC-*`, каждый config change — к `CFG-*`.
1. **Baseline/Final symmetry**: для каждого baseline-артефакта существует final-артефакт.
1. **No blind changes**: код не меняется без предварительного плана (`RF-*`).
1. **No untested changes**: каждый `RF-*` проверяется через `py-test-bot`.
1. **Architecture gate**: финальный аудит (`py-audit-bot`) является обязательным gate перед завершением задачи.
1. **Config compliance gate**: `py-config-bot-1.py` MUST иметь 0 critical findings после `py-config-bot`.
1. **Zone isolation**: orchestrator writes `src/`, py-config-bot — только в `configs/`, py-doc-bot — только в `docs/` + docstrings + diagrams.
1. **Foreground/background safety**: critical changes (writes, config edits) требуют foreground mode для approval.

______________________________________________________________________

## 8. Упрощённые режимы

### 8.1. Quick-fix (single bug, low risk)

```
py-test-bot (baseline, scope=1 file, foreground/background)
→ orchestrator (fix)
→ py-test-bot (final, foreground/background)
→ py-doc-bot (docstring only, foreground)
```

### 8.2. Doc-only

```
py-doc-bot (создание/обновление, foreground)
  → py-audit-bot (targeted, audit_type=docs, foreground)
```

### 8.3. Config-only

```
py-audit-bot (targeted, audit_type=config, foreground)
  → py-plan-bot (plan, foreground)
  → py-config-bot (изменение configs, foreground)
  → py-test-bot (final, scope=config-related tests, foreground/background)
  → py-audit-bot (final, foreground)
```

### 8.4. New entity (full scaffolding)

```
py-plan-bot (plan, foreground)
  → orchestrator (domain entity + transformer + schema + adapter)
  → py-config-bot (pipeline + DQ + filter + source configs, foreground)
  → py-test-bot (new_tests + final, foreground/background)
  → py-doc-bot (docstrings + provider docs, foreground)
  → py-audit-bot (final, foreground)
```

### 8.5. Composite pipeline

```
py-audit-bot (baseline, scope=seed + enricher pipelines, foreground)
  → py-plan-bot (composite plan, foreground)
  → py-config-bot (composite config: seed/enrichers/merge, foreground)
  → orchestrator (composite orchestrator, если требуется новый код)
  → py-test-bot (integration tests, foreground/background)
  → py-doc-bot (composite pipeline docs, foreground)
  → py-audit-bot (final, foreground)
```

______________________________________________________________________

## 9. Опорные документы

|| Документ                                               | Описание                                 |
|| ------------------------------------------------------ | ---------------------------------------- |
|| `.devin/agents/py-*/AGENT.md`                          | Спецификации субагентов для Devin CLI    |
|| `.devin/agents/DEVIN-RUNTIME.md`                        | Каноническая runtime mapping для Devin  |
|| `.devin/agents/ORCHESTRATION.md`                       | Каноническая orchestration карта Devin   |
|| `.codex/agents/CODEX-RUNTIME.md`                       | Codex reference mapping                 |
|| `.codex/agents/ORCHESTRATION.md`                       | Codex orchestration reference            |
|| `docs/00-project/RULES.md`                             | Архитектурные правила проекта            |
|| `docs/02-architecture/decisions/`                      | ADR-001..ADR-050                         |
|| `docs/00-project/glossary.md`                          | Терминология                             |

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
