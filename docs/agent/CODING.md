# Навыки Работы с Кодовой Базой BioETL

Этот документ описывает стандарты кодирования и используемые инструменты.

## 1. Стек технологий
*   **Язык:** Python 3.10+
*   **Обработка данных:** Polars, Delta Lake (`deltalake`), Pandera (валидация).
*   **Инфраструктура:** Prefect (оркестрация), Redis (блокировки), Prometheus (метрики).
*   **Сеть:** `httpx` (async), `respx` (тесты), специализированные клиенты (`pubchempy`, `chembl_webresource_client`).

## 2. Стандарты кода
*   **Типизация:** Строгая статическая типизация. Проверка через `mypy`. Используйте `typing.Protocol` для интерфейсов.
*   **Линтинг:** `ruff` для форматирования и линтинга. Конфигурация в `pyproject.toml`.
*   **Именование:**
    *   Классы: `PascalCase` (суффиксы `Impl`, `ABC`, `Factory` обязательны там, где уместно).
    *   Функции/Переменные: `snake_case`.
    *   Константы: `UPPER_CASE`.
*   **Логирование:** `structlog` вместо стандартного `logging`.
    *   Никаких `print()`.
    *   Обязательные поля: `run_id`, `pipeline`, `stage`.
*   **Конфигурация:** `pydantic-settings`. Секреты через `.env` (не коммитить!).

## 3. Асинхронность (AsyncIO)
*   Код преимущественно асинхронный.
*   **Блокирующие операции:** I/O операции, не поддерживающие async (синхронные клиенты, запись в Delta Lake, тяжелая валидация), **должны** быть вынесены в тредпул:
    ```python
    await loop.run_in_executor(None, blocking_func, *args)
    ```
*   **Event Loop:** Не создавайте новые event loops вручную внутри адаптеров. Используйте `asyncio.get_running_loop()`.

## 4. Обработка ошибок
*   Используйте типизированные исключения (`src/bioetl/domain/exceptions.py`).
*   **Строгий режим:** Переменная `BIOETL_STRICT_ERROR_HANDLING=true` вызывает raise, иначе логгирование warning.
*   **Circuit Breaker:** Реализован для внешних вызовов (5 ошибок -> Open state).
*   **Retry:** Стандарт: 3 попытки, экспоненциальный backoff (x2).

## 5. Безопасность
*   Сканирование через `bandit`.
*   PII данные: хеширование `sha256(lowercase(val) + salt)`.
*   Никаких хардкодных секретов.

## 6. Организация файлов
*   Composition Root: `src/bioetl/interfaces/bootstrap.py`.
*   Пайплайны: `src/bioetl/application/pipelines/`.
*   Адаптеры: `src/bioetl/infrastructure/adapters/`.
*   Тесты: `tests/` (зеркальная структура относительно `src/`).
