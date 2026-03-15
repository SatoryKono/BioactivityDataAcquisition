# Русский промт: аудит и улучшение `docs/00-project/ai`

Источник: `docs/00-project/ai/prompts/claude2/ai-docs-audit-and-improve.md`
Назначение: orchestration prompt для улучшения AI-документации.

## Промт

Ты — Claude Code, работающий как documentation orchestrator для BioETL.

Проведи аудит `docs/00-project/ai/`, собери план и внеси безопасные улучшения по контролируемому циклу.

### Scope

- `docs/00-project/ai/**`
- напрямую связанные docs nav/config файлы, если это требуется той же правкой

`src/bioetl/**` не менять.

### Операционная модель

Работай в таком порядке:

1. discovery
2. baseline audit
3. приоритизированный план
4. по одному change-set
5. verification после каждого change-set
6. final audit
7. independent double-check

### Discovery

Собери evidence-backed инвентарь для:

- структуры каталогов
- deprecated aliases и stale duplicates
- broken links
- nav drift
- файлов вне ожидаемой навигации
- расхождений между `guides/`, `runtime/`, `policy/` и snapshots

### Baseline audit

Оцени:

- соответствие проектным правилам
- согласованность с MkDocs nav
- legacy-path drift
- consistency именования и структуры

Раздели проблемы baseline на `must` и `should`.

### Планирование

Сформируй RF-style задачи с полями:

- objective
- file scope
- risk
- mitigation
- definition of done

### Правила исполнения

- Применяй по одной RF-задаче за раз.
- После каждого docs change-set запускай релевантную проверку.
- Если проверка упала, исправь текущий change-set до перехода дальше.
- Если качество стало хуже baseline, остановись и объясни почему.

### Итоговый вывод

1. Таблица findings: `Problem | Severity | File | Status | Evidence`
2. RF-план с приоритетами
3. Выполненные изменения
4. Проверки и результаты
5. Метрики до/после
6. Явный вердикт:
   - `continue`
   - или `stop: <reason>`
