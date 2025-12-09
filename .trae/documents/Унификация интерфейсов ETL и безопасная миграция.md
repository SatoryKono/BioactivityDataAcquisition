## Цели
- Сохранить текущую функциональность без breaking changes.
- Навести единообразие интерфейсов по группам (DataClient, ApiClient, RecordSource, ExtractionService, Extractor/Transformer/Validator/Loader, Output/Writer).
- Выполнить миграцию по этапам с покрытием тестами ≥85% и соблюдением детерминизма.

## Текущее состояние (проверено в коде)
- ApiClientABC: src/bioetl/domain/clients/base/contracts.py:43-61.
- UnifiedAPIClientImpl: src/bioetl/infrastructure/clients/base/impl/unified_api_client_impl.py:29-66,122-161.
- ChemblHttpClientImpl (DataClient): src/bioetl/infrastructure/clients/chembl/impl/chembl_http_client_impl.py:27-61,81-99,136-190.
- ChemblPaginatorImpl: src/bioetl/infrastructure/clients/chembl/paginator.py:9-22,40-79.
- ExtractionServiceABC: src/bioetl/domain/ports/extraction.py:15-105.
- Retry: src/bioetl/infrastructure/http/retry.py, экспортируется из src/bioetl/infrastructure/http/__init__.py.
- Протокол RecordSource уже существует (domain.record_source, используется в ExtractionServiceABC через RawRecord).
- Старые классы из `clients.base.interfaces` отсутствуют, фактических конфликтов нет.

## Изменения по группам
- DataClient/APIClient:
  - Оставить разделение: DataClientABC (семантические запросы по сущности) + ApiClientABC (низкоуровневый HTTP).
  - Зафиксировать единые сигнатуры и использовать UnifiedAPIClientImpl везде, где нужен HTTP клиент.
- RecordSource:
  - Оставить текущий Protocol для итерации (iter_records() -> Iterable[list[RawRecord]]), чтобы избежать лишних классов.
  - Унифицировать конструкторы через фабрики: обязательно принимать `chunk_size`, опционально `limit`, специфичные параметры через именованные аргументы.
- ExtractionService:
  - Оставить ExtractionServiceABC без изменений (сигнатуры соответствуют). Допустить общие утилиты (batch адаптер), без смены имен.
- Extractor/Transformer/Validator/Loader:
  - ExtractorABC оставить `extract(**kwargs)`; в реализациях явно поддержать `limit: int | None`.
  - ValidatorABC: подтвердить `validate(df)`, `is_valid(df)`; PanderaValidatorImpl уже соответствует.
  - Loader vs OutputWriter: унифицировать вызовы через фасад UnifiedOutputWriterImpl; адаптер LoaderABC может делегировать в OutputWriter.write_result, без увеличения числа классов.
- Нормализация:
  - Сохранить методы NormalizationServiceABC; где есть дублирующие алиасы (apply_normalize_fields), оставить один метод и алиас как совместимость.

## Миграция без ломки
1. Ввести фабрики для RecordSource (без новых классов): единая точка создания по типу источника (api/csv/id_list/memory) с согласованными аргументами.
2. В пайплайнах заменить прямые вызовы специфичных конструкторов на фабрики, не меняя сигнатуры `extract()`.
3. Вызовы записи унифицировать через UnifiedOutputWriterImpl; если где-то используется иной Loader — сделать делегирование.
4. Обновить импорты на `bioetl.infrastructure.http` (RetryPolicy уже там) и `UnifiedAPIClientImpl` для consistency.
5. Тесты: обновить фикстуры для источников (единые аргументы), проверить unit/integration/golden; цель покрытия ≥85%.

## Тесты и CI
- Unit без сети; мок HTTP в DataClient, проверка пагинации ChemblPaginatorImpl.
- Integration: минимальные прогоны пайплайнов с фиктивными источниками.
- Golden: ключевые трансформации и экспорт; детерминизм: фиксированный порядок колонок/стррок, UTC, атомарная запись.
- CI: ruff/black/isort/mypy --strict, pytest + coverage; секреты не в логах.

## Документация
- Обновить `docs/project/00-rules-summary.md` и интерфейсные разделы (без NN-файлов добавления).
- ADR при существенной унификации (без ломки API — можно как maintenance note).

## Критерии готовности
- Все тесты зелёные, покрытие ≥85%.
- Нет новых классов (кроме ABC/Protocol) без удаления эквивалентных — соблюдение zero-sum.
- Пайплайны используют фабрики источников и фасад записи.
- Импорты единообразны, логирование только через UnifiedLogger, HTTP через UnifiedAPIClientImpl.

## Следующие шаги
- Реализовать фабрики RecordSource и адаптер Loader→OutputWriter.
- Пройтись по пайплайнам и заменить конструирование на фабрики.
- Обновить тестовые фикстуры и прогнать CI.

Подтвердите план — после подтверждения начну миграцию по шагам и верификацию.