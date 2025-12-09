## Цели
- Добавить конфигурируемый fallback при 5xx/timeout для эндпоинтов ChEMBL.
- Логировать переключения, фиксировать фактический endpoint в метаданных.
- Сохранить совместимость интерфейсов и детерминизм.

## Изменения в конфиге
- Расширить `ChemblSourceConfig` полем `fallbacks: dict[str, list[str]]` (e.g. `assay: ["assays", "assays_archive"]`).
- Валидация: ключи — известные сущности; значения — непустые строки, без слэшей.

## Request Builder
- `ChemblRequestBuilderImpl` оставить без ломки: эндпоинт выбирается через `build_for_endpoint/for_endpoint`.
- При использовании fallback — просто переустанавливать endpoint и перестраивать URL.

## Клиент ChEMBL (DataClient)
- В `ChemblHttpClientImpl.fetch()`:
  - Определить первичный endpoint через `_resolve_endpoint(entity)`.
  - Получить список `fallbacks[entity]` (включая первичный как 1-й).
  - Итеративно: для каждого endpoint → `builder` → URL → `_execute_request(url)`.
  - На `ApiUnexpectedStatusError (>=500)`/`requests.Timeout` перейти к следующему.
  - Логировать: `http_fallback_attempt`, поля: `entity`, `from`, `to`, `attempt`, `reason`.
  - Установить `self._last_endpoint_used` при успехе.

## Логирование
- Только `UnifiedLogger`, без `print()`; поля: `provider`, `entity`, `endpoint`, `status_code`, `reason`.

## Метаданные
- В `ChemblPipelineBase._enrich_context(context)`: дополнительно `context.metadata["endpoint_used"] = getattr(extraction_service, "get_last_endpoint_used", lambda: None)()` с безопасной проверкой.
- Если метод/атрибут отсутствует — не писать поле.

## Внедрение зависимостей
- Контейнер: передавать `fallbacks` из `ChemblSourceConfig` в конструктор `ChemblHttpClientImpl` (новый необязательный аргумент), либо встраивать в `ChemblRequestBuilderImpl`.
- Не ломать существующее создание — все новые параметры с default.

## Тесты
- Unit: заглушка `http` возвращает 500/timeout → проверка переключения на следующий endpoint, логов и `last_endpoint_used`.
- Unit: успешный первичный endpoint → отсутствие fallback.
- Integration (минимально): ID-only источник использует `request_batch` и работает при 500 на первичном.
- Golden/детерминизм: порядок строк/колонок, UTC, атомарная запись — без изменений.

## Документация
- Добавить раздел в `docs/project/00-rules-summary.md` об отказоустойчивости клиентов (fallback по конфигу).
- Чек-лист: логирование fallback, метаданные `endpoint_used`.

## Критерии готовности
- Все тесты зелёные, покрытие ≥85%.
- Fallback включается только при ошибках; без влияния на успешные запросы.
- Метаданные содержат фактический endpoint, если доступно.

Подтвердите — приступлю к реализации (конфиг → клиент → пайплайн → тесты).