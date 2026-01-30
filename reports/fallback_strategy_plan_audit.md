# Architecture Audit Report
Дата: 2026-01-30
Scope: план модификации fallback-стратегии для publication pipelines

## Executive Summary
- Total findings: 5
- Critical (MUST): 3
- Moderate (SHOULD): 2
- Informational (MAY): 0

## [MUST] OpenAlex: в коде нет PMID-lookup, план утверждает обратное

**Location**: `src/bioetl/infrastructure/adapters/openalex/client.py:301-356`

**Rule Violated**: REQ-ARCH-040 — запрещены утверждения без верификации (фактическая ошибка в плане).

**Evidence**:
```python
        # Validate filter_field - fallback only supports DOI-based lookups
        if filter_field != "doi":
            self.logger.warning(
                "unsupported_filter_field_for_fallback",
                field=filter_field,
                msg="OpenAlex fallback only supports 'doi' filtering, skipping",
            )
            return
```

**Impact**: План полагается на существующую поддержку PMID (Phase 2), но текущая реализация ограничена DOI. Реализация Phase 2 для OpenAlex требует нового кода (PMID → /works?filter=ids.pmid:{pmid}).

**Recommendation**:
```python
# Добавить отдельный PMID-поиск в OpenAlex адаптер
async def _search_by_pmid(self, pmid: str) -> dict[str, Any] | None:
    params = self._build_base_params()
    params["filter"] = f"ids.pmid:{pmid}"
    # запрос /works
```

**Verification**: `sed -n '295,380p' src/bioetl/infrastructure/adapters/openalex/client.py`

---

## [MUST] Semantic Scholar: отсутствует PMID batch lookup

**Location**: `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py:283-342`

**Rule Violated**: REQ-ARCH-040 — утверждение без подтверждения (в плане заявлена поддержка PMID).

**Evidence**:
```python
        valid_dois = [d for d in filter_ids if d and d.strip()]
        title_only_entries = [d for d in filter_ids if not d or not d.strip()]

        # Phase 1: Batch DOI lookup
        async for record in self._batch_doi_phase(
            valid_dois, resolved_dois, limit, fetched
        ):
            ...
```

**Impact**: Плановая Phase 2 (PMID → /paper/batch PMID:ID) отсутствует в текущем коде. Для реализации нужно добавлять новые методы и тесты.

**Recommendation**:
```python
# Добавить PMID batch lookup
ids = [f"PMID:{pmid}"]
# POST /paper/batch
```

**Verification**: `sed -n '283,360p' src/bioetl/infrastructure/adapters/semanticscholar/adapter.py`

---

## [MUST] Противоречие в разделе «Variant A»

**Location**: `src/bioetl/domain/ports/data_source.py:82-168`

**Rule Violated**: REQ-ARCH-040 — план заявляет «не менять порт», но далее предлагает добавить новый метод в `FilterableDataSourcePort`.

**Evidence**:
```python
class FilterableDataSourcePort(DataSourcePort, Protocol):
    ...
    def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ...
```

**Impact**: Добавление нового метода в `FilterableDataSourcePort` — это изменение интерфейса, которое требует обновить все адаптеры, mixin-ы и архитектурные тесты. Нельзя одновременно заявлять «порт не меняем» и добавлять метод.

**Recommendation**:
```python
# Вариант: новый Protocol
class ExtendedFallbackDataSourcePort(FilterableDataSourcePort, Protocol):
    def fetch_filtered_with_extended_fallback(...):
        ...
```

**Verification**: `sed -n '82,190p' src/bioetl/domain/ports/data_source.py`

---

## [SHOULD] CSV title-only записи используют маркеры, не пустые строки

**Location**: `src/bioetl/infrastructure/adapters/input/csv_filter_reader.py:120-196`

**Rule Violated**: REQ-ARCH-040 — описание формата CSV в плане не совпадает с фактической логикой.

**Evidence**:
```python
                elif fallback_str:
                    # Case 3: Record has title only (empty DOI)
                    # Use indexed marker for title-only lookup (Phase 3)
                    marker = f"__title_only_{title_only_count}__"
                    all_ids.append(marker)
                    fallback_mapping[marker] = fallback_str
```

**Impact**: План описывает title-only как пустые строки в `filter_ids`, но реально используются маркеры `__title_only_N__`. Это влияет на логирование и на то, какая фаза будет задействована в адаптерах.

**Recommendation**:
```markdown
Уточнить формат CSV:
- title-only записи кодируются как __title_only_N__
- fallback_mapping хранит marker → title
```

**Verification**: `sed -n '120,210p' src/bioetl/infrastructure/adapters/input/csv_filter_reader.py`

---

## [SHOULD] Формат CSV фильтров не унифицирован (PubMed)

**Location**: `configs/filter/entities/pubmed/publication.yaml:17-28`

**Rule Violated**: REQ-ARCH-040 — план утверждает единый формат (doi,title), но PubMed использует `pubmed_id`.

**Evidence**:
```yaml
input_filter:
  enabled: true
  source_path: "data/input/pubmed.csv"
  column_name: "pubmed_id"
  filter_field: "pmid"
  batch_size: 100
  fallback_column: "title"
```

**Impact**: План не отражает фактическую схему CSV для PubMed; это вводит в заблуждение при подготовке данных.

**Recommendation**:
```markdown
Развести форматы CSV по провайдерам:
- CrossRef/OpenAlex/S2: doi,title
- PubMed: pubmed_id,title
```

**Verification**: `sed -n '17,40p' configs/filter/entities/pubmed/publication.yaml`

---

## Updated Plan (скорректированная версия)

### 1. Текущее состояние (верифицировано)
1. **3‑phase fallback** реализован для CrossRef, OpenAlex, PubMed, Semantic Scholar через `BaseTitleFallbackHandler`:
   - Phase 1: batch lookup по primary ID
   - Phase 2: title fallback (`process_missing_dois`)
   - Phase 3: title-only (`process_title_only_entries`)
2. **UniProt** использует общий fallback без title-based логики (fallback значения передаются в query).
3. **CSV title-only** записи кодируются маркерами `__title_only_N__` в `filter_ids`.
4. **PMID lookup в OpenAlex и Semantic Scholar отсутствует** — требуется новая реализация.

### 2. Цели изменения
Расширить текущую стратегию до 4 фаз:
1) Primary ID → 2) Alternate ID → 3) Title fallback → 4) Title-only.

### 3. Архитектурный подход (минимальный риск)
1. **Новый Protocol, а не изменение существующего порта**:
   - Создать `ExtendedFallbackDataSourcePort` с методом `fetch_filtered_with_extended_fallback()`.
   - `FilteredDataSource` должен проверять `isinstance(adapter, ExtendedFallbackDataSourcePort)`.
2. **InputFilterConfig**:
   - Добавить `alternate_id_column: str | None = None`.
3. **InputFilterPort / CsvFilterReader**:
   - Новый метод `load_filter_with_two_fallbacks()` для чтения primary + alternate + title.
4. **Adapters**:
   - OpenAlex: добавить PMID lookup через `GET /works?filter=ids.pmid:{pmid}`.
   - Semantic Scholar: добавить PMID lookup через `POST /paper/batch` с `PMID:{pmid}`.
   - PubMed: добавить DOI → PMID через `esearch` с `"{doi}"[DOI]`.
   - CrossRef: Phase 2 пропускается (нет PMID API). Отдельный ADR для PMID→DOI resolve.

### 4. Конфигурации
- Добавить `alternate_id_column` в configs для publication pipelines.
- Учесть различие схем CSV:
  - DOI-провайдеры: `doi,pmid,title` (pmid optional)
  - PubMed: `pubmed_id,doi,title` (doi optional)

### 5. Тестирование
- Новый unit-тест для базового alternate-id handler.
- Обновить тесты адаптеров для Phase 2.
- Проверить `FilteredDataSource` на загрузку двух fallback колонок.

### 6. Документация
- ADR: `ADR-033-four-phase-publication-fallback.md`.
- Обновить docs по input_filter CSV схемам.

## Verification Log
- `sed -n '295,380p' src/bioetl/infrastructure/adapters/openalex/client.py`
- `sed -n '283,360p' src/bioetl/infrastructure/adapters/semanticscholar/adapter.py`
- `sed -n '82,190p' src/bioetl/domain/ports/data_source.py`
- `sed -n '120,210p' src/bioetl/infrastructure/adapters/input/csv_filter_reader.py`
- `sed -n '17,40p' configs/filter/entities/pubmed/publication.yaml`
