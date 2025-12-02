# Project Rules Summary

Сводка обязательных правил разработки (invariants) проекта BioETL.

## 1. Детерминизм
**Правило:** Идентичные входные данные + идентичная конфигурация = **битово-идентичный** выходной файл.
- **Сортировка**: Явная сортировка строк и колонок перед записью.
- **Время**: Все timestamps только в UTC.
- **JSON**: `sort_keys=True` при сериализации.
- **Атомарность**: Использование `write-temp-and-rename`.

## 2. Validate-before-write
**Правило:** Никакие данные не попадают в `output/` без прохождения Pandera-валидации.
- Схемы описываются в `src/bioetl/schemas/`.
- Валидация обязательна на стадии `validate`.

## 3. Логирование
**Правило:** Использование только `UnifiedLogger`.
- ❌ `print("Starting...")`
- ✅ `logger.info("Starting...", run_id=run_id)`
- Логи должны быть структурированными (Key-Value).

## 4. API Clients
**Правило:** Все внешние вызовы через `UnifiedAPIClient`.
- Обязательны: Retry (backoff), Rate Limit, Circuit Breaker.
- Запрещены "сырые" вызовы `requests.get()` в бизнес-логике.

## 5. Именование (Naming Conventions)
**Правило:** Строгое следование конвенциям.
- Модули: `snake_case` (`pipeline_base.py`)
- Классы: `PascalCase` (`ActivityPipeline`)
- Интерфейсы (ABC): Суффикс `ABC` (`StageABC`)
- Реализации: Суффикс `Impl` (опционально, если есть `Default`)
- Функции: `snake_case` (`get_data`)
- Константы: `UPPER_SNAKE_CASE` (`DEFAULT_TIMEOUT`)
- Документация: `kebab-case` с префиксом (`01-overview.md`)

## 6. Тестирование
**Правило:** Надежность превыше всего.
- Unit-тесты без сетевых вызовов.
- Golden-тесты для критических трансформаций.
- Покрытие кода ≥ 85%.

