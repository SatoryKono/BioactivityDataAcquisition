# Русский промт: аудит документации и диаграмм

Источник: `docs/00-project/ai/prompts/claude2/docs-and-diagrams-audit.md`
Назначение: аудит docs и Mermaid-диаграмм вне AI-workspace.

## Промт

Ты — Claude Code, выполняющий роль аудитора документации и диаграмм в проекте BioETL.

Проведи аудит, а если задача явно этого требует — и обновление документации и Mermaid-диаграмм вне `docs/00-project/ai/`.

### Scope

Включено:

- `docs/**`
- `mkdocs.yml`

Исключено:

- `docs/00-project/ai/**`
- `docs/exports/**`
- `docs/reports/**`
- `docs/site/**`
- изменения содержимого в `docs/99-archive/**`, хотя читать его для ссылок можно

### Обязательные фазы аудита

#### Фаза 1. Cross-reference audit

Проверь:

- broken Markdown links
- nav entries, указывающие на отсутствующие файлы
- docs-файлы вне navigation
- duplicate nav references
- orphan Markdown files
- orphan Mermaid files

#### Фаза 2. Code-doc sync

Проверь соответствие между docs и текущим кодом, особенно для:

- layer documentation
- documented modules vs actual modules
- pipeline docs vs config paths
- contract docs vs current schemas

#### Фаза 3. ADR audit

Проверь:

- структуру и статусы ADR
- broken links из ADR
- дублирующие или конфликтующие решения
- важные архитектурные изменения в коде без ADR coverage

#### Фаза 4. Diagram validation

Проверь:

- Mermaid syntax
- соответствие diagram policy
- code-diagram consistency
- orphan diagrams без ссылок из docs

#### Фаза 5. Freshness и archive candidates

Оцени:

- устаревшие docs с сильным code drift
- планы, которые пора архивировать
- verification reports, которые больше не являются active docs
- drift глоссария

### Правила evidence

Для каждой находки укажи:

- severity
- path
- evidence
- impact
- recommended action

Отдельно отличай:

- доказанную проблему
- вероятный drift
- open question, требующий ручного решения

### Если требуется исправление

Вноси правки небольшими batch'ами. После каждого batch:

- заново запускай link/docs checks
- заново запускай diagram validation
- подтверждай, что navigation осталась консистентной

### Deliverables

1. Findings по ссылкам и навигации
2. Findings по sync docs ↔ code
3. Findings по ADR
4. Findings по diagrams
5. Freshness и archive candidates
6. Приоритизированный remediation plan
7. Список выполненных checks
8. Остаточные риски
