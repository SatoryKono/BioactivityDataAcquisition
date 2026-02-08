# ORCHESTRATION.md — Оркестрация команды subagent-ов BioETL

*Версия: 3.0 | Дата: 2026-02-08 | Supersedes v2.2 | Платформа: Claude Code CLI*

## 1. Обзор

Команда из **7 субагентов** обеспечивает полный жизненный цикл задачи разработки BioETL — от аудита текущего состояния до финальной верификации изменений. Основной агент (Claude Code) выступает оркестратором, делегируя работу субагентам через `Task` tool с параметром `subagent_type`.

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
│ pyDebugBot│     │     │
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
| pyAuditBot baseline | Задача = чистый bugfix одного файла, scope очевиден |
| pyPlanBot | Задача = single-file doc update |
| pyTestBot baseline | Нет существующих тестов для scope (→ сразу new_tests) |
| pyCodeBot | Задача = чистый config/doc change |
| pyConfigBot | Задача не затрагивает configs/ |
| pyDebugBot | Все тесты проходят |
| pyDocBot | Задача не меняет публичный API / поведение |
| pyAuditBot final | Задача = чистый doc update без code changes |

### 5.2. Маршрутизация RF-* по типу

| RF type | Primary subagent | Secondary |
|---------|:---:|:---:|
| `refactor` | pyCodeBot | pyConfigBot (если config impact) |
| `feature` | pyCodeBot | pyConfigBot (если новый entity) |
| `bugfix` | pyCodeBot / pyDebugBot | pyConfigBot (если config-related bug) |
| `config` | pyConfigBot | — |
| `doc` | pyDocBot | — |

### 5.3. Эскалация

| Ситуация | Действие |
|----------|----------|
| pyDebugBot: 5 итераций без fix | → `Requires Manual Review`, уведомить пользователя |
| pyAuditBot final: новый MUST | → Блокер, возврат к pyDebugBot/pyPlanBot |
| pyTestBot: coverage < 85% | → MUST: разработка тестов (phase=new_tests) |
| pyPlanBot: цикл зависимостей RF-* | → Пересмотр декомпозиции задачи |
| pyConfigBot: gap_analysis critical > 0 | → Блокер, возврат к pyConfigBot/pyPlanBot |

### 5.4. Параллелизация

В текущей модели (sequential Codex) subagent-ы работают последовательно. При наличии параллельного исполнения допустимо:

- `pyTestBot` (baseline) ∥ `pyAuditBot` (baseline) — оба read-only
- `pyCodeBot` ∥ `pyConfigBot` — разные файловые зоны (src/ vs configs/)
- `pyDocBot` ∥ `pyAuditBot` (final) — если doc changes не влияют на code audit scope

---

## 6. ID-системы

| Prefix | Subagent | Формат | Пример | Описание |
|--------|----------|--------|--------|----------|
| `RF-` | pyPlanBot | `RF-001` | RF-001 | Рефакторинг / изменение |
| `DBG-` | pyDebugBot | `DBG-001` | DBG-001 | Debug-итерация |
| `AUD-` | pyAuditBot | `AUD-001` | AUD-001 | Audit finding |
| `DOC-` | pyDocBot | `DOC-001` | DOC-001 | Обновление документации |
| `FAIL-` | pyTestBot | `FAIL-001` | FAIL-001 | Упавший тест (в отчёте) |
| `CFG-` | pyConfigBot | `CFG-001` | CFG-001 | Изменение конфигурации |

Все ID уникальны в пределах `task_id`. Cross-references: `DBG-001 → RF-002`, `DOC-003 → RF-001`, `CFG-001 → RF-003`.

---

## 7. Гарантии и инварианты

1. **Traceability**: каждое изменение в коде привязано к `RF-*`, каждый fix — к `DBG-*`, каждый doc update — к `DOC-*`, каждый config change — к `CFG-*`.
2. **Baseline/Final symmetry**: для каждого baseline-артефакта существует final-артефакт.
3. **No blind changes**: код не меняется без предварительного плана (`RF-*`).
4. **No untested changes**: каждый `RF-*` проверяется через `pyTestBot`.
5. **Architecture gate**: финальный аудит (`pyAuditBot`) является обязательным gate перед завершением задачи.
6. **Config compliance gate**: `config_gap_analysis.py` MUST иметь 0 critical findings после `pyConfigBot`.
7. **Zone isolation**: pyCodeBot пишет только в `src/`, pyConfigBot — только в `configs/`, pyDocBot — только в `docs/` + docstrings.

---

## 8. Упрощённые режимы

### 8.1. Quick-fix (single bug, low risk)

```
pyTestBot (baseline, scope=1 file)
  → pyCodeBot (fix)
  → pyTestBot (final)
  → pyDocBot (docstring only)
```

### 8.2. Doc-only

```
pyDocBot (создание/обновление)
  → pyAuditBot (targeted, audit_type=docs)
```

### 8.3. Config-only

```
pyAuditBot (targeted, audit_type=config)
  → pyPlanBot (plan)
  → pyConfigBot (изменение configs)
  → pyTestBot (final, scope=config-related tests)
  → pyAuditBot (final)
```

### 8.4. New entity (full scaffolding)

```
pyPlanBot (plan)
  → pyCodeBot (domain entity + transformer + schema + adapter)
  → pyConfigBot (pipeline + DQ + filter + source configs)
  → pyTestBot (new_tests + final)
  → pyDocBot (docstrings + provider docs)
  → pyAuditBot (final)
```

### 8.5. Composite pipeline

```
pyAuditBot (baseline, scope=seed + enricher pipelines)
  → pyPlanBot (composite plan)
  → pyConfigBot (composite config: seed/enrichers/merge)
  → pyCodeBot (composite orchestrator, если требуется новый код)
  → pyTestBot (integration tests)
  → pyDocBot (composite pipeline docs)
  → pyAuditBot (final)
```

---

## 9. Опорные документы

| Документ | Описание |
|----------|----------|
| `docs/00-project/agents/CODEX.md` | Основной регламент Codex |
| `docs/00-project/RULES.md` | Архитектурные правила проекта |
| `docs/02-architecture/decisions/` | ADR-001..ADR-028 |
| `docs/00-project/glossary.md` | Терминология |
| `tests/architecture/` | Автоматические проверки инвариантов |
| `scripts/config_gap_analysis.py` | Автоматическая проверка конфигов |

---

## 9a. Skill Activation Protocol

### 9a.1 Маппинг навыков на субагенты

Каждый субагент имеет primary skill (активируется всегда) и secondary skills (активируются контекстно). Полные описания — в соответствующих `SUBAGENT.md`.

| # | Субагент | Primary Skill | Secondary Skills |
|:-:|----------|---------------|------------------|
| I | pyAuditBot | `etl-system-auditor` | `python-software-architect` |
| II | pyPlanBot | `python-software-architect` | `etl-rest-api-expert`, `data-engineering` |
| III | pyTestBot | `senior-python-developer` | `data-engineering` |
| IV | pyCodeBot | `senior-python-developer` | `etl-rest-api-expert`, `python-software-architect` |
| V | pyConfigBot | `data-engineering` | `etl-rest-api-expert` |
| VI | pyDebugBot | `senior-python-developer` | `etl-rest-api-expert` |
| VII | pyDocBot | `python-tech-writer` | `bioinformatics-databases` |

### 9a.2 Протокол активации

**При запуске субагента оператор:**

1. Открывает SUBAGENT.md целевого агента
2. Читает секцию `## Skills` — определяет primary + релевантные secondary
3. Загружает SKILL.md файлы (`view /mnt/skills/user/<skill>/SKILL.md`)
4. Применяет инструкции навыка к текущей задаче

**Правила активации secondary skills:**

- Secondary активируется **только** если текущая задача попадает в описанные триггеры
- При конфликте между primary и secondary — приоритет у primary
- Навык `bioinformatics-databases` активируется при работе с domain-specific терминологией

### 9a.3 Rule References

Каждый SUBAGENT.md содержит секцию `## Rule References` с таблицами:

| Тип | Формат | Пример |
|-----|--------|--------|
| Правило RULES.md | `[RULES-§X.Y]` | `[RULES-§2.1]` — Hexagonal Architecture |
| ADR | `[ADR-NNN]` | `[ADR-010]` — Local-only deployment |
| Инвариант | `[INV:name]` | `[INV:IMPORT_DOMAIN]` — domain → ничего |
| Глоссарий | `[GLOSS:term]` | `[GLOSS:Molecule]` — ChEMBL terminology |

**Verification:** каждый rule reference сопровождается командой проверки (bash). При аудите pyAuditBot обязан выполнить все verification-команды для scope задачи.

### 9a.4 Навыки — пути

| Навык | Путь |
|-------|------|
| `etl-system-auditor` | `/mnt/skills/user/etl-system-auditor/SKILL.md` |
| `python-software-architect` | `/mnt/skills/user/python-software-architect/SKILL.md` |
| `senior-python-developer` | `/mnt/skills/user/senior-python-developer/SKILL.md` |
| `data-engineering` | `/mnt/skills/user/data-engineering/SKILL.md` |
| `etl-rest-api-expert` | `/mnt/skills/user/etl-rest-api-expert/SKILL.md` |
| `python-tech-writer` | `/mnt/skills/user/python-tech-writer/SKILL.md` |
| `bioinformatics-databases` | `/mnt/skills/user/bioinformatics-databases/SKILL.md` |

---

## 10. MCP & Tools Integration

### 10.1 Матрица MCP-серверы × Субагенты

Каждый субагент имеет доступ к MCP-серверам через платформу Claude.ai. Полные описания сценариев — в соответствующих `SUBAGENT.md`, секция `## MCP Tools`.

| MCP Server | pyAuditBot | pyPlanBot | pyTestBot | pyCodeBot | pyConfigBot | pyDebugBot | pyDocBot |
|------------|:----------:|:---------:|:---------:|:---------:|:-----------:|:----------:|:--------:|
| **ChEMBL** | ✅ Schema validation | — | ✅ Golden data, contracts | ✅ API reference | ✅ Field reference | ✅ Error repro | — |
| **PubMed** | — | ✅ Coverage eval | ✅ Test data | ✅ Publication ref | — | — | ✅ Citations |
| **bioRxiv** | — | ✅ Trends, research | ✅ Preprint test data | — | — | — | ✅ Context |
| **Open Targets** | ✅ Target validation | ✅ Data availability | — | ✅ GraphQL schema | ✅ Join key validation | — | — |
| **Mermaid Chart** | ✅ Arch diagrams | — | — | — | — | — | ✅ All diagrams |
| **BioRender** | — | — | — | — | — | — | ✅ Scientific figs |

### 10.2 Матрица Platform Tools × Субагенты

| Tool | pyAuditBot | pyPlanBot | pyTestBot | pyCodeBot | pyConfigBot | pyDebugBot | pyDocBot |
|------|:----------:|:---------:|:---------:|:---------:|:-----------:|:----------:|:--------:|
| `web_search` | ✅ Docs | ✅ Research | — | ✅ Lib docs | ✅ Schema docs | ✅ Solutions | ✅ API docs |
| `web_fetch` | ✅ | ✅ | — | ✅ | — | ✅ | ✅ |
| `google_drive_search` | ✅ History | ✅ Plans | ✅ Golden | — | — | — | ✅ Docs |
| `ask_user_input` | ✅ Scope | ✅ Priority | — | — | — | ✅ Clarify | — |
| `message_compose` | — | — | — | — | — | — | ✅ Reports |

### 10.3 Протокол использования MCP

**При запуске субагента оператор:**

1. Определяет, нужны ли MCP-вызовы для текущей задачи (по таблице §10.1)
2. Если да — использует соответствующий MCP tool напрямую в контексте Claude.ai
3. Результат MCP → input для субагента (findings, reference data, test data)

**Правила:**

- MCP-вызовы **опциональны** — субагент работает и без них
- MCP используется для **верификации** (schema drift, contract testing), **не для production data flow**
- Результаты MCP **не кэшируются между сессиями** — каждый вызов fresh
- При ошибке MCP → субагент продолжает работу без MCP data, помечает `[...] MCP недоступен`

### 10.4 Типовые MCP workflows

| Workflow | Агент | Trigger | MCP Tools | Output |
|----------|-------|---------|-----------|--------|
| Schema Drift Detection | pyAuditBot | audit ChEMBL pipeline | ChEMBL:compound_search → compare with entity | AUD-SCHEMA-* |
| Golden Dataset Generation | pyTestBot | new_tests for ChEMBL | ChEMBL:compound_search/get_bioactivity → save | tests/golden/*.json |
| Contract Testing | pyTestBot | final (ChEMBL scope) | ChEMBL MCP → compare with contract | FAIL-CONTRACT-* |
| Research Context | pyPlanBot | new entity planning | bioRxiv:search_preprints → analyze | 01-plan §Research Context |
| Documentation Diagrams | pyDocBot | DOC-* for architecture | Mermaid:validate_and_render → save | docs/diagrams/*.svg |
| API Reference | pyCodeBot | new adapter implementation | ChEMBL/OT/PubMed → study response | Field mapping in code |
| Config Fields Validation | pyConfigBot | new pipeline config | ChEMBL MCP → compare fields | CFG-DRIFT-* |
| Error Reproduction | pyDebugBot | DBG-* for API failure | ChEMBL MCP → reproduce request | DBG-* root cause |

---

## 11. Changelog (ORCHESTRATION.md)

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

- **NEW**: `pyCodeBot` — написание production-кода (`src/bioetl/`), файловая зона `src/`
- **NEW**: `pyConfigBot` — управление конфигурациями (`configs/`), файловая зона `configs/`
- **NEW**: ID-prefix `CFG-` для config changes
- **NEW**: Артефакт `04a-config-log.md`
- **NEW**: Упрощённые режимы: `new-entity` (§8.4), `composite-pipeline` (§8.5)
- **NEW**: §5.2 — маршрутизация RF-* по типу изменения
- **NEW**: §7.6 — config compliance gate
- **NEW**: §7.7 — zone isolation
- **CHANGED**: Шаг ⑤ (ранее «рефакторинг») → шаг ④ «реализация» с параллельным pyCodeBot + pyConfigBot
- **CHANGED**: Матрица взаимодействий расширена до 7×7
- **CHANGED**: Счёт subagent-ов: 5 → 7

### v1.0 (2026-02-07)

- Initial release: pyAuditBot, pyPlanBot, pyTestBot, pyDebugBot, pyDocBot
