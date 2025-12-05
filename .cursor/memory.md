# Проект BioETL

- **Ответы**: на русском, кратко.
- **Детерминизм**: обязателен (стабильный порядок колонок/строк, UTC, атомарная запись через temp→os.replace).
- **Валидация**: Pandera-схемы для всех таблиц перед записью.
- **Архитектура**:
  - Логирование: `UnifiedLogger`.
  - API: `UnifiedAPIClient` (retry/backoff/rate limit).
  - Трёхслойный паттерн: ABC (infrastructure/clients/base/contracts) → Default factory → Impl.
- **Именование**:
  - Модули: snake_case.
  - Классы: PascalCase (Factory, Client, Impl, Config).
  - Функции: snake_case (get_, fetch_, iter_, create_).
- **Docs**: kebab-case с `NN-` префиксом в `docs/application/pipelines/`.
- **Тесты**: coverage ≥85%, golden-тесты, без сети в unit-тестах.
- **Секреты**: env/secret manager.
- **Пути**:
  - Pipelines: `src/bioetl/application/pipelines/<provider>/<entity>/<stage>.py`.
  - Clients: `src/bioetl/infrastructure/clients/`.

