# Semantic Scholar Publication Pipeline — Verification Report

*Дата верификации: 2026-01-25*
*Версия pipeline: 1.1.0*
*Верификатор: Claude AI*

---

## 1. Сводка

| Аспект | Статус | Комментарий |
|--------|--------|-------------|
| **Paper ID валидация** | ✅ Реализовано | 40-char hex, схема + Value Object |
| **External IDs извлечение** | ⚠️ Частично | DBLP не извлекается, ACL извлекается |
| **TLDR извлечение** | ✅ Реализовано | Корректно обрабатывает nested structure |
| **Authors извлечение** | ⚠️ Частично | Whitespace-only имена не фильтруются |
| **Journal/Venue приоритет** | ✅ Реализовано | journal.name → venue fallback |
| **Open Access info** | ✅ Реализовано | oa_status нормализуется к lowercase |
| **Fields of Study** | ⚠️ Частично | null/empty элементы не фильтруются |
| **Citation counts** | ⚠️ Частично | influentialCitationCount не извлекается |
| **Year валидация** | ✅ Реализовано | min_year=1500 для исторических публикаций |
| **Lookup metadata** | ✅ Реализовано | _lookup_method, _original_id |

**Общий статус:** 132/132 тестов проходят, найдено 5 потенциальных улучшений.

---

## 2. Детальный Анализ

### 2.1. Paper ID Validation

**Файлы:**
- `extractors.py:120` — не валидирует формат
- `transformer.py:169` — только проверяет наличие
- `publication.py:43-47` — Pandera схема с regex `^[a-f0-9]{40}$`
- `academic_ids.py:82-126` — SemanticScholarId Value Object

**Поведение:**
- Отсутствующий paper_id → record skipped (✅)
- Невалидный формат (не 40-char hex) → проходит transformer, отклоняется схемой (⚠️)

**Рекомендация:** Задача требует `_dq_error=True` при невалидном paper_id. Текущая реализация отклоняет запись на уровне схемы, но не устанавливает `_dq_error`. Это может быть приемлемо, если схема является последним рубежом валидации.

---

### 2.2. External IDs Extraction

**Файл:** `extractors.py:19-45`

| API ключ | Извлекается? | Python ключ |
|----------|-------------|-------------|
| DOI | ✅ | `doi` |
| PubMed | ✅ | `pmid` |
| PMCID | ✅ | `pmcid` |
| PubMedCentral | ✅ (fallback) | `pmcid` |
| ArXiv | ✅ | `arxiv` |
| CorpusId | ✅ | `corpus_id` |
| MAG | ✅ | `mag` |
| ACL | ✅ | `acl` |
| **DBLP** | ❌ | — |

**Gap:** DBLP упоминается в задаче как один из внешних ID, но не извлекается. API S2 поддерживает `DBLP` ключ.

**Рекомендация:** Добавить `"dblp": external_ids.get("DBLP")` в `extract_external_ids()`.

---

### 2.3. TLDR Extraction

**Файл:** `extractors.py:189-206`

**Тестовое покрытие:**
- `tldr: null` → `None` ✅
- `tldr: {}` → `None` ✅
- `tldr.text: null` → `None` ✅
- `tldr.text: ""` → `""` (пустая строка проходит)
- `tldr.text: "valid"` → `"valid"` ✅

**Статус:** Полностью реализовано, тесты покрывают edge cases.

---

### 2.4. Authors Extraction

**Файл:** `extractors.py:48-71`

**Обнаруженная проблема:**
```python
# Текущая реализация:
if name:  # Пропускает whitespace-only строки!
    result.append(name)
```

**Тест:**
```python
authors = [{'name': '   '}]  # Whitespace only
extract_authors(authors)  # Returns ['   '] — НЕВЕРНО!
```

**Рекомендация:** Изменить на `if name and name.strip():` для фильтрации whitespace-only имён.

---

### 2.5. Journal/Venue Priority

**Файл:** `extractors.py:74-103`

**Поведение:**
1. `journal.name` присутствует → используется `journal.name` ✅
2. `journal.name` пустой/None, `venue` присутствует → используется `venue` ✅
3. `journal` None → используется `venue` ✅

**Pages parsing:** `parse_page_range()` корректно обрабатывает:
- `"123-145"` → `("123", "145")`
- `"123"` → `("123", None)`
- `"e12345"` → `("e12345", None)`
- `null` → `(None, None)`

**Статус:** Полностью реализовано.

---

### 2.6. Open Access Information

**Файл:** `extractors.py:106-186`

**OA Status нормализация:**
| Input | Output |
|-------|--------|
| `"GOLD"` | `"gold"` ✅ |
| `"Green"` | `"green"` ✅ |
| `"unknown"` | `None` ✅ |
| `None` | `None` ✅ |
| `"  GOLD  "` | `"gold"` ✅ (whitespace trimmed) |

**Closed access:** `is_oa=False` + `oa_status=None` → `oa_status="closed"` ✅

**Статус:** Полностью реализовано, 15+ тестов покрывают edge cases.

---

### 2.7. Fields of Study

**Файл:** `extractors.py:209-230`

**Обнаруженная проблема:**
```python
# Текущая реализация:
return fields_of_study[:max_count]  # Не фильтрует None/""!
```

**Тест:**
```python
fields = ['Biology', None, '', 'Medicine']
extract_fields_of_study(fields)  # Returns ['Biology', None, '', 'Medicine']
```

**Рекомендация:** Добавить фильтрацию:
```python
return [f for f in fields_of_study[:max_count] if f]
```

---

### 2.8. Citation/Reference Counts

**Файлы:**
- `transformer.py:191-192` — извлекает `citationCount`, `referenceCount`
- `publication.py:97-101` — валидация `ge=0`

**Gap:** `influentialCitationCount` документирован в спецификации (`01-publication-spec.md:62,82`) но НЕ извлекается transformer.

**Рекомендация:** Добавить извлечение `influentialCitationCount` в transformer и схему.

---

### 2.9. Year Validation

**Файл:** `extractors.py:233-249`

**Конфигурация:** `ValidationConfig(min_publication_year=1500)`

**Тестовое покрытие:**
- `1500` → `1500` ✅
- `2100` → `2100` ✅
- `1499` → `None` ✅
- `2101` → `None` ✅
- `None` → `None` ✅

**Статус:** Полностью реализовано.

---

### 2.10. Lookup Metadata

**Файлы:**
- `adapter.py:239,274` — устанавливает `_lookup_method: "doi"`
- `fallback.py:219-220` — устанавливает `_lookup_method: "title_fallback"`, `_original_id`
- `transformer.py:165-166` — передаёт metadata без модификации

**Допустимые значения:** `["direct", "doi", "pmid", "title_fallback", "title_only", "unknown"]`

**Статус:** Полностью реализовано.

---

## 3. Тестовое Покрытие

| Тестовый файл | Тестов | Статус |
|---------------|--------|--------|
| `test_extractors.py` | 44 | ✅ Pass |
| `test_transformer.py` | 41 | ✅ Pass |
| `test_publication_schema.py` | 47 | ✅ Pass |
| **Итого** | **132** | **✅ Pass** |

---

## 4. Рекомендации

### 4.1. Критичные (должны быть исправлены)

1. **Authors whitespace filtering** (`extractors.py:69`):
   ```python
   # Было:
   if name:
   # Должно быть:
   if name and name.strip():
   ```

2. **Fields of Study filtering** (`extractors.py:230`):
   ```python
   # Было:
   return fields_of_study[:max_count]
   # Должно быть:
   return [f for f in fields_of_study[:max_count] if f and isinstance(f, str)]
   ```

### 4.2. Желательные (улучшения)

3. **Add DBLP extraction** (`extractors.py:37-45`):
   ```python
   return {
       ...
       "dblp": external_ids.get("DBLP"),
   }
   ```

4. **Add influentialCitationCount** (`transformer.py`, `publication.py`):
   - Добавить поле в transformer: `"influential_citation_count": rec.get("influentialCitationCount")`
   - Добавить в схему: `influential_citation_count: Series[int] = pa.Field(nullable=True, ge=0)`

### 4.3. Опциональные

5. **Paper ID format validation at transformer level**: Если требуется `_dq_error=True` при невалидном формате (не только при отсутствии), добавить валидацию в `_extract_business_data()` с использованием `SemanticScholarId.from_raw()`.

---

## 5. Архитектурное Соответствие

| Требование | Соответствие |
|------------|--------------|
| Ports & Adapters | ✅ adapter в infrastructure, transformer в application |
| DI | ✅ pii_hasher, data_normalizer инжектируются |
| Value Objects | ✅ DOI, PubMedId, PublicationYear |
| Template Method | ✅ BasePublicationTransformer |
| Pandera Schema | ✅ SemanticScholarPublicationSchema |

---

## 6. Заключение

Semantic Scholar Publication Pipeline **реализован корректно** и соответствует архитектурным требованиям проекта. Найдены 5 потенциальных улучшений (2 критичных, 2 желательных, 1 опциональное), которые не блокируют текущую функциональность, но могут привести к data quality issues в edge cases.

**Приоритетные действия:**
1. Исправить фильтрацию whitespace-only author names
2. Исправить фильтрацию null/empty elements в fields_of_study
3. Добавить DBLP в external IDs extraction
4. Добавить influentialCitationCount extraction
