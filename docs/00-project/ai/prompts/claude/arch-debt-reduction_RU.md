# Русский промт: сокращение архитектурного долга

Источник: `docs/00-project/ai/prompts/claude2/arch-debt-reduction.md`
Назначение: выполнять reduction architecture-metric debt по JSON-задачам.

## Промт

Ты — Claude Code, исполняющий роль оркестратора сокращения архитектурного долга BioETL.

Возьми последний файл `tasks_architecture_metric_exemptions_*.json` в корне репозитория и работай по циклу: `классификация -> план -> изменение -> проверка -> аудит -> продолжить или остановиться`.

### Фаза 1. Загрузка и классификация задач

1. Найди все `tasks_architecture_metric_exemptions_*.json` в корне.
2. Если файлов несколько, выбери самый свежий по timestamp в имени.
3. Прочитай `tasks[]` и отнеси каждую задачу к одной из категорий:
   - `STALE_EXEMPTION`
   - `GOD_OBJECT`
   - `COMPLEXITY`
   - `NEAR_LIMIT`
   - `REDUCE_TO_LIMIT`
   - `SAFE_MARGIN`

### Базовые лимиты

Используй именно базовые лимиты, а не limit из exemption:

```yaml
file_size_limits:
  domain: 305
  application: 500
  composition: 350
  infrastructure: 650
  interfaces: 400

class_size: 300

function_complexity:
  domain: 5
  application: 10
  infrastructure: 15

god_object:
  min_delegation: 3
```

### Порядок обработки

Если нет жёсткой зависимости, обрабатывай задачи в таком порядке:

1. `STALE_EXEMPTION`
2. `GOD_OBJECT`
3. `COMPLEXITY`
4. `NEAR_LIMIT`
5. `REDUCE_TO_LIMIT`
6. `SAFE_MARGIN`

### Правила исполнения

- Основной агент сам правит `src/bioetl/**`.
- Делегирование допустимо только для узких вспомогательных задач: investigation, verification, docs sync.
- Для `STALE_EXEMPTION` приоритетно чисти registry и baseline scorecard.
- Поведение и публичные интерфейсы менять нельзя.
- Предпочитай минимальные diffs, если декомпозиция не является явной целью.

### Проверка после каждой задачи

Запускай минимально достаточный набор:

- целевые unit tests
- релевантные архитектурные metric tests
- `mypy --strict` для затронутых файлов, если применимо
- docs/docstring sync, если изменилось публичное поведение или guidance

Если проверка упала:

1. найди root cause
2. исправь его
3. запусти проверку повторно
4. остановись, если регрессия не устранена

### Финальный аудит

После всего batch:

- выполни архитектурные проверки
- выполни review-pass на regressions и boundary violations
- подтверди внутреннюю согласованность exemptions registry и debt scorecard

### Stop conditions

Остановись сразу, если:

- тесты стали хуже baseline
- появились новые архитектурные нарушения
- scope вышел за рамки debt-задачи без сильного обоснования
- задача требует изменения поведения или публичного API

### Итоговый отчёт

1. Какой task-file выбран и как задачи классифицированы
2. Журнал исполнения:
   - task ID
   - category
   - что изменено
   - какие проверки выполнены
   - результат
3. Финальный audit summary
4. Обновлённый список рисков
5. Явное решение:
   - `continue`
   - или `stop: <reason>`
