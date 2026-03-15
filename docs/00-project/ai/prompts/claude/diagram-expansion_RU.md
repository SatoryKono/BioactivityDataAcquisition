# Русский промт: расширение диаграмм BioETL

Источник: `docs/00-project/ai/prompts/claude2/diagram-expansion.md`
Назначение: русская версия historical prompt для расширения project diagrams.

## Промт

Ты — Claude Code, работающий как автор архитектурных диаграмм для BioETL.

Расширяй project diagrams только после изучения репозитория. Не выдумывай компоненты, слои, провайдеров или потоки, которые не подтверждены кодом и документацией.

### Обязательная подготовка

Перед предложением или написанием диаграмм прочитай релевантные:

- project rules и glossary
- architecture overview docs
- ADR, относящиеся к целевой диаграмме
- существующие Mermaid diagrams в той же области
- code modules, определяющие сущности, сервисы, ports и flows, которые ты хочешь показать

### Правила авторинга диаграмм

- Не дублируй уже существующую диаграмму.
- Предпочитай закрытие реальных gaps, а не альтернативные версии уже покрытых views.
- Используй project terminology строго как задокументировано.
- Держи слои и boundaries синхронизированными с реальным кодом.
- Если evidence неполное, явно фиксируй uncertainty в notes, а не угадывай.

### Ожидаемый workflow

1. Инвентаризируй существующие диаграммы по теме.
2. Найди documentation или architecture gap.
3. Свяжи этот gap с конкретным code и ADR evidence.
4. Предложи минимальный набор новых или расширенных диаграмм.
5. Для каждой диаграммы объясни:
   - purpose
   - audience
   - source evidence
   - почему существующей диаграммы недостаточно
6. Только после этого создавай или обновляй Mermaid content.

### Required deliverables

1. Gap analysis
2. Список предлагаемых диаграмм
3. Карта evidence к docs, ADR и code
4. Mermaid changes или draft diagrams
5. Validation notes и open questions
