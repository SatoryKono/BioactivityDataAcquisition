# ORCHESTRATION.md — Оркестрация команды subagent-ов BioETL

*Версия: 3.0 | Дата: 2026-02-08 | Supersedes v2.2 | Платформа: Claude Code CLI*

## 1. Обзор

Команда из **8 субагентов** (7 core + 1 специализированный diagram агент) обеспечивает полный жизненный цикл задачи разработки BioETL — от аудита текущего состояния до финальной верификации изменений. Основной агент (Claude Code) выступает оркестратором, делегируя работу субагентам через `Task` tool с параметром `subagent_type`.

**Запуск субагента:**
```
Task(subagent_type="py-audit-bot", prompt="...", model="opus")
```

| # | Субагент (`subagent_type`) | Model | Роль | Артефакт |
|:-:|----------------------------|-------|------|----------|
| I | **py-audit-bot** | opus | Baseline/final аудит, code review, arch guardian, API validation | `00-audit-baseline.md`, `07-audit-final.md` |
| II | **py-plan-bot** | opus | Планирование, декомпозиция, composite design | `01-plan-initial.md`, `03-plan-updated.md` |
| III | **py-test-bot** | sonnet | Тестирование | `02-test-baseline.md`, `05-test-final.md` |
| IV | **py-code-bot** | opus | Production-код, pipeline scaffolding | `04-refactoring-log.md` |
| V | **py-config-bot** | sonnet | Конфигурации (pipeline, DQ, filter, composite) | `04a-config-log.md` |
| VI | **py-debug-bot** | opus | Отладка падений | `04-refactoring-log.md` (debug-секции) |
| VII | **py-doc-bot** | sonnet | Документация, ADR management | `06-doc-update-log.md` |
| VIII | **py-diagram-bot** | sonnet | Mermaid diagrams, render pipeline, docx/pdf bundles | `06-doc-update-log.md` (diagram sections) |

### Разделение ответственности (файловые зоны)

| Субагент | Зона записи | Только чтение |
|----------|-------------|---------------|
| py-code-bot | `src/bioetl/`, `tests/` (scaffolding) | `configs/`, `docs/` |
| py-config-bot | `configs/` | `src/bioetl/`, `docs/` |
| py-doc-bot | `docs/`, docstrings в `src/` | `configs/`, `tests/` |
| py-test-bot | `tests/` | `src/bioetl/`, `configs/` |
| py-debug-bot | `src/bioetl/`, `tests/` (fixes) | `configs/`, `docs/` |
| py-audit-bot | — (read-only) | всё |
| py-plan-bot | — (read-only) | всё |
| py-diagram-bot | `docs/02-architecture/mmd-diagrams/`, `docs/02-architecture/diagram-descriptions/`, `scripts/diagrams/` | `src/bioetl/`, `configs/` |

### Определения субагентов

Файлы: `.claude/agents/py-*.md` — каждый содержит YAML-frontmatter (`name`, `description`, `model`) + полную спецификацию с инлайнированными знаниями. Оригинальные спецификации Codex сохранены в `.claude/agents/subagents/` как справочный материал.

---

## 2. Стандартный workflow задачи

```
┌─────────────────────────────────────────────────────────────────────┐
│                        СТАРТ ЗАДАЧИ                                 │
│                     task_id назначен                                │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ① py-audit-bot (baseline)   │──→ 00-audit-baseline.md
│  Аудит целевого фрагмента   │
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ② py-plan-bot (initial)     │──→ 01-plan-initial.md
│  Формирование плана RF-*    │
│  (+консолидация с user plan)│
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ③ py-test-bot (baseline)    │──→ 02-test-baseline.md
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
│ (цикл)      │──→ 04-refactoring-log.md (debug-секции)
└──────┬──────┘    │
       │           │
       ▼           │
┌──────────────┐   │
│ py-plan-bot  │   │
│ (update)     │──→ 03-plan-updated.md
└──────┬───────┘   │
       │           │
       ◄───────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  ④ РЕАЛИЗАЦИЯ (параллельно по зонам ответственности) │
│                                                       │
│  py-code-bot ─→ src/bioetl/  ──→ 04-refactoring-log.md│
│       │                                                │
│       ├─ (entity scaffolding?) ──→ py-config-bot        │
│       │                                                │
│  py-config-bot → configs/  ──→ 04a-config-log.md       │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────┐
│  ⑤ py-test-bot (final)       │──→ 05-test-final.md
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
│  ⑥ py-doc-bot                │──→ 06-doc-update-log.md
│  Обновление docs/docstrings │
└─────────────────┬───────────┘
                  │
                  ▼
┌─────────────────────────────┐
│  ⑦ py-audit-bot (final)      │──→ 07-audit-final.md
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

---

## 3. Матрица взаимодействий

| Отправитель → | py-plan-bot | py-test-bot | py-code-bot | py-config-bot | py-debug-bot | py-doc-bot | py-audit-bot |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **py-audit-bot** | findings → RF-* | — | — | config gaps | — | drift findings | — |
| **py-plan-bot** | — | scope RF-* | RF-* to implement | config RF-* | — | — | scope |
| **py-test-bot** | — | — | — | — | FAIL report | — | — |
| **py-code-bot** | need new RF-* | — | — | entity scaffolding | — | — | — |
| **py-config-bot** | — | config tests | — | — | — | DQ migration docs | — |
| **py-debug-bot** | plan update | retest trigger | fix code | fix config | — | fix → doc | fix → re-audit |
| **py-doc-bot** | — | — | — | — | — | — | terminology check |

### Ключевые потоки данных

```
py-plan-bot (RF-*)
    ├──→ py-code-bot (type=refactor|feature|bugfix → src/)
    ├──→ py-config-bot (type=config → configs/)
    └──→ py-test-bot (test impact → tests/)

py-code-bot (entity scaffolding)
    └──→ py-config-bot (pipeline + DQ + filter configs)

py-audit-bot (config findings)
    └──→ py-config-bot (gap remediation)

py-config-bot (DQ migration)
    └──→ py-doc-bot (update DQ documentation)
```

---

## 4. Структура артефактов

```
reports/plans/<task_id>/
├── 00-audit-baseline.md      ← py-audit-bot (baseline)
├── 01-plan-initial.md        ← py-plan-bot (initial)
├── 02-test-baseline.md       ← py-test-bot (baseline)
├── 03-plan-updated.md        ← py-plan-bot (update)          [опционально]
├── 04-refactoring-log.md     ← py-code-bot + py-debug-bot
├── 04a-config-log.md         ← py-config-bot
├── 05-test-final.md          ← py-test-bot (final)
├── 06-doc-update-log.md      ← py-doc-bot
└── 07-audit-final.md         ← py-audit-bot (final)
```

Требования к каждому файлу (минимум):

- Дата/время создания
- Scope (файлы/модули)
- Команды верификации
- Ссылки на `RF-*` / `DBG-*` / `AUD-*` / `DOC-*` / `CFG-*` идентификаторы
- Severity (если применимо): `MUST` / `SHOULD` / `MAY`
- Статус: `done` / `in_progress` / `blocked` / `escalated`

---

## 5. Протоколы принятия решений

### 5.1. Когда пропустить шаг

| Шаг | Можно пропустить если |
|-----|----------------------|
| py-audit-bot baseline | Задача = чистый bugfix одного файла, scope очевиден |
| py-plan-bot | Задача = single-file doc update |
| py-test-bot baseline | Нет существующих тестов для scope (→ сразу new_tests) |
| py-code-bot | Задача = чистый config/doc change |
| py-config-bot | Задача не затрагивает configs/ |
| py-debug-bot | Все тесты проходят |
| py-doc-bot | Задача не меняет публичный API / поведение |
| py-audit-bot final | Задача = чистый doc update без code changes |

### 5.2. Маршрутизация RF-* по типу

| RF type | Primary subagent | Secondary |
|---------|:---:|:---:|
| `refactor` | py-code-bot | py-config-bot (если config impact) |
| `feature` | py-code-bot | py-config-bot (если новый entity) |
| `bugfix` | py-code-bot / py-debug-bot | py-config-bot (если config-related bug) |
| `config` | py-config-bot | — |
| `doc` | py-doc-bot | — |

### 5.3. Эскалация

| Ситуация | Действие |
|----------|----------|
| py-debug-bot: 5 итераций без fix | → `Requires Manual Review`, уведомить пользователя |
| py-audit-bot final: новый MUST | → Блокер, возврат к py-debug-bot/py-plan-bot |
| py-test-bot: coverage < 85% | → MUST: разработка тестов (phase=new_tests) |
| py-plan-bot: цикл зависимостей RF-* | → Пересмотр декомпозиции задачи |
| py-config-bot: gap_analysis critical > 0 | → Блокер, возврат к py-config-bot/py-plan-bot |

### 5.4. Параллелизация

В Claude Code субагенты могут запускаться как параллельно (`run_in_background: true`), так и последовательно. Допустимые параллельные запуски:

- `py-test-bot` (baseline) ∥ `py-audit-bot` (baseline) — оба read-only
- `py-code-bot` ∥ `py-config-bot` — разные файловые зоны (src/ vs configs/)
- `py-doc-bot` ∥ `py-audit-bot` (final) — если doc changes не влияют на code audit scope

---

## 6. ID-системы

| Prefix | Subagent | Формат | Пример | Описание |
|--------|----------|--------|--------|----------|
| `RF-` | py-plan-bot | `RF-001` | RF-001 | Рефакторинг / изменение |
| `DBG-` | py-debug-bot | `DBG-001` | DBG-001 | Debug-итерация |
| `AUD-` | py-audit-bot | `AUD-001` | AUD-001 | Audit finding |
| `DOC-` | py-doc-bot | `DOC-001` | DOC-001 | Обновление документации |
| `FAIL-` | py-test-bot | `FAIL-001` | FAIL-001 | Упавший тест (в отчёте) |
| `CFG-` | py-config-bot | `CFG-001` | CFG-001 | Изменение конфигурации |

Все ID уникальны в пределах `task_id`. Cross-references: `DBG-001 → RF-002`, `DOC-003 → RF-001`, `CFG-001 → RF-003`.

---

## 7. Гарантии и инварианты

1. **Traceability**: каждое изменение в коде привязано к `RF-*`, каждый fix — к `DBG-*`, каждый doc update — к `DOC-*`, каждый config change — к `CFG-*`.
2. **Baseline/Final symmetry**: для каждого baseline-артефакта существует final-артефакт.
3. **No blind changes**: код не меняется без предварительного плана (`RF-*`).
4. **No untested changes**: каждый `RF-*` проверяется через `py-test-bot`.
5. **Architecture gate**: финальный аудит (`py-audit-bot`) является обязательным gate перед завершением задачи.
6. **Config compliance gate**: `config_gap_analysis.py` MUST иметь 0 critical findings после `py-config-bot`.
7. **Zone isolation**: py-code-bot пишет только в `src/`, py-config-bot — только в `configs/`, py-doc-bot — только в `docs/` + docstrings.

---

## 8. Упрощённые режимы

### 8.1. Quick-fix (single bug, low risk)

```
py-test-bot (baseline, scope=1 file)
→ py-code-bot (fix)
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
  → py-code-bot (domain entity + transformer + schema + adapter)
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
  → py-code-bot (composite orchestrator, если требуется новый код)
  → py-test-bot (integration tests)
  → py-doc-bot (composite pipeline docs)
  → py-audit-bot (final)
```

---

## 9. Опорные документы

| Документ | Описание |
|----------|----------|
| `.claude/agents/py-*.md` | Спецификации субагентов для Claude Code CLI |
| `.claude/agents/subagents/` | Оригинальные спецификации (справочный материал) |
| `.claude/rules/ai-selfreview-rules.md` | Правила автоматической самопроверки кода |
| `docs/00-project/RULES.md` | Архитектурные правила проекта |
| `docs/02-architecture/decisions/` | ADR-001..ADR-040 |
| `docs/00-project/glossary.md` | Терминология |
| `tests/architecture/` | Автоматические проверки инвариантов |
| `scripts/config_gap_analysis.py` | Автоматическая проверка конфигов |

---

## 9a. Инлайнированные знания

В Claude Code CLI навыки не загружаются из внешних файлов. Вместо этого ключевые знания инлайнированы непосредственно в файлы субагентов (`.claude/agents/py-*.md`), в секцию `## Инлайнированные знания`.

### 9a.1 Маппинг знаний на субагенты

| # | Субагент | Основные знания | Дополнительные |
|:-:|----------|----------------|----------------|
| I | py-audit-bot | ETL system auditing, code review | Software architecture, REST API validation |
| II | py-plan-bot | Software architecture | REST API, data engineering, composite pipelines |
| III | py-test-bot | Python testing (pytest, VCR.py) | Data engineering (Pandera, DQ) |
| IV | py-code-bot | Python development, pipeline scaffolding | REST API, composite pipelines |
| V | py-config-bot | Data engineering, YAML configs | REST API config |
| VI | py-debug-bot | Python debugging, RCA | REST API debugging, Pandera issues |
| VII | py-doc-bot | Technical writing, ADR management | Bioinformatics terminology |

### 9a.2 Rule References

Каждый файл субагента содержит секцию `## Rule References` с таблицами:

| Тип | Формат | Пример |
|-----|--------|--------|
| Правило RULES.md | `[RULES-§X.Y]` | `[RULES-§2.1]` — Hexagonal Architecture |
| ADR | `[ADR-NNN]` | `[ADR-010]` — Local-only deployment |
| Инвариант | `[INV:name]` | `[INV:IMPORT_DOMAIN]` — domain → ничего |

**Verification:** каждый rule reference сопровождается командой проверки (bash).

---

## 10. MCP & Tools Integration

### 10.1 Матрица MCP-серверы × Субагенты

Каждый субагент имеет доступ к MCP-серверам через `ToolSearch`. Полные описания сценариев — в соответствующих `.claude/agents/py-*.md`, секция `## MCP Tools`.

> **Примечание:** Перед использованием MCP инструментов необходимо вызвать `ToolSearch("<provider>")` для загрузки.

| MCP Server | py-audit-bot | py-plan-bot | py-test-bot | py-code-bot | py-config-bot | py-debug-bot | py-doc-bot |
|------------|:----------:|:---------:|:---------:|:---------:|:-----------:|:----------:|:--------:|
| **ChEMBL** | ✅ Schema validation | — | ✅ Golden data, contracts | ✅ API reference | ✅ Field reference | ✅ Error repro | — |
| **PubMed** | — | ✅ Coverage eval | ✅ Test data | ✅ Publication ref | — | — | ✅ Citations |
| **bioRxiv** | — | ✅ Trends, research | ✅ Preprint test data | — | — | — | ✅ Context |
| **Open Targets** | ✅ Target validation | ✅ Data availability | — | ✅ GraphQL schema | ✅ Join key validation | — | — |
| **Mermaid Chart** | ✅ Arch diagrams | — | — | — | — | — | ✅ All diagrams |
| **BioRender** | — | — | — | — | — | — | ✅ Scientific figs |

### 10.2 Матрица Platform Tools × Субагенты

| Tool | py-audit-bot | py-plan-bot | py-test-bot | py-code-bot | py-config-bot | py-debug-bot | py-doc-bot |
|------|:----------:|:---------:|:---------:|:---------:|:-----------:|:----------:|:--------:|
| `WebSearch` | Docs | Research | — | Lib docs | Schema docs | Solutions | API docs |
| `WebFetch` | Pages | Pages | — | Pages | — | SO/GH Issues | Pages |

### 10.3 Протокол использования MCP

**В Claude Code CLI:**

1. Субагент определяет, нужны ли MCP-вызовы для текущей задачи (по таблице §10.1)
2. Вызывает `ToolSearch("<provider>")` для загрузки MCP инструментов
3. Использует загруженные инструменты напрямую
4. Результат MCP → input для анализа (findings, reference data, test data)

**Правила:**

- MCP-вызовы **опциональны** — субагент работает и без них
- MCP используется для **верификации** (schema drift, contract testing), **не для production data flow**
- Результаты MCP **не кэшируются между сессиями** — каждый вызов fresh
- При ошибке MCP → субагент продолжает работу без MCP data, помечает `[...] MCP недоступен`

### 10.4 Типовые MCP workflows

| Workflow | Агент | Trigger | MCP Tools | Output |
|----------|-------|---------|-----------|--------|
| Schema Drift Detection | py-audit-bot | audit ChEMBL pipeline | ChEMBL:compound_search → compare with entity | AUD-SCHEMA-* |
| Golden Dataset Generation | py-test-bot | new_tests for ChEMBL | ChEMBL:compound_search/get_bioactivity → save | tests/golden/*.json |
| Contract Testing | py-test-bot | final (ChEMBL scope) | ChEMBL MCP → compare with contract | FAIL-CONTRACT-* |
| Research Context | py-plan-bot | new entity planning | bioRxiv:search_preprints → analyze | 01-plan §Research Context |
| Documentation Diagrams | py-doc-bot | DOC-* for architecture | Mermaid:validate_and_render → save | docs/diagrams/*.svg |
| API Reference | py-code-bot | new adapter implementation | ChEMBL/OT/PubMed → study response | Field mapping in code |
| Config Fields Validation | py-config-bot | new pipeline config | ChEMBL MCP → compare fields | CFG-DRIFT-* |
| Error Reproduction | py-debug-bot | DBG-* for API failure | ChEMBL MCP → reproduce request | DBG-* root cause |

---

## 11. Changelog (ORCHESTRATION.md)

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
- **NEW**: §5.2 — маршрутизация RF-* по типу изменения
- **NEW**: §7.6 — config compliance gate
- **NEW**: §7.7 — zone isolation
- **CHANGED**: Шаг ⑤ (ранее «рефакторинг») → шаг ④ «реализация» с параллельным py-code-bot + py-config-bot
- **CHANGED**: Матрица взаимодействий расширена до 7×7
- **CHANGED**: Счёт subagent-ов: 5 → 7

### v1.0 (2026-02-07)

- Initial release: py-audit-bot, py-plan-bot, py-test-bot, py-debug-bot, py-doc-bot
