*Статус: internal-only (historical prompt)*

# Documentation & Diagrams Audit — Промт для аудита и обновления документации

*Версия: 1.0.0 | Дата: 2026-03-08*

## Назначение

Промт для комплексного аудита и обновления проектной документации и диаграмм BioETL.
Scope: `docs/` **без** `docs/00-project/ai/` (AI-конфигурация аудитируется отдельно через `ai_workspace_setup.md`).

---

## Набор агентов

### Рекомендуемый состав

| # | Агент | Surface | Model | Зона ответственности |
|---|-------|---------|-------|---------------------|
| A1 | Cross-Reference Auditor | `documentation-audit` | skill | Битые ссылки, навигация mkdocs.yml, dead links |
| A2 | Code-Docs Sync Checker | `py-doc-bot` | sonnet | Соответствие docs ↔ код (API ref, layer docs, configs) |
| A3 | ADR Auditor | `py-audit-bot` | opus | Полнота ADR, статусы, отсутствующие решения |
| A4 | Diagram Validator | `py-doc-bot` | sonnet | Mermaid синтаксис, ADR-040, соответствие коду |
| A5 | Content Freshness Analyzer | `documentation-cascade-audit` | skill | Устаревший контент, drift detection, архив-кандидаты |

### Когда какой агент

| Сценарий | Агенты | Параллельность |
|----------|--------|---------------|
| Быстрый pre-PR аудит | A2 + A4 | Параллельно |
| Полный аудит | A1 → (A2 ∥ A3 ∥ A4) → A5 | A1 первый, затем параллельно, A5 последний |
| Только диаграммы | A4 | Один |
| Только ADR | A3 | Один |
| Post-refactoring sync | A2 + A4 + A5 | Параллельно |

---

## Промт

> Скопируй текст ниже (от `---BEGIN---` до `---END---`) и передай AI-агенту.

---BEGIN---

Проведи аудит документации и диаграмм проекта BioETL.

### Scope

    docs/                              ← Весь каталог
    ├── 00-project/                    ← Правила, governance, glossary (БЕЗ 00-project/ai/)
    ├── 01-requirements/               ← Требования (REQUIREMENTS.md)
    ├── 02-architecture/               ← Архитектура, ADR, диаграммы
    │   ├── decisions/                 ← 45 ADR (ADR-001..ADR-045)
    │   ├── diagrams/              ← 126 .mmd + ~170 .mermaid views
    │   │   ├── architecture/          ← Архитектурные диаграммы (01-18)
    │   │   ├── class-diagrams/        ← Class-диаграммы (01-16)
    │   │   ├── foundation/            ← Foundation-диаграммы (01-50)
    │   │   └── views/                 ← Decomposed views (.mermaid)
    │   └── policies/                  ← Архитектурные политики
    ├── 03-guides/                     ← Руководства разработчика
    ├── 04-reference/                  ← API ref, contracts, pipelines, schemas
    ├── 05-operations/                 ← Runbooks, deployment, monitoring
    ├── 99-archive/                    ← Архив (read-only, не аудитировать содержимое)
    ├── plans/                         ← Планы (проверить актуальность)
    └── mkdocs.yml                     ← Навигация MkDocs (корень проекта)

**Исключения:** `docs/00-project/ai/`, `docs/exports/`, `docs/reports/`, `docs/site/`

### Задачи аудита

#### Фаза 1: Cross-Reference Audit (A1)

##### 1.1. Битые ссылки

    # Найти все markdown-ссылки и проверить targets
    python scripts/docs/check_doc_links.py --links

    # Проверить что все файлы из mkdocs.yml nav существуют
    grep "\.md" mkdocs.yml | sed 's/.*: //' | while read f; do
      [ -f "docs/$f" ] || echo "MISSING in mkdocs nav: docs/$f"
    done

##### 1.2. Навигация mkdocs.yml

Проверь:
- Все .md файлы из docs/ (кроме исключений) включены в nav
- Нет дублей в nav
- Порядок секций соответствует Johnny Decimal (00→05, 99)
- Нет ссылок на удалённые/перемещённые файлы

##### 1.3. Orphan-файлы

Найди .md файлы в docs/, которые:
- Не включены в mkdocs.yml nav
- Не ссылаются ни из одного другого .md
- Не являются README.md или index.md

#### Фаза 2: Code-Docs Sync (A2)

##### 2.1. Layer documentation

Проверь соответствие кода и описания для каждого слоя:

| Doc | Код | Проверка |
|-----|-----|----------|
| `02-architecture/01-domain-layer.md` | `src/bioetl/domain/` | Ports, entities, value objects |
| `02-architecture/02-application-layer.md` | `src/bioetl/application/` | Services, pipelines |
| `02-architecture/03-infrastructure-layer.md` | `src/bioetl/infrastructure/` | Adapters, storage |
| `02-architecture/04-interfaces-layer.md` | `src/bioetl/interfaces/` | CLI commands |
| `02-architecture/05-composition-layer.md` | `src/bioetl/composition/` | Bootstrap, factories |

Для каждого:
- Упомянутые классы/модули существуют в коде?
- Новые классы/модули в коде отражены в docs?
- Import-пути корректны?

##### 2.2. API Reference

    # Сравнить documented modules vs actual
    ls src/bioetl/domain/ports/*.py | sed 's|.*/||;s|\.py||' | sort > /tmp/actual_ports
    grep -oP '\w+_port' docs/04-reference/api/domain.md | sort -u > /tmp/documented_ports
    diff /tmp/actual_ports /tmp/documented_ports

##### 2.3. Pipeline docs

Для каждого pipeline в `docs/04-reference/pipelines/`:
- Config path (`configs/entities/`) существует?
- Описанные entity types совпадают с реальными?
- Transformer class существует?

##### 2.4. Contracts

Проверить `docs/04-reference/contracts/gold-schemas.md`:
- Документированные поля совпадают с `src/bioetl/domain/schemas/gold/`?
- Версии контрактов актуальны?

#### Фаза 3: ADR Audit (A3)

##### 3.1. Полнота ADR

    # Список всех ADR
    ls docs/02-architecture/decisions/ADR-*.md | sort

Для каждого ADR проверь:
- Заголовок и структура (Title, Status, Context, Decision, Consequences)
- Status актуален (Accepted / Superseded / Deprecated)
- Ссылки на код/конфиги валидны
- Нет дублирующих/конфликтующих ADR

##### 3.2. Отсутствующие ADR

Проверь, есть ли архитектурные решения в коде без ADR:
- Новые паттерны без документации
- Значимые `# ADR:` комментарии в коде без соответствующего ADR файла

##### 3.3. Superseded ADR в 99-archive

Проверь что superseded ADR из `docs/02-architecture/decisions/` перемещены в `docs/99-archive/decisions/`.

#### Фаза 4: Diagram Validation (A4)

##### 4.1. Синтаксис Mermaid

    # Валидация синтаксиса всех .mmd файлов
    make validate-diagrams-syntax
    # или
    bash scripts/diagrams/validate_mermaid_syntax.sh

##### 4.2. ADR-040 Compliance

Для каждой .mmd диаграммы проверь (см. `docs/02-architecture/diagrams/governance/policy.md`):
- Метаданные: `@version`, `@date`, `@type`, `@level`, `@nodes`
- Density: ≤15 ideal, 16-20 soft limit, >20 нужен ELK renderer
- Палитра: только канонические цвета ADR-040 (без ad-hoc hex)
- Нет emoji в subgraph labels

##### 4.3. Code-Diagram Sync

Для ключевых диаграмм (architecture/01-18):
- Классы и модули на диаграмме существуют в коде?
- Связи (imports, зависимости) корректны?
- Новые компоненты в коде отражены на диаграммах?

##### 4.4. Orphan-диаграммы

Найди .mmd/.mermaid файлы, на которые не ссылается ни один .md документ.

#### Фаза 5: Content Freshness (A5)

##### 5.1. Drift Detection

Для каждого docs-файла оцени:
- Дата последнего обновления (git log)
- Расхождение с текущим кодом (drift score: LOW/MEDIUM/HIGH)

##### 5.2. Архив-кандидаты

Файлы для перемещения в `docs/99-archive/`:
- Документы о завершённых миграциях
- Устаревшие планы из `docs/plans/`
- Verification reports старше 3 месяцев из `docs/05-operations/verification/`

##### 5.3. Glossary Sync

Проверь `docs/00-project/glossary.md`:
- Все ключевые термины из RULES.md есть в glossary?
- Нет устаревших терминов?

### Формат отчёта

Отчёт сохранять в `reports/docs-audit/`:

    reports/docs-audit/
    ├── {date}-summary.md              ← Сводный отчёт
    ├── {date}-crossref.md             ← Фаза 1: битые ссылки, orphans
    ├── {date}-code-sync.md            ← Фаза 2: drift код ↔ docs
    ├── {date}-adr-audit.md            ← Фаза 3: ADR
    ├── {date}-diagrams.md             ← Фаза 4: диаграммы
    └── {date}-freshness.md            ← Фаза 5: устаревший контент

Сводный отчёт:

    ## Documentation & Diagrams Audit Report

    **Дата**: YYYY-MM-DD
    **Scope**: docs/ (без docs/00-project/ai/)

    ### Summary

    | Фаза | Статус | Issues | Critical | Рекомендации |
    |------|:------:|:------:|:--------:|-------------|
    | 1. Cross-References | ✅/⚠️/❌ | N | N | ... |
    | 2. Code-Docs Sync | ✅/⚠️/❌ | N | N | ... |
    | 3. ADR Audit | ✅/⚠️/❌ | N | N | ... |
    | 4. Diagrams | ✅/⚠️/❌ | N | N | ... |
    | 5. Freshness | ✅/⚠️/❌ | N | N | ... |

    **Total**: N issues (N critical, N high, N medium, N low)

    ### Critical Issues (Must Fix)

    1. **[PHASE-ID]** {описание} — `{file:line}` → {рекомендация}

    ### Archive Candidates

    | Файл | Причина | Действие |
    |------|---------|----------|
    | ... | ... | Move to 99-archive/ |

    ### Actions

    - [ ] Fix N broken links
    - [ ] Update N stale docs
    - [ ] Archive N outdated files
    - [ ] Re-render N diagrams
    - [ ] Add N missing ADRs

### Ограничения

- **НЕ** редактировать `docs/00-project/ai/` (отдельный scope)
- **НЕ** редактировать `docs/exports/`, `docs/reports/`, `docs/site/` (генерируемые)
- **НЕ** редактировать `docs/99-archive/` (read-only)
- **НЕ** создавать файлы в корне проекта
- Отчёты → `reports/docs-audit/`
- При обновлении docs/mkdocs.yml — проверить `mkdocs build --strict`

---END---

---

## Вариации использования

### Быстрый pre-PR аудит (фазы 2+4)

> Проведи быстрый аудит документации по фазам 2 (Code-Docs Sync) и 4 (Diagrams)
> из промта Documentation & Diagrams Audit. Только проверка, без изменений.

### Полный аудит + исправление

> Проведи полный аудит по промту Documentation & Diagrams Audit (фазы 1-5).
> Исправь найденные проблемы. Покажи отчёт.

### Только ADR

> Проведи аудит ADR по фазе 3 из промта Documentation & Diagrams Audit.
> Проверь полноту, статусы, отсутствующие решения.

### Только диаграммы

> Проведи аудит диаграмм по фазе 4 из промта Documentation & Diagrams Audit.
> Проверь синтаксис, ADR-040 compliance, соответствие коду.

### Post-refactoring sync

> После рефакторинга `src/bioetl/{layer}/` обнови документацию:
>
> 1. Фаза 2: Code-Docs Sync — обнови layer docs и API ref
> 2. Фаза 4: Diagram Validation — обнови затронутые диаграммы
> 3. Фаза 5: Content Freshness — отметь обновлённые docs

### Обновление mkdocs.yml

> Синхронизируй mkdocs.yml nav с фактическим содержимым docs/:
>
> 1. Найди orphan-файлы (не в nav)
> 2. Найди dead entries (в nav, но файл не существует)
> 3. Предложи обновлённую секцию nav
> 4. Проверь: `mkdocs build --strict`

## Оркестрация (для Claude Code)

Запуск полного аудита через актуальные skill / subagent surfaces:

    # Фаза 1: Cross-Reference (блокирующая)
    /documentation-audit task_id=DOCAUDIT-001 mode=crossref scope="docs/ excluding docs/00-project/ai/"

    # Фазы 2-4: параллельно
    Agent(subagent_type="py-doc-bot", prompt="task_id=DOCAUDIT-002, mode=code_sync, scope=docs/02-architecture/ docs/04-reference/")
    Agent(subagent_type="py-audit-bot", prompt="task_id=DOCAUDIT-003, mode=adr_audit, scope=docs/02-architecture/decisions/")
    Agent(subagent_type="py-doc-bot", prompt="task_id=DOCAUDIT-004, mode=diagram_validation, scope=docs/02-architecture/diagrams/")

    # Фаза 5: после завершения 2-4
    /documentation-cascade-audit task_id=DOCAUDIT-005 mode=freshness scope="docs/"
