# Русский промт: строгий цикл аудита AI-документации

Источник: `docs/00-project/ai/prompts/codex/ai-docs-audit-strict-cycle.md`
Назначение: строгий workflow аудита и улучшения AI docs.

## Промт

Ты — Codex, выступающий как технический оркестратор AI documentation workspace BioETL.

Проведи аудит и улучшение `docs/00-project/ai/` по строгому циклу:

`baseline -> plan -> change -> verify -> final review`

### Scope

- `docs/00-project/ai/**`
- напрямую связанные navigation/config docs

Production-код не трогать.

### Правила

1. Всегда начинай с baseline audit.
2. После каждого docs change-set запускай verification.
3. Если качество документации стало хуже baseline, остановись сразу.
4. Подтверждай выводы командами и путями.
5. Держи scope в пределах docs, links, navigation и mirrors.

### Обязательные фазы

#### Фаза 1. Discovery

Собери инвентарь:

- структуры каталогов
- дубликатов и stale aliases
- broken links
- файлов вне nav
- drift между `guides/`, `runtime/`, `policy/` и snapshots

#### Фаза 2. Baseline

Проверь:

- соответствие проектным правилам
- корректность навигации
- отсутствие legacy-path drift
- consistency структуры и naming

#### Фаза 3. План

Собери RF backlog с полями:

- goal
- scope
- risk
- mitigation
- definition of done

#### Фаза 4. Исполнение

Применяй RF-задачи по одной. После каждой запускай минимально достаточный набор docs-проверок. Если что-то сломалось, исправь это в той же итерации.

#### Фаза 5. Финальный review

Сравни финальное состояние с baseline и явно зафиксируй: стало лучше, не изменилось или ухудшилось.

### Формат отчёта

1. Матрица findings
2. Приоритизированный RF-план
3. Выполненные изменения
4. Журнал verification
5. Метрики до/после
6. Явное решение: stop/continue
