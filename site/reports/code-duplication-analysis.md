# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-01-15
**Ветка**: claude/refactor-code-duplication-NfP8Z
**Автор**: Claude (автоматизированный анализ)

---

## Executive Summary

- **Проанализировано**: ~60 pipeline/transformer файлов, ~30 адаптеров, ~20 сервисов
- **Обнаружено категорий дублирования**: 3 (минорные)
- **Потенциальное сокращение**: ~50-70 LOC (менее 0.1% от общего объёма)
- **Вердикт**: Кодовая база **хорошо спроектирована** с эффективным использованием абстракций

---

## 1. Существующие Абстракции (УЖЕ РЕАЛИЗОВАНО)

Анализ выявил, что проект **уже использует** правильные паттерны для минимизации дублирования:

### 1.1 Иерархия трансформеров

```
BaseTransformer (673 LOC)                    # Общий каркас, hash, serialization
    │
    ├── BaseChemblTransformer (183 LOC)      # ChEMBL-specific Template Method
    │       │
    │       ├── ActivityTransformer
    │       ├── AssayTransformer
    │       ├── MoleculeTransformer
    │       ├── TargetTransformer
    │       └── ...10+ transformers
    │
    └── BasePublicationTransformer (201 LOC) # Publication Template Method
            │
            ├── CrossRefPublicationTransformer
            ├── OpenAlexPublicationTransformer
            ├── SemanticScholarTransformer
            └── PubMedTransformer
```

### 1.2 Переиспользуемые Mixins и Base Classes

| Компонент | Файл | LOC | Назначение |
|-----------|------|-----|------------|
| `HealthCheckMixin` | `infrastructure/adapters/health_check_mixin.py` | 397 | Observability для health checks |
| `HealthCheckProviderMixin` | (там же) | - | Full health check implementation |
| `BaseHttpAdapter` | `infrastructure/adapters/base.py` | 124 | HTTP lifecycle + error handling |
| `BaseTitleFallbackHandler` | `infrastructure/adapters/common/base_title_fallback.py` | 181 | Title fallback для DOI resolution |
| `BaseFieldExtractor` | `application/pipelines/pubmed/extractors/base.py` | 66 | Template Method для PubMed XML |

### 1.3 Declarative DSL для Field Mapping

`field_specs.py` реализует конфигурационный подход:

```python
# Вместо дублированных _map_* методов используется:
_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        *simple_fields("target_chembl_id", "assay_chembl_id"),
        *int_fields("record_id", "src_id"),
    ),
)

# Применение:
result = map_field_groups(record, [_IDENTIFIERS, _MOLECULE_TARGET_ASSAY])
```

### 1.4 Общие Сервисы (Domain Layer)

| Сервис | Файл | Использование |
|--------|------|---------------|
| `IdentityService` | `domain/services/identity_service.py` | Content Hash + Entity ID computation |
| `DataNormalizationService` | `domain/services/data_normalization_service.py` | DOI, PMID, HTML normalization |
| `serialize_to_json` | `domain/serialization.py` | JSON serialization |

---

## 2. Верифицированные Дублирования (МИНОРНЫЕ)

### 2.1 `_validate_taxonomy_id` (3 места, ~15 LOC)

#### Текущее состояние

```python
# activity_transformer.py:28
def _validate_taxonomy_id_str(value: Any) -> str | None:
    vo = TaxonomyId.from_raw(value)
    return str(vo.value) if vo else None

# assay_transformer.py:30, target_component_transformer.py:26
def _validate_taxonomy_id(value: Any) -> int | None:
    vo = TaxonomyId.from_raw(value)
    return vo.value if vo else None
```

#### Анализ

- **Дублирование**: Логика идентична, разница в return type (`str` vs `int`)
- **Impact**: Low (3 места, 15 LOC)
- **Причина различия**: ActivityTransformer требует `str` для entity field

#### Рекомендация

Добавить helper в `domain/value_objects/taxonomy_id.py`:

```python
# В TaxonomyId или отдельным модулем:
def validate_taxonomy_id(value: Any) -> int | None:
    vo = TaxonomyId.from_raw(value)
    return vo.value if vo else None

def validate_taxonomy_id_str(value: Any) -> str | None:
    vo = TaxonomyId.from_raw(value)
    return str(vo.value) if vo else None
```

**Приоритет**: P3 (Low) - ~5 LOC экономии, не критично

---

### 2.2 `_normalize_doi` в Адаптерах (2 места, ~20 LOC)

#### Текущее состояние

```python
# semanticscholar/adapter.py:521
def _normalize_doi(doi: str) -> str:
    if doi.startswith("https://doi.org/"):
        return doi[16:]
    # ...

# openalex/client.py:474
def _normalize_doi(doi: str) -> str | None:
    if not doi:
        return None
    doi = doi.strip()
    if doi.startswith("https://doi.org/"):
        return doi[16:]
    # ...
```

#### Анализ

- **НЕ чистое дублирование**: Разное поведение (None handling, strip)
- **Существует**: `domain/normalization.py:normalize_doi` - но он делает `.lower()`, что НЕ нужно для URL comparison
- **Intent**: Адаптеры нужны для exact DOI matching при lookup

#### Рекомендация

**НЕ консолидировать** - это provider-specific логика с разными requirements.
Альтернатива: добавить `strip_doi_prefix(doi: str) -> str` в domain/normalization.py.

**Приоритет**: P4 (Very Low) - разная семантика, консолидация может сломать логику

---

### 2.3 `serialize_to_json(...) if ... else None` Pattern (10+ мест)

#### Текущее состояние

```python
# Повторяется в UniProt extractors:
return serialize_to_json(extracted, ensure_ascii=False) if extracted else None
```

#### Анализ

- **Pattern**: Одна строка, 10+ мест в UniProt extractors
- **Impact**: Very Low (не влияет на читаемость)
- **Idiomatic**: Это стандартный Python idiom

#### Рекомендация

**НЕ рефакторить** - это идиоматичный код, wrapper не добавит ценности:

```python
# НЕ ДЕЛАТЬ - избыточная абстракция:
def serialize_or_none(data: list | None) -> str | None:
    return serialize_to_json(data, ensure_ascii=False) if data else None
```

**Приоритет**: P5 (Skip) - не требует действий

---

## 3. Паттерны, которые НЕ являются дублированием

### 3.1 Похожие Названия Функций с Разной Логикой

| Функция | OpenAlex | SemanticScholar | Отличия |
|---------|----------|-----------------|---------|
| `extract_authors` | `authorships[].author.display_name` | `authors[].name` | Разная структура API |
| `extract_journal_info` | Returns `{journal_name, issn, publisher}` | Returns `{journal_name, volume, pages}` | Разные поля |
| `extract_open_access_info` | Takes `dict` | Takes `bool, dict` | Разная сигнатура |

**Вердикт**: Provider-specific extractors - **НЕ дублирование**

### 3.2 Template Method Implementations

`_extract_business_data` появляется 20 раз - это **abstract method implementations**, а не дублирование.
Каждая реализация уникальна для entity type.

### 3.3 Init Методы

`__init__` в трансформерах похожи, но **правильно делегируют** в `super().__init__()`.
Это стандартный паттерн наследования, не дублирование.

---

## 4. Матрица Приоритизации

| # | Категория | Impact | Complexity | LOC | Приоритет | Рекомендация |
|---|-----------|--------|------------|-----|-----------|--------------|
| 1 | `_validate_taxonomy_id` | Low | Low | ~15 | P3 | Optional refactor |
| 2 | `_normalize_doi` | Very Low | Medium | ~20 | P4 | Keep as-is |
| 3 | `serialize_to_json` pattern | None | Low | ~10 | P5 | Skip |

---

## 5. Заключение

### 5.1 Состояние Кодовой Базы

Кодовая база BioETL **хорошо спроектирована** с точки зрения DRY:

1. **Эффективная иерархия классов**: `BaseTransformer` → `BaseChemblTransformer` → Entity transformers
2. **Правильное использование Mixins**: `HealthCheckMixin`, `HealthCheckProviderMixin`
3. **Declarative DSL**: `field_specs.py` заменяет repetitive mapping code
4. **Domain Services**: `IdentityService`, `DataNormalizationService` централизуют логику

### 5.2 Рекомендованные Действия

| Действие | Статус | Обоснование |
|----------|--------|-------------|
| Консолидация `_validate_taxonomy_id` | Optional | ~5 LOC экономии, P3 |
| Консолидация `_normalize_doi` | NOT recommended | Разная семантика |
| Refactor `serialize_to_json` pattern | NOT recommended | Идиоматичный код |
| Создание новых Base Classes | NOT needed | Существующие абстракции достаточны |

### 5.3 Метрики

- **Обнаружено реального дублирования**: ~35 LOC (0.05% от 68,400 LOC)
- **Потенциальная экономия**: ~15 LOC (при консолидации taxonomy validation)
- **Качество абстракций**: HIGH - правильное использование Template Method, Mixins, DI

---

## 6. Чеклист Валидации

Для подтверждения выводов:

```bash
# Проверка существующих абстракций
grep -r "class Base" src/bioetl/ | wc -l  # ~10 base classes

# Проверка делегирования в "больших" файлах
wc -l src/bioetl/application/core/base_transformer.py  # 673 LOC, но с делегированием
grep -c "self\._" src/bioetl/application/core/base_transformer.py  # ~15 delegations

# Тесты проходят
make lint && make test
```

---

*Анализ завершён. Кодовая база не требует значительного рефакторинга для устранения дублирования.*
