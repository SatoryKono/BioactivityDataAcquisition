*Статус: internal-working prompt*

# Documentation & Diagrams Audit

*Версия: 2.0.0 | Дата: 2026-04-04*

## Назначение

Рабочий промт для комплексного аудита и обновления документации и диаграмм
BioETL. Промт выровнен с текущей структурой репозитория и подходит для Codex,
Claude Code и других агентных сред.

Основной scope: `docs/` без `docs/00-project/ai/`.
AI-конфигурация и runtime-поведение аудитируются отдельно через
`docs/00-project/ai/prompts/ai_workspace_setup.md`.

## Рекомендуемый состав агентов

| #   | Агент                      | Surface                                     | Роль                                 |
| --- | -------------------------- | ------------------------------------------- | ------------------------------------ |
| A1  | Cross-Reference Auditor    | `documentation-audit`                       | Битые ссылки, nav, orphan docs       |
| A2  | Code-Docs Sync Checker     | `py-doc-bot`                                | Соответствие docs ↔ code/configs     |
| A3  | ADR Auditor                | `py-audit-bot`                              | ADR completeness, status, conflicts  |
| A4  | Diagram Validator          | `py-doc-bot` + `technical-designer-mermaid` | Mermaid syntax, ADR-040, code sync   |
| A5  | Content Freshness Analyzer | `documentation-cascade-audit`               | Freshness, drift, archive candidates |

## Рекомендуемые режимы

| Сценарий              | Агенты                   | Порядок                           |
| --------------------- | ------------------------ | --------------------------------- |
| Быстрый pre-PR аудит  | A2 + A4                  | Параллельно                       |
| Полный аудит          | A1 -> (A2, A3, A4) -> A5 | A1 блокирующий, затем параллельно |
| Только диаграммы      | A4                       | Один агент                        |
| Только ADR            | A3                       | Один агент                        |
| Post-refactoring sync | A2 + A4 + A5             | Параллельно                       |

______________________________________________________________________

## Готовый промт

Скопируй текст ниже от `---BEGIN---` до `---END---` и передай AI-агенту.

---BEGIN---

Проведи аудит документации и диаграмм проекта BioETL.

### Scope

Аудитировать:

```text
docs/
├── 00-project/                    # правила, glossary, governance
├── 01-requirements/
├── 02-architecture/
│   ├── decisions/
│   ├── diagrams/
│   │   ├── architecture/
│   │   ├── class-diagrams/
│   │   ├── foundation/
│   │   └── views/
│   └── policies/
├── 03-guides/
├── 04-reference/
├── 05-operations/
├── 99-archive/                    # read-only, содержимое не менять
└── plans/

mkdocs.yml                         # root-level artifact, проверять отдельно
README.md                          # root-level doc entrypoint
```

Исключения:

- `docs/00-project/ai/`
- `docs/exports/`
- `docs/reports/`
- `docs/site/`

### Общие правила

- Документируй реальное текущее состояние репозитория, а не желаемое.
- Не редактируй production code, если задача только про аудит docs.
- Не редактируй содержимое `docs/99-archive/`.
- Если предлагается архивирование, только пометь кандидатов и обоснуй.
- Все high/critical findings должны иметь evidence: `file`, `line`, `command`.
- При утверждениях о структуре репозитория сначала проверь live tree, не делай
  предположений по старым counts или naming snapshots.

## Фаза 1: Cross-Reference Audit

### 1.1. Битые ссылки

Выполни:

```bash
uv run python -m scripts.docs check-links --links --specs --configs
```

Дополнительно проверь, что все Markdown targets из `mkdocs.yml` существуют.
Учитывай, что `mkdocs.yml` находится в корне репозитория, а не внутри `docs/`.

### 1.2. Навигация MkDocs

Проверь:

- все publishable `.md` файлы из scope включены в `mkdocs.yml` nav либо
  осознанно исключены;
- нет dead entries в nav;
- нет дублей nav-entries;
- порядок разделов соответствует текущей информационной архитектуре
  (`00-project` -> `05-operations` -> `99-archive`);
- нет ссылок на удалённые или перемещённые файлы.

### 1.3. Orphan docs

Найди `.md` файлы в scope, которые:

- не включены в `mkdocs.yml`;
- не referenced из других `.md`;
- не являются `README.md`, `INDEX.md`, `index.md`;
- не относятся к repo-only internal surfaces, исключённым из публикации.

## Фаза 2: Code-Docs Sync

### 2.1. Layer documentation

Проверь соответствие между layer docs и кодом:

| Doc                                               | Code                         |
| ------------------------------------------------- | ---------------------------- |
| `docs/02-architecture/01-domain-layer.md`         | `src/bioetl/domain/`         |
| `docs/02-architecture/02-application-layer.md`    | `src/bioetl/application/`    |
| `docs/02-architecture/03-infrastructure-layer.md` | `src/bioetl/infrastructure/` |
| `docs/02-architecture/04-interfaces-layer.md`     | `src/bioetl/interfaces/`     |
| `docs/02-architecture/05-composition-layer.md`    | `src/bioetl/composition/`    |

Для каждого файла проверь:

- упомянутые классы и модули существуют;
- новые значимые модули отражены в docs;
- import paths и package names корректны;
- описания не противоречат текущим архитектурным ограничениям.

### 2.2. API Reference

Сравни фактический API surface с reference docs.

Особое внимание:

- `docs/04-reference/api/domain/ports.md`
- `docs/04-reference/api/domain/*.md`
- `docs/04-reference/api/application/*.md`
- `docs/04-reference/api/infrastructure/*.md`
- `docs/04-reference/api/composition/*.md`

Не предполагай, что вся domain API reference живёт только в
`docs/04-reference/api/domain.md`; используй подфайлы как primary surface.

Для портов сравни с:

- `src/bioetl/domain/ports/**/*.py`

### 2.3. Pipeline docs

Аудируй обе формы layout:

- `docs/04-reference/pipelines/*.md`
- `docs/04-reference/pipelines/*/*.md`

Для каждого pipeline/doc entry проверь:

- связанный config path существует (`configs/entities/`, `configs/composites/`,
  либо provider-specific config where applicable);
- entity/pipeline naming совпадает с текущим кодом и config topology;
- если упомянут transformer/service/class, он существует;
- xwalk/spec docs не противоречат реальным pipeline inputs/outputs.

### 2.4. Contracts

Проверь `docs/04-reference/contracts/gold-schemas.md`.

Source of truth:

- `src/bioetl/domain/contracts/gold/`

Дополнительно проверь:

- `docs/04-reference/contracts/gold/*.json`

Нужно проверить:

- актуальность contract inventory;
- версии, `Last verified`, linked ADRs;
- согласованность полей и contract grouping с кодом.

Не использовать `src/bioetl/domain/schemas/gold/` как source of truth, если
репозиторий фактически хранит Gold contracts в `domain/contracts/gold/`.

## Фаза 3: ADR Audit

### 3.1. Полнота ADR

Для live ADR set в `docs/02-architecture/decisions/ADR-*.md` проверь:

- наличие базовой структуры: Title, Status, Context, Decision, Consequences;
- валидность ссылок на code/config/docs;
- отсутствие конфликтующих решений;
- соответствие status реальному состоянию репозитория.

### 3.2. Missing ADRs

Проверь, есть ли архитектурно значимые решения в коде/документации без ADR:

- новые стабильные patterns;
- явные `ADR` references в комментариях/текстах без соответствующего ADR;
- крупные governance decisions, описанные только в code/docs.

### 3.3. Superseded ADR handling

Если существует `docs/99-archive/decisions/`, проверь корректность переноса
superseded ADR туда.

Если такого каталога нет:

- не считать это ошибкой само по себе;
- проверить, как помечены superseded ADR в live tree;
- перечислить archive candidates и inconsistencies в status/links.

## Фаза 4: Diagram Validation

### 4.1. Mermaid syntax

Выполни:

```bash
make validate-diagrams-syntax
```

или:

```bash
bash scripts/diagrams/validate_mermaid_syntax.sh
```

### 4.2. ADR-040 compliance

Проверяй относительно:

- `docs/02-architecture/decisions/ADR-040-diagram-governance.md`
- связанных policy/guidance файлов в `docs/02-architecture/diagrams/`
- текущих diagram tooling rules в `scripts/diagrams/`

Для диаграмм проверь:

- обязательные metadata markers;
- naming и file placement;
- palette/style consistency;
- отсутствие ad-hoc цветов и emoji в labels там, где это запрещено;
- соответствие quality budget и density rules актуальному governance.

### 4.3. Code-Diagram Sync

Для ключевых diagram families проверь:

- referenced modules/classes существуют;
- relationships не противоречат реальным imports/dependencies;
- новые значимые компоненты отражены там, где диаграмма должна быть canonical.

Не ограничивайся только `architecture/01-18`, если canonical diagrams
фактически распределены по нескольким subtrees.

### 4.4. Orphan diagrams

Найди `.mmd` / `.mermaid` файлы, на которые не ссылается ни один publishable
`.md`, и раздели их на:

- canonical but indirectly consumed;
- generated/support artifacts;
- true orphan candidates.

## Фаза 5: Content Freshness

### 5.1. Drift detection

Для каждого docs-файла в scope оцени:

- last meaningful update via git history;
- drift score (`LOW`, `MEDIUM`, `HIGH`);
- factual drift vs editorial/style debt.

### 5.2. Archive candidates

Отдельно выдели кандидатов на перенос в `docs/99-archive/`:

- завершённые migration docs;
- устаревшие планы из `docs/plans/`;
- stale verification/runbook support docs, если они больше не operationally
  relevant.

Не перемещай автоматически, только предложи.

### 5.3. Glossary sync

Проверь `docs/00-project/glossary.md`:

- ключевые термины из active docs и rules присутствуют;
- определения не устарели;
- нет лишних deprecated terms without note.

## Формат отчёта

Сохраняй артефакты в:

```text
reports/docs-audit/
├── {date}-summary.md
├── {date}-crossref.md
├── {date}-code-sync.md
├── {date}-adr-audit.md
├── {date}-diagrams.md
└── {date}-freshness.md
```

### Сводный отчёт

```md
## Documentation & Diagrams Audit Report

**Дата**: YYYY-MM-DD
**Scope**: docs/ (excluding docs/00-project/ai/) + root mkdocs.yml + README.md

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
- [ ] Reconcile N code-doc drifts
- [ ] Re-render N diagrams
- [ ] Add or update N ADRs
```

## Ограничения

- Не редактировать `docs/00-project/ai/`.
- Не редактировать `docs/exports/`, `docs/reports/`, `docs/site/`.
- Не редактировать `docs/99-archive/`.
- Не создавать файлы в корне проекта.
- Если обновляется `mkdocs.yml` или publishable docs, после изменений проверить:

```bash
python -m scripts.docs build-site --strict
```

или project-preferred equivalent через текущий env wrapper.

## Режимы использования

### Быстрый pre-PR аудит

Проведи только:

- Фаза 2: Code-Docs Sync
- Фаза 4: Diagram Validation

Только проверка, без изменений.

### Полный аудит + исправление

Проведи полный аудит по фазам 1-5.
Исправь найденные проблемы в разрешённом scope.
Покажи итоговый отчёт и список изменений.

### Только ADR

Проведи только фазу 3: ADR Audit.

### Только диаграммы

Проведи только фазу 4: Diagram Validation.

### Post-refactoring sync

После рефакторинга слоя `src/bioetl/{layer}/`:

1. Обнови layer docs и API reference.
1. Обнови затронутые диаграммы.
1. Отметь обновлённые docs как re-verified.

## Оркестрация

Если агентная среда поддерживает subagents:

- сначала выполни A1;
- затем параллельно A2, A3, A4;
- после этого выполни A5;
- затем нормализуй findings в один consolidated summary.

Если subagents недоступны:

- выполни те же фазы последовательно в том же порядке.

---END---

## Примечания по актуальности

- Этот промт исключает `docs/00-project/ai/` из audit scope, но сам хранится в
  AI prompt surface как repo-only working artifact.
- При конфликте между этим промтом и текущими runtime/skill instructions
  приоритет у актуальных skill docs, agent guides и active project docs.
