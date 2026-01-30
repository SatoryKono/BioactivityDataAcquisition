# Implementation Prompts — 4-Phase Publication Fallback

**Связан с**: `consolidated-fallback-audit-and-plan.md`
**Порядок выполнения**: Этап 1 → 2 → 3 → 4 (строго последовательно по этапам, параллельно внутри этапа 3)

---

## Этап 1: Foundation

### Промт 1.1 — ADR-033

```
Создай ADR-033-four-phase-publication-fallback.md в docs/02-architecture/decisions/.

Контекст:
Текущая система publication fallback поддерживает 3 фазы: batch primary ID lookup →
title fallback → title-only. Однако cross-ID resolution (DOI↔PMID) отсутствует:
- OpenAlex/SemanticScholar: только DOI, нет PMID lookup
- PubMed: только PMID, нет DOI lookup
- CrossRef: только DOI (нет PMID API — Phase 2 пропускается)

Решение: Расширить стратегию до 4 фаз добавлением Phase 2 (Alternate ID lookup)
через новый Protocol ExtendedFallbackDataSourcePort, не изменяя существующий
FilterableDataSourcePort.

Формат: следуй шаблону существующих ADR в docs/02-architecture/decisions/
(Status: Proposed, Context, Decision, Consequences, References).

Ссылки на верифицированные файлы:
- Текущий порт: src/bioetl/domain/ports/data_source.py:82-168
- BaseTitleFallbackHandler: src/bioetl/infrastructure/adapters/common/base_title_fallback.py
- InputFilterConfig: src/bioetl/domain/filtering/input_config.py:47-55
- FilteredDataSource: src/bioetl/application/core/filtered_data_source.py:94-167

ВАЖНО: Перед написанием прочитай 2-3 существующих ADR для сверки формата.
```

### Промт 1.2 — ExtendedFallbackDataSourcePort

```
Добавь новый Protocol ExtendedFallbackDataSourcePort в
src/bioetl/domain/ports/data_source.py.

Требования:
1. Наследует FilterableDataSourcePort (Protocol)
2. Декоратор @runtime_checkable
3. Один метод fetch_filtered_with_extended_fallback() с сигнатурой:
   - entity_type: str
   - filter_ids: list[str]
   - filter_field: str
   - fallback_mapping: dict[str, str]        # primary_id → fallback_value (title)
   - alternate_id_mapping: dict[str, str]     # primary_id → alternate_id
   - alternate_id_field: str                  # e.g. "pmid" for DOI→PMID
   - limit: int | None = None
   - Returns: AsyncIterator[dict[str, Any]]
4. Docstring в стиле существующих Protocol (см. FilterableDataSourcePort)
5. Не менять существующие Protocol!

Контекст: текущий FilterableDataSourcePort (строки 82-168) содержит fetch_filtered,
fetch_multi_filtered, fetch_filtered_with_fallback. Новый Protocol расширяет, не заменяет.

После изменений: make lint && make test
```

### Промт 1.3 — InputFilterConfig + alternate_id_column

```
Расширь InputFilterConfig в src/bioetl/domain/filtering/input_config.py:

1. Добавь поле alternate_id_column: str | None = None в dataclass InputFilterConfig
   (после fallback_column, строка ~53)
2. Если есть InputFilterContext — добавь alternate_id_mapping: dict[str, str]
   (маппинг primary_id → alternate_id)
3. Обнови валидацию: alternate_id_column имеет смысл только при наличии column_name
   (single-column mode)

НЕ менять: columns, direct_filter_ids, direct_fallback_mapping — это другие режимы.

Прочитай файл перед изменениями. После: make lint && make test
```

### Промт 1.4 — BaseAlternateIdFallbackHandler

```
Создай класс BaseAlternateIdFallbackHandler в
src/bioetl/infrastructure/adapters/common/base_alternate_id_fallback.py.

Требования:
1. Наследует BaseTitleFallbackHandler
   (из src/bioetl/infrastructure/adapters/common/base_title_fallback.py)
2. Добавляет Phase 2: async method process_missing_by_alternate_id()
   - Принимает: missing_ids (list[str]), alternate_id_mapping (dict[str,str]),
     search_fn (Callable), normalize_fn (Callable | None)
   - Для каждого missing_id ищет alternate_id в маппинге
   - Если найден — вызывает search_fn(alternate_id)
   - Yield найденные записи, добавляя _lookup_method = "alternate_id"
   - Логирует события: {provider}_alternate_id_fallback_attempt/success/not_found
3. Orchestration method fetch_with_extended_fallback() реализует 4-phase:
   Phase 1: batch primary → Phase 2: alternate ID → Phase 3: title → Phase 4: title-only

Перед написанием прочитай BaseTitleFallbackHandler — наследуй стиль, логирование,
паттерн событий.

После: make lint && make test
```

---

## Этап 2: CSV & Application

### Промт 2.1 — CsvFilterReader: load_filter_with_two_fallbacks

```
Добавь метод load_filter_with_two_fallbacks() в
src/bioetl/infrastructure/adapters/input/csv_filter_reader.py.

Требования:
1. Читает CSV с тремя колонками: primary_column, alternate_id_column, fallback_column
2. Возвращает tuple: (filter_ids, fallback_mapping, alternate_id_mapping)
   - filter_ids: list[str] — primary IDs + маркеры __title_only_N__
   - fallback_mapping: dict[str, str] — primary_id → title (как в существующем коде)
   - alternate_id_mapping: dict[str, str] — primary_id → alternate_id
3. Обратная совместимость: если alternate_id_column отсутствует в CSV — alternate_id_mapping пуст
4. Повторяет паттерн маркеров __title_only_N__ из load_filter_with_fallback() (строки 184-189)

Перед написанием прочитай существующие методы load_filter() и load_filter_with_fallback()
в этом файле — следуй их стилю.

Также обнови InputFilterPort (если есть) в domain/ports/ для нового метода.

После: make lint && make test
```

### Промт 2.2 — FilteredDataSource: alternate_id dispatch

```
Расширь FilteredDataSource в src/bioetl/application/core/filtered_data_source.py.

Требования:
1. При загрузке фильтра (single-column mode) — если InputFilterConfig.alternate_id_column
   задан, вызывать load_filter_with_two_fallbacks() и сохранять alternate_id_mapping
2. При вызове адаптера — проверять isinstance(adapter, ExtendedFallbackDataSourcePort):
   - Если да и alternate_id_mapping не пуст → вызывать
     fetch_filtered_with_extended_fallback() с alternate_id_mapping
   - Иначе → fallback на существующий fetch_filtered_with_fallback()
3. Для multi-column и direct IDs режимов — без изменений

ВАЖНО: FilteredDataSource находится в application слое. Импортировать Protocol из
domain/ports/data_source.py (допустимо по матрице импортов).
НЕ импортировать из infrastructure!

Перед написанием прочитай filtered_data_source.py целиком — особенно _load_single_column_filter
(строки 148-167) и _fetch_with_fallback (строки 277-294).

После: make lint && make test
```

### Промт 2.3 — Unit tests для Foundation + CSV

```
Напиши unit-тесты для:

1. ExtendedFallbackDataSourcePort — contract test (по аналогии с существующими
   architecture tests в tests/architecture/)
2. BaseAlternateIdFallbackHandler:
   - Phase 2 с найденным alternate_id
   - Phase 2 с отсутствующим alternate_id → fallback to Phase 3
   - Пустой alternate_id_mapping → сразу Phase 3
   - Логирование событий (alternate_id_fallback_attempt/success/not_found)
3. CsvFilterReader.load_filter_with_two_fallbacks():
   - 3-column CSV (primary, alternate, title)
   - 2-column legacy CSV (alternate_id_mapping пуст)
   - Title-only строки → маркеры __title_only_N__
4. FilteredDataSource:
   - isinstance dispatch на ExtendedFallbackDataSourcePort
   - Fallback на FilterableDataSourcePort если extended не реализован
   - alternate_id_column=None → стандартное поведение

Используй in-memory fakes для адаптеров (предпочтительно по RULES.md §4.2).
Размести тесты в соответствующих директориях tests/unit/.

После: make test-unit
```

---

## Этап 3: Adapters (параллельно)

### Промт 3.1 — OpenAlex PMID lookup

```
Реализуй PMID lookup в OpenAlex адаптере:
src/bioetl/infrastructure/adapters/openalex/client.py

Требования:
1. Добавь метод _search_by_pmid(pmid: str) -> dict[str, Any] | None:
   - Запрос: GET /works?filter=ids.pmid:{pmid}&select={fields}
   - Использовать существующий UnifiedHTTPClient (self._http)
   - Вернуть первый результат или None
2. Реализуй ExtendedFallbackDataSourcePort.fetch_filtered_with_extended_fallback():
   - Phase 1: существующий batch DOI lookup (переиспользовать код)
   - Phase 2: для unresolved DOIs → ищем PMID в alternate_id_mapping → _search_by_pmid()
   - Phase 3-4: делегировать в BaseTitleFallbackHandler / BaseAlternateIdFallbackHandler
3. Обнови guard в fetch_filtered_with_fallback (строки 326-332) — оставить DOI-only
   для старого метода, новый метод поддерживает DOI+PMID

Перед написанием: прочитай client.py целиком, особенно fetch_filtered_with_fallback
(строки 295-390) и _search_by_title (если есть).

Rate limit: OpenAlex polite pool ≤ 10 req/sec. Убедись что _search_by_pmid использует
существующий rate limiter.

После: make lint && make test
Также: создай VCR-кассету для PMID lookup (tests/fixtures/vcr/openalex/).
```

### Промт 3.2 — SemanticScholar PMID batch

```
Реализуй PMID batch lookup в SemanticScholar адаптере:
src/bioetl/infrastructure/adapters/semanticscholar/adapter.py

Требования:
1. Добавь метод _batch_pmid_phase(pmids, resolved, limit, fetched):
   - POST /paper/batch с ids=["PMID:{pmid}", ...]
   - Переиспользовать паттерн существующего _batch_doi_phase()
   - Batch size: до 500 (S2 API limit)
2. Реализуй ExtendedFallbackDataSourcePort.fetch_filtered_with_extended_fallback():
   - Phase 1: batch DOI → Phase 2: batch PMID → Phase 3-4: title fallback
3. Сохранить существующий fetch_filtered_with_fallback() без изменений

Перед написанием: прочитай adapter.py целиком, особенно _batch_doi_phase()
и fetch_filtered_with_fallback() (строки 283-345).

Rate limit: S2 API — 1 req/sec для unauthenticated, 10 req/sec с API key.
Убедись что _batch_pmid_phase использует существующий rate limiter.

После: make lint && make test
VCR-кассета: tests/fixtures/vcr/semanticscholar/
```

### Промт 3.3 — PubMed DOI lookup

```
Реализуй DOI → PMID lookup в PubMed адаптере:
src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py

Требования:
1. Добавь метод _search_by_doi(doi: str) -> list[str]:
   - esearch: term="{doi}"[DOI]&db=pubmed&retmode=json
   - Вернуть список PMID из esearch result
2. Добавь метод _fetch_by_dois(dois: list[str], limit) -> AsyncIterator[dict]:
   - Для каждого DOI: _search_by_doi() → получить PMIDs → _yield_articles_from_pmids()
   - Добавить _lookup_method = "doi_to_pmid"
3. Реализуй ExtendedFallbackDataSourcePort.fetch_filtered_with_extended_fallback():
   - Phase 1: batch PMID lookup (существующий)
   - Phase 2: для unresolved → ищем DOI в alternate_id_mapping → _search_by_doi → efetch
   - Phase 3-4: title fallback
4. Сохранить fetch_filtered() и fetch_filtered_with_fallback() без изменений

Перед написанием: прочитай pubmed_client.py целиком, особенно fetch_filtered()
(строки 214-250) и _yield_articles_from_pmids().

Rate limit: PubMed 3 req/sec (с API key 10 req/sec). Убедись что DOI search
использует существующий rate limiter.

ВАЖНО: PubMed адаптер использует BaseSyncAdapter (run_in_executor) для eutils.
Проверь, нужен ли async wrapper для esearch.

После: make lint && make test
VCR-кассета: tests/fixtures/vcr/pubmed/
```

### Промт 3.4 — Unit tests для адаптеров

```
Напиши unit-тесты для Phase 2 каждого адаптера:

1. OpenAlex _search_by_pmid():
   - PMID найден → возвращает запись
   - PMID не найден → None
   - Rate limit / HTTP error → graceful handling
2. SemanticScholar _batch_pmid_phase():
   - Batch PMID lookup — partial hits
   - Пустой список → no requests
   - API error → retry/fallback
3. PubMed _search_by_doi():
   - DOI найден → возвращает PMIDs
   - DOI не найден → пустой список
   - Multiple PMIDs for one DOI

Для каждого адаптера используй in-memory fakes для HTTP client.
Размести в tests/unit/infrastructure/adapters/{provider}/.

После: make test-unit
```

---

## Этап 4: Config & Docs

### Промт 4.1 — Обновление YAML конфигов

```
Обнови YAML конфиги publication pipelines, добавив alternate_id_column:

1. configs/filter/entities/crossref/publication.yaml:
   alternate_id_column: "pmid"    # DOI primary, PMID alternate

2. configs/filter/entities/openalex/publication.yaml:
   alternate_id_column: "pmid"    # DOI primary, PMID alternate

3. configs/filter/entities/semanticscholar/publication.yaml:
   alternate_id_column: "pmid"    # DOI primary, PMID alternate

4. configs/filter/entities/pubmed/publication.yaml:
   alternate_id_column: "doi"     # PMID primary, DOI alternate

Каждый конфиг:
- Добавить alternate_id_column после fallback_column
- Добавить комментарий с пояснением
- НЕ менять существующие поля

Перед изменениями прочитай каждый файл. После: make lint && make test
```

### Промт 4.2 — Документация

```
Обнови документацию:

1. Если ADR-033 ещё не создан — создай (см. Промт 1.1)
2. Обнови docs/verification/consolidated-fallback-audit-and-plan.md:
   - Добавь раздел "Implementation Status" с чеклистом выполненных этапов
3. Проверь, нужно ли обновить:
   - RULES.md §2 (если Medallion затронут)
   - docs/providers/ (описание fallback по провайдерам)
   - CLAUDE.md §2.3 (если появились новые "ложные утверждения" для предотвращения)

НЕ трогать CLAUDE.md если нет реальных изменений в архитектурных пояснениях.
```

---

## Важные ограничения для всех промтов

1. **Матрица импортов**: domain ← application ← composition → infrastructure.
   Адаптеры НЕ импортируют из application.
2. **DI**: все зависимости через конструктор. Никаких `import` конкретных реализаций
   в domain/application.
3. **VCR**: все HTTP-вызовы должны иметь VCR-кассеты для CI.
4. **Тесты**: in-memory fakes предпочтительны (RULES.md §4.2).
5. **Проверка перед коммитом**: `make lint && make test` после каждого промта.
6. **Верификация**: перед утверждениями о коде — проверять файлы (REQ-ARCH-040).
