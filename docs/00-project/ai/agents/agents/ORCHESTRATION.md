______________________________________________________________________

Version: 4.2.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-04'

______________________________________________________________________

# ORCHESTRATION.md — Оркестрация команды subagent-ов BioETL

*Версия: 4.2 | Дата: 2026-03-26 | Supersedes v4.1 | Платформа: Codex CLI*

## 1. Обзор

Команда из **9 активных субагентов** (7 core + 2 orchestrator/swarm) обеспечивает полный жизненный цикл задачи разработки BioETL. Основной агент (Codex) выступает оркестратором, делегируя работу субагентам через native agent roles (`default` / `explorer` / `worker`) с привязкой к логическим профилям `py-*`. Production-код пишется напрямую оркестратором (без отдельного `py-code-bot`).

**Запуск логического профиля в Codex runtime:**

```
spawn_agent(
  agent_type="default",
  message="Follow .codex/agents/py-audit-bot.md for task_id=AUD-001, phase=baseline, scope=src/bioetl/application/."
)
```

> Runtime mapping: см. `.codex/agents/CODEX-RUNTIME.md`.

|  #   | Субагент (`subagent_type`)   | Model  | Роль                                                                                   | Артефакт                                               |
| :--: | ---------------------------- | ------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------ |
|  I   | **py-audit-bot**             | opus   | Baseline/final аудит, code review, arch guardian, API validation                       | `review_py-audit-bot_{YYYYMMDD}_{HHMM}_{phase}.md`     |
|  II  | **py-architecture-debt-bot** | opus   | Полный workflow устранения архитектурного долга: generate -> plan -> execute -> verify | `review_py-architecture-debt-bot_{YYYYMMDD}_{HHMM}.md` |
| III  | **py-plan-bot**              | opus   | Планирование, декомпозиция, composite design                                           | `review_py-plan-bot_{YYYYMMDD}_{HHMM}.md`              |
|  IV  | **py-test-bot**              | sonnet | Тестирование                                                                           | `review_py-test-bot_{YYYYMMDD}_{HHMM}.md`              |
|  V   | **py-config-bot**            | sonnet | Конфигурации (pipeline, DQ, filter, composite)                                         | `review_py-config-bot_{YYYYMMDD}_{HHMM}.md`            |
|  VI  | **py-debug-bot**             | opus   | Отладка падений                                                                        | `review_py-debug-bot_{YYYYMMDD}_{HHMM}.md`             |
| VII  | **py-doc-bot**               | sonnet | Документация, ADR, диаграммы (Mermaid)                                                 | `review_py-doc-bot_{YYYYMMDD}_{HHMM}.md`               |
| VIII | **py-test-swarm**            | opus   | Иерархическое тестирование (L1→L2→L3)                                                  | test reports                                           |
|  IX  | **py-review-orchestrator**   | opus   | Иерархический code review (S1-S8)                                                      | review reports                                         |

> **Note:** `py-code-bot` removed in v4.0 — production code is written directly by the orchestrator. `py-diagram-bot` merged into `py-doc-bot`. Repo-wide documentation audits now route through the `documentation-audit` / `documentation-cascade-audit` skills rather than a dedicated documentation-only subagent profile.

### Разделение ответственности (файловые зоны)

| Субагент                 | Зона записи                                                           | Только чтение                         |
| ------------------------ | --------------------------------------------------------------------- | ------------------------------------- |
| orchestrator (direct)    | `src/bioetl/`, `tests/`                                               | `configs/`, `docs/`                   |
| py-architecture-debt-bot | `src/bioetl/`, `tests/`, `reports/quality/`, root task JSON artifacts | `configs/`, `docs/` (edits delegated) |
| py-config-bot            | `configs/`                                                            | `src/bioetl/`, `docs/`                |
| py-doc-bot               | `docs/`, docstrings, `docs/00-project/ai/agents/scripts/diagrams/`    | `configs/`, `tests/`                  |
| py-test-bot              | `tests/`                                                              | `src/bioetl/`, `configs/`             |
| py-debug-bot             | `src/bioetl/`, `tests/` (fixes)                                       | `configs/`, `docs/`                   |
| py-audit-bot             | — (read-only)                                                         | всё                                   |
| py-plan-bot              | — (read-only)                                                         | всё                                   |

### Определения субагентов

Файлы: `.codex/agents/py-*.md` — каждый содержит YAML-frontmatter (`name`, `description`, `model`) + полную спецификацию с инлайнированными знаниями.

## 1.1 Evidence Calibration

Перед repo-wide structural выводами, hotspot-программами и package-reorg инициативами сверяйся с текущими evidence packs:

- [Project File Structure Summary](../../../../reports/evidence/project-file-structure/SUMMARY.md)
- [Project Package Topology Summary](../../../../reports/evidence/project-package-topology/SUMMARY.md)
- [Governance Signals Summary](../../../../reports/evidence/governance-signals/SUMMARY.md)
- [Governance Signals Decisions](../../../../reports/evidence/governance-signals/04-decisions/SUMMARY.md)

Operational defaults:

- package count сам по себе не является refactor trigger;
- family-level topology важнее whole-layer breadth;
- topology показывает, где смотреть, а governance signals — где реально действовать.

## 1.2 Memory-Enabled Task Loop

Перед стандартным subagent workflow оркестратор и role-specific profiles должны
использовать canonical memory loop из `src/memory/DAILY_WORKFLOW.md`.

Минимальный порядок:

1. `python -m memory.tooling.workflow pre-task --task-id <id> --title "<task>"`
1. retrieval order: `catalog -> graph -> rag -> source`
1. baseline/profile-specific work
1. `python -m memory.tooling.workflow post-task --task-id <id> --title "<task>" --summary "<result>"`
1. promotion только для durable knowledge

Это не заменяет runtime source или `.codex/agents/*.md`, а стандартизирует:

- pre-task retrieval
- session-note creation
- post-task summary
- refresh rebuild-only memory artifacts
- optional promotion into curated memory
- periodic curated review via `python -m memory.tooling.workflow review-curated`
- archive of superseded curated notes instead of silent stale accumulation

Regular ritual rule:

- run `review-curated` on a recurring engineering cadence
- run it again before release-readiness, governance, or architecture-review checkpoints
- treat `due` notes as verification work and `stale` notes as review-or-archive candidates

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
│  Аудит целевого фрагмента   │
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ② py-plan-bot (initial)     │──→ review_py-plan-bot_{YYYYMMDD}_{HHMM}.md
│  Формирование плана RF-*    │
│  (+консолидация с user plan)│
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ③ py-test-bot (baseline)    │──→ review_py-test-bot_{YYYYMMDD}_{HHMM}.md
│  Фиксация состояния тестов  │
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
│  Финальный прогон тестов    │
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
│  Обновление docs/docstrings │
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ⑦ py-audit-bot (final)      │──→ review_py-audit-bot_{YYYYMMDD}_{HHMM}_final.md
│  Финальная верификация       │
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

|   Отправитель →   |   py-plan-bot    |  py-test-bot   | py-config-bot | py-debug-bot |    py-doc-bot     |   py-audit-bot    |
| :---------------: | :--------------: | :------------: | :-----------: | :----------: | :---------------: | :---------------: |
| **py-audit-bot**  | findings → RF-\* |       —        |  config gaps  |      —       |  drift findings   |         —         |
|  **py-plan-bot**  |        —         |  scope RF-\*   | config RF-\*  |      —       |         —         |       scope       |
|  **py-test-bot**  |        —         |       —        |       —       | FAIL report  |         —         |         —         |
| **py-config-bot** |        —         |  config tests  |       —       |      —       | DQ migration docs |         —         |
| **py-debug-bot**  |   plan update    | retest trigger |  fix config   |      —       |     fix → doc     |  fix → re-audit   |
|  **py-doc-bot**   |        —         |       —        |       —       |      —       |         —         | terminology check |

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

Правило: любой агент/субагент формирует итоговый отчёт только по этому пути
(LLM = вызывающая модель, agent = профиль/skill, `phase` — опциональный
суффикс для baseline/final/targeted, если это закреплено в contract
конкретного `py-*` профиля). Дополнительные артефакты (телеметрия, метрики,
промежуточные планы) сохраняйте рядом в той же директории, но итоговый отчёт
должен соответствовать шаблону
`reports/{LLM}/review_{agent}_{YYYYMMDD}_{HHMM}[_{phase}].md`.

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

| Шаг                   | Можно пропустить если                                 |
| --------------------- | ----------------------------------------------------- |
| py-audit-bot baseline | Задача = чистый bugfix одного файла, scope очевиден   |
| py-plan-bot           | Задача = single-file doc update                       |
| py-test-bot baseline  | Нет существующих тестов для scope (→ сразу new_tests) |
| orchestrator code     | Задача = чистый config/doc change                     |
| py-config-bot         | Задача не затрагивает configs/                        |
| py-debug-bot          | Все тесты проходят                                    |
| py-doc-bot            | Задача не меняет публичный API / поведение            |
| py-audit-bot final    | Задача = чистый doc update без code changes           |

### 5.2. Маршрутизация RF-\* по типу

| RF type    |      Primary subagent       |                Secondary                |
| ---------- | :-------------------------: | :-------------------------------------: |
| `refactor` |        orchestrator         |   py-config-bot (если config impact)    |
| `feature`  |        orchestrator         |    py-config-bot (если новый entity)    |
| `bugfix`   | orchestrator / py-debug-bot | py-config-bot (если config-related bug) |
| `config`   |        py-config-bot        |                    —                    |
| `doc`      |         py-doc-bot          |                    —                    |

### 5.3. Эскалация

| Ситуация                                 | Действие                                           |
| ---------------------------------------- | -------------------------------------------------- |
| py-debug-bot: 5 итераций без fix         | → `Requires Manual Review`, уведомить пользователя |
| py-audit-bot final: новый MUST           | → Блокер, возврат к py-debug-bot/py-plan-bot       |
| py-test-bot: coverage < 85%              | → MUST: разработка тестов (phase=new_tests)        |
| py-plan-bot: цикл зависимостей RF-\*     | → Пересмотр декомпозиции задачи                    |
| py-config-bot: gap_analysis critical > 0 | → Блокер, возврат к py-config-bot/py-plan-bot      |

### 5.4. Параллелизация

В Claude Code субагенты могут запускаться как параллельно (`run_in_background: true`), так и последовательно. Допустимые параллельные запуски:

- `py-test-bot` (baseline) ∥ `py-audit-bot` (baseline) — оба read-only
- `orchestrator` ∥ `py-config-bot` — разные файловые зоны (src/ vs configs/)
- `py-doc-bot` ∥ `py-audit-bot` (final) — если doc changes не влияют на code audit scope

______________________________________________________________________

## 6. ID-системы

| Prefix  | Subagent      | Формат     | Пример   | Описание                |
| ------- | ------------- | ---------- | -------- | ----------------------- |
| `RF-`   | py-plan-bot   | `RF-001`   | RF-001   | Рефакторинг / изменение |
| `DBG-`  | py-debug-bot  | `DBG-001`  | DBG-001  | Debug-итерация          |
| `AUD-`  | py-audit-bot  | `AUD-001`  | AUD-001  | Audit finding           |
| `DOC-`  | py-doc-bot    | `DOC-001`  | DOC-001  | Обновление документации |
| `FAIL-` | py-test-bot   | `FAIL-001` | FAIL-001 | Упавший тест (в отчёте) |
| `CFG-`  | py-config-bot | `CFG-001`  | CFG-001  | Изменение конфигурации  |

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

______________________________________________________________________

## 8. Упрощённые режимы

### 8.1. Quick-fix (single bug, low risk)

```
py-test-bot (baseline, scope=1 file)
→ orchestrator (fix)
→ py-test-bot (final)
→ py-doc-bot (docstring only)
```

### 8.2. Doc-only

```
py-doc-bot (создание/обновление)
  → py-audit-bot (targeted, audit_type=docs)
```

### 8.3. Config-only

```
py-audit-bot (targeted, audit_type=config)
  → py-plan-bot (plan)
  → py-config-bot (изменение configs)
  → py-test-bot (final, scope=config-related tests)
  → py-audit-bot (final)
```

### 8.4. New entity (full scaffolding)

```
py-plan-bot (plan)
  → orchestrator (domain entity + transformer + schema + adapter)
  → py-config-bot (pipeline + DQ + filter + source configs)
  → py-test-bot (new_tests + final)
  → py-doc-bot (docstrings + provider docs)
  → py-audit-bot (final)
```

### 8.5. Composite pipeline

```
py-audit-bot (baseline, scope=seed + enricher pipelines)
  → py-plan-bot (composite plan)
  → py-config-bot (composite config: seed/enrichers/merge)
  → orchestrator (composite orchestrator, если требуется новый код)
  → py-test-bot (integration tests)
  → py-doc-bot (composite pipeline docs)
  → py-audit-bot (final)
```

______________________________________________________________________

## 9. Опорные документы

| Документ                                               | Описание                                 |
| ------------------------------------------------------ | ---------------------------------------- |
| `.codex/agents/py-*.md`                                | Спецификации субагентов для Codex CLI    |
| `ai/claude/rules/agent-orchestration-rules.md`         | Claude runtime orchestration compatibility rules |
| `docs/00-project/RULES.md`                             | Архитектурные правила проекта            |
| `docs/02-architecture/decisions/`                      | ADR-001..ADR-043                         |
| `docs/00-project/glossary.md`                          | Терминология                             |
| `tests/architecture/`                                  | Автоматические проверки инвариантов      |
| `docs/00-project/ai/agents/scripts/py-config-bot-1.py` | Автоматическая проверка конфигов         |

______________________________________________________________________

## 9a. Инлайнированные знания

В Codex CLI ключевые знания для BioETL-профилей инлайнированы непосредственно в файлы субагентов (`.codex/agents/py-*.md`) и подключаются через skill wrappers в `.codex/skills/`.

### 9a.1 Маппинг знаний на субагенты

|  #  | Субагент      | Основные знания                  | Дополнительные                                  |
| :-: | ------------- | -------------------------------- | ----------------------------------------------- |
|  I  | py-audit-bot  | ETL system auditing, code review | Software architecture, REST API validation      |
| II  | py-plan-bot   | Software architecture            | REST API, data engineering, composite pipelines |
| III | py-test-bot   | Python testing (pytest, VCR.py)  | Data engineering (Pandera, DQ)                  |
| IV  | py-config-bot | Data engineering, YAML configs   | REST API config                                 |
|  V  | py-debug-bot  | Python debugging, RCA            | REST API debugging, Pandera issues              |
| VI  | py-doc-bot    | Technical writing, ADR, diagrams | Bioinformatics terminology, Mermaid             |

### 9a.2 Rule References

Каждый файл субагента содержит секцию `## Rule References` с таблицами:

| Тип              | Формат         | Пример                                  |
| ---------------- | -------------- | --------------------------------------- |
| Правило RULES.md | `[RULES-§X.Y]` | `[RULES-§2.1]` — Hexagonal Architecture |
| ADR              | `[ADR-NNN]`    | `[ADR-010]` — Local-only deployment     |
| Инвариант        | `[INV:name]`   | `[INV:IMPORT_DOMAIN]` — domain → ничего |

**Verification:** каждый rule reference сопровождается командой проверки (bash).

______________________________________________________________________

## 10. MCP & Tools Integration

### 10.1 Матрица MCP-серверы × Субагенты

Каждый субагент имеет доступ к MCP-серверам через runtime tooling. Полные описания сценариев — в соответствующих `.codex/agents/py-*.md`, секция `## MCP Tools`.

> **Примечание:** Перед использованием MCP инструментов необходимо вызвать `ToolSearch("<provider>")` для загрузки.

| MCP Server        |     py-audit-bot     |     py-plan-bot     |        py-test-bot        |   py-config-bot    |  py-debug-bot  |     py-doc-bot     |
| ----------------- | :------------------: | :-----------------: | :-----------------------: | :----------------: | :------------: | :----------------: |
| **ChEMBL**        | ✅ Schema validation |          —          | ✅ Golden data, contracts | ✅ Field reference | ✅ Error repro |         —          |
| **PubMed**        |          —           |  ✅ Coverage eval   |       ✅ Test data        |         —          |       —        |    ✅ Citations    |
| **bioRxiv**       |          —           | ✅ Trends, research |   ✅ Preprint test data   |         —          |       —        |     ✅ Context     |
| **Mermaid Chart** |   ✅ Arch diagrams   |          —          |             —             |         —          |       —        |  ✅ All diagrams   |
| **BioRender**     |          —           |          —          |             —             |         —          |       —        | ✅ Scientific figs |

### 10.2 Матрица Platform Tools × Субагенты

| Tool        | py-audit-bot | py-plan-bot | py-test-bot | py-config-bot | py-debug-bot | py-doc-bot |
| ----------- | :----------: | :---------: | :---------: | :-----------: | :----------: | :--------: |
| `WebSearch` |     Docs     |  Research   |      —      |  Schema docs  |  Solutions   |  API docs  |
| `WebFetch`  |    Pages     |    Pages    |      —      |       —       | SO/GH Issues |   Pages    |

### 10.3 Протокол использования MCP

**В Claude Code CLI:**

1. Субагент определяет, нужны ли MCP-вызовы для текущей задачи (по таблице §10.1)
1. Вызывает `ToolSearch("<provider>")` для загрузки MCP инструментов
1. Использует загруженные инструменты напрямую
1. Результат MCP → input для анализа (findings, reference data, test data)

**Правила:**

- MCP-вызовы **опциональны** — субагент работает и без них
- MCP используется для **верификации** (schema drift, contract testing), **не для production data flow**
- Результаты MCP **не кэшируются между сессиями** — каждый вызов fresh
- При ошибке MCP → субагент продолжает работу без MCP data, помечает `[...] MCP недоступен`

### 10.4 Типовые MCP workflows

| Workflow                  | Агент         | Trigger                    | MCP Tools                                     | Output                    |
| ------------------------- | ------------- | -------------------------- | --------------------------------------------- | ------------------------- |
| Schema Drift Detection    | py-audit-bot  | audit ChEMBL pipeline      | ChEMBL:compound_search → compare with entity  | AUD-SCHEMA-\*             |
| Golden Dataset Generation | py-test-bot   | new_tests for ChEMBL       | ChEMBL:compound_search/get_bioactivity → save | tests/golden/\*.json      |
| Contract Testing          | py-test-bot   | final (ChEMBL scope)       | ChEMBL MCP → compare with contract            | FAIL-CONTRACT-\*          |
| Research Context          | py-plan-bot   | new entity planning        | bioRxiv:search_preprints → analyze            | 01-plan §Research Context |
| Documentation Diagrams    | py-doc-bot    | DOC-\* for architecture    | Mermaid:validate_and_render → save            | docs/diagrams/\*.svg      |
| API Reference             | orchestrator  | new adapter implementation | ChEMBL/OT/PubMed → study response             | Field mapping in code     |
| Config Fields Validation  | py-config-bot | new pipeline config        | ChEMBL MCP → compare fields                   | CFG-DRIFT-\*              |
| Error Reproduction        | py-debug-bot  | DBG-\* for API failure     | ChEMBL MCP → reproduce request                | DBG-\* root cause         |

______________________________________________________________________

## 11. Changelog (ORCHESTRATION.md)

### v4.2 (2026-03-26)

- **CHANGED**: active agent table no longer lists the legacy documentation-only subagent
- **CHANGED**: repo-wide docs audits now point to `documentation-audit` / `documentation-cascade-audit`
- **CHANGED**: active agent count updated to 8 (6 core + 2 orchestrator/swarm)

### v4.1 (2026-03-10)

- **PLATFORM**: основной runtime зафиксирован как Codex CLI
- **ADDED**: `.codex/agents/CODEX-RUNTIME.md` для маппинга logical profiles → native agent roles
- **CHANGED**: source-of-truth ссылки переключены на `.codex/agents/`
- **CHANGED**: примеры запуска адаптированы под `spawn_agent(...)`

### v4.0 (2026-03-04)

> Исторический changelog ниже является non-normative. Для текущего workflow ориентируйся на разделы выше и на note о том, что production-код пишет orchestrator напрямую.

- **REMOVED**: `py-code-bot` — production code now written directly by orchestrator
- **MERGED**: `py-diagram-bot` into `py-doc-bot` (diagrams are documentation artifacts)
- **ADDED**: `py-test-swarm`, docs-audit orchestration track, `py-review-orchestrator` to agent table
- **REMOVED**: `.claude/agents/subagents/` reference (deleted in Phase 1)
- **CHANGED**: Agent count: 8 → 9 (6 core + 3 orchestrator/swarm)
- **CHANGED**: All workflow references updated: py-code-bot → orchestrator
- **CHANGED**: MCP matrices reduced from 7×7 to 6×6

### v3.0 (2026-02-08)

- **PLATFORM**: Адаптация для Claude Code CLI (ранее Codex/Claude.ai)
- **CHANGED**: Все субагенты переименованы: `pyXxxBot` → `py-xxx-bot` (для `subagent_type` в Task tool)
- **CHANGED**: 8 старых Claude Code агентов заменены на 7 унифицированных: `py-audit-bot`, `py-plan-bot`, `py-test-bot`, `py-code-bot`, `py-config-bot`, `py-debug-bot`, `py-doc-bot`
- **CHANGED**: Навыки из `/mnt/skills/` инлайнированы в файлы субагентов (секция `## Инлайнированные знания`)
- **REMOVED**: `google_drive_search`, `message_compose`, `ask_user_input` (недоступны в CLI)
- **CHANGED**: `web_search` / `web_fetch` → `WebSearch` / `WebFetch` (встроенные инструменты Claude Code)
- **CHANGED**: MCP инструменты доступны через `ToolSearch` (deferred loading)
- **CHANGED**: §9a — Skill Activation Protocol → Инлайнированные знания
- **NEW**: Ссылки на `.claude/agents/py-*.md` вместо `SUBAGENT.md`

### v2.2 (2026-02-07)

- **NEW**: §10 — MCP & Tools Integration (матрицы 7×7 для MCP-серверов и Platform Tools)
- **NEW**: Секция `## MCP Tools` добавлена во все 7 SUBAGENT.md (сценарии, workflows, параметры)
- **NEW**: Секция `## Platform Tools` добавлена во все 7 SUBAGENT.md (web_search, ask_user_input, google_drive_search)
- **NEW**: §10.3 — протокол использования MCP (опциональность, верификация, fallback)
- **NEW**: §10.4 — 8 типовых MCP workflows (schema drift, golden data, contract testing, etc.)
- **CHANGED**: §10 (Changelog) → §11 (ренумерация)

### v2.1 (2026-02-07)

- **NEW**: §9a — Skill Activation Protocol (маппинг 7 навыков на 7 субагентов)
- **NEW**: Секция `## Skills` добавлена во все 7 SUBAGENT.md (primary + secondary skills с путями и триггерами)
- **NEW**: Секция `## Rule References` добавлена во все 7 SUBAGENT.md ([RULES-§], [ADR-], [INV:], [GLOSS:])
- **NEW**: §9a.3 — формат ссылок на правила с verification-командами

### v2.0 (2026-02-07)

- **NEW**: `py-code-bot` — написание production-кода (`src/bioetl/`), файловая зона `src/`
- **NEW**: `py-config-bot` — управление конфигурациями (`configs/`), файловая зона `configs/`
- **NEW**: ID-prefix `CFG-` для config changes
- **NEW**: Артефакт `04a-config-log.md`
- **NEW**: Упрощённые режимы: `new-entity` (§8.4), `composite-pipeline` (§8.5)
- **NEW**: §5.2 — маршрутизация RF-\* по типу изменения
- **NEW**: §7.6 — config compliance gate
- **NEW**: §7.7 — zone isolation
- **CHANGED**: Шаг ⑤ (ранее «рефакторинг») → шаг ④ «реализация» с параллельным py-code-bot + py-config-bot
- **CHANGED**: Матрица взаимодействий расширена до 7×7
- **CHANGED**: Счёт subagent-ов: 5 → 7

### v1.0 (2026-02-07)

- Initial release: py-audit-bot, py-plan-bot, py-test-bot, py-debug-bot, py-doc-bot
