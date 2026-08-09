# Documentation & Diagrams Audit

## Evaluation Metadata
- **Category:** Architecture Prompts
- **Weighted Score:** 6.77 / 10
- **Overall Rating:** Medium
- **Path:** docs/00-project/ai/prompts/documentation_diagrams_audit.md

## Evaluation Breakdown
- Clarity: 7/10 (weight: 0.15)
- Completeness: 7/10 (weight: 0.15)
- Specificity: 7/10 (weight: 0.12)
- Context: 7/10 (weight: 0.10)
- Guardrails: 7/10 (weight: 0.10)
- Maintainability: 7/10 (weight: 0.08)
- Reusability: 6/10 (weight: 0.08)
- Error Handling: 6/10 (weight: 0.08)
- Validation: 6/10 (weight: 0.07)
- Documentation: 7/10 (weight: 0.07)

## Original Content (Summary)

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
| A1  | Cross-Reference Auditor    | `py-doc-bot`                       | Битые ссылки, nav, orphan docs       |
| A2  | Code-Docs Sync Checker     | `py-doc-bot`                                | Соответствие docs ↔ code/configs     |
| A3  | ADR Auditor                | `py-audit-bot`                              | ADR completeness, status, conflicts  |
| A4  | Diagram Validator          | `py-doc-bot` + `technical-designer-mermaid` | Mermaid syntax, ADR-040, code sync   |
| A5  | Content Freshness Analyzer | `py-doc-bot`               | Freshness, drift, archive candidates |

## Рекомендуемые режимы

| Сценарий              | Агенты                   | Порядок                           |
| --------------------- | ------------------------ | --------------------------------- |
| Быстрый pre-PR аудит  | A2 + A4                  | Параллельно                       |
| Полный аудит          | A1 -> (A2, A3, A4) -> A5 | A1 блокирующий, затем параллельно |
| Только диаграммы      | A4                       | Один агент                        |
| Только ADR            | A3                       | Один агент                        |
| Post-refactoring sync | A2 + A4 + A5             | Параллельно                       |

## Готовый промт

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
