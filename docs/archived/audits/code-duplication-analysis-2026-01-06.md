# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-01-06
**Ветка**: main
**Автор**: Claude Code Agent

## Executive Summary

- **Проанализировано**: 13 ChEMBL трансформеров + 6 адаптеров провайдеров + 4 storage компонента
- **Обнаружено категорий дублирования**: 2
- **Потенциальное сокращение**: ~30 LOC (15%)
- **Уже покрыто существующими утилитами**: ~85%

---

## 1. Существующая инфраструктура (НЕ ДУБЛИРОВАТЬ)

### 1.1 Утилиты трансформации

| Утилита | Файл | LOC | Использование |
|---------|------|-----|---------------|
| `map_field_groups` | `field_specs.py:160-175` | 15 | 7/13 трансформеров |
| `FieldGroup` / `FieldSpec` | `field_specs.py:30-80` | 50 | 7/13 трансформеров |
| `flatten_nested_dict` | `transform_utils.py:31-72` | 41 | 3/13 трансформеров |
| `extract_list_field` | `transform_utils.py:75-120` | 45 | 1/13 трансформеров |
| `aggregate_nested_lists` | `transform_utils.py:134-179` | 45 | 1/13 трансформеров |
| `safe_int/float/str` | `domain/transformations.py:40-90` | 50 | Везде |

### 1.2 Базовые классы

| Класс | Файл | LOC | Назначение |
|-------|------|-----|------------|
| `BaseChemblTransformer` | `base_chembl_transformer.py` | 165 | Template Method для ChEMBL |
| `BaseHttpAdapter` | `adapters/base.py` | 273 | Health check, error handling |
| `BaseDeltaWriter` | `storage/base_delta_writer.py` | 282 | Общая логика Delta Lake |

---

## 2. Верифицированные дублирования

### 2.1 Паттерн: `flatten_nested_dict` + rename

#### Верификация
- **Файлы**: `molecule_transformer.py`, `assay_transformer.py`, `activity_transformer.py`
- **Строки**:
  - `molecule_transformer.py:68-84` (3 функции)
  - `assay_transformer.py:44-55` (1 функция)
  - `activity_transformer.py:135-163` (2 метода)
- **Существующие утилиты**: `flatten_nested_dict` покрывает базовый случай, НО не поддерживает rename
- **Дата верификации**: 2026-01-06
- **Проверка refactoring-plan.md**: Нет в ложных утверждениях ✅

#### Текущее состояние (дублирование)

```python
# molecule_transformer.py:68-72
def _extract_hierarchy(data: dict[str, Any] | None) -> dict[str, Any]:
    result = flatten_nested_dict(data, "hierarchy_", _HIERARCHY_FIELDS)
    result["hierarchy_child_chembl_id"] = result.pop("hierarchy_molecule_chembl_id")
    return result

# molecule_transformer.py:75-79
def _extract_properties(data: dict[str, Any] | None) -> dict[str, Any]:
    result = flatten_nested_dict(data, "property_", _PROPERTIES_FIELDS)
    result["property_ro5_violations"] = result.pop("property_num_ro5_violations")
    return result

# molecule_transformer.py:82-84
def _extract_structures(data: dict[str, Any] | None) -> dict[str, Any]:
    return flatten_nested_dict(data, "structure_", _STRUCTURES_FIELDS)

# assay_transformer.py:44-55
def _extract_variant(data: dict[str, Any] | None) -> dict[str, Any]:
    return flatten_nested_dict(data, "variant_", _VARIANT_FIELDS)

# activity_transformer.py:135-149
def _extract_ligand_efficiency(self, le_data) -> dict[str, Any]:
    return flatten_nested_dict(le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS)

# activity_transformer.py:151-163
def _extract_action_type(self, action_data) -> dict[str, Any]:
    return flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)
```

#### Анализ паттерна

| Функция | Файл | Использует rename? | Может использовать утилиту? |
|---------|------|-------------------|---------------------------|
| `_extract_hierarchy` | molecule | Да | ✅ С параметром `renames` |
| `_extract_properties` | molecule | Да | ✅ С параметром `renames` |
| `_extract_structures` | molecule | Нет | ✅ Уже использует |
| `_extract_variant` | assay | Нет | ✅ Уже использует |
| `_extract_ligand_efficiency` | activity | Нет | ✅ Уже использует |
| `_extract_action_type` | activity | Нет | ✅ Уже использует |

#### Предлагаемое решение

Добавить параметр `renames` в `flatten_nested_dict`:

```python
def flatten_nested_dict(
    data: dict[str, Any] | None,
    prefix: str,
    field_mapping: dict[str, Callable[[Any], Any] | None],
    renames: dict[str, str] | None = None,  # NEW
) -> dict[str, Any]:
    """Разворачивает вложенный словарь с опциональным переименованием.

    Args:
        data: Вложенный словарь.
        prefix: Префикс для ключей.
        field_mapping: {source_key: converter}.
        renames: {old_key: new_key} для переименования после flatten.
    """
    if not data or not isinstance(data, dict):
        keys = list(field_mapping.keys())
        result = {f"{prefix}{key}": None for key in keys}
        if renames:
            for old_key, new_key in renames.items():
                if old_key in result:
                    result[new_key] = result.pop(old_key)
        return result

    result: dict[str, Any] = {}
    for source_key, converter in field_mapping.items():
        value = data.get(source_key)
        if converter is not None and value is not None:
            result[f"{prefix}{source_key}"] = converter(value)
        else:
            result[f"{prefix}{source_key}"] = value

    if renames:
        for old_key, new_key in renames.items():
            if old_key in result:
                result[new_key] = result.pop(old_key)

    return result
```

#### Использование после рефакторинга

```python
# molecule_transformer.py — упрощение
_HIERARCHY_RENAMES = {
    "hierarchy_molecule_chembl_id": "hierarchy_child_chembl_id",
}

_PROPERTIES_RENAMES = {
    "property_num_ro5_violations": "property_ro5_violations",
}

# В _extract_business_data:
**flatten_nested_dict(
    rec.get("molecule_hierarchy"),
    "hierarchy_",
    _HIERARCHY_FIELDS,
    renames=_HIERARCHY_RENAMES,
),
```

#### Impact

- **LOC сокращение**: ~20 строк (6 функций → 2 параметризованных вызова)
- **Риск**: LOW (backward-compatible change, новый optional parameter)
- **Приоритет**: P1

---

### 2.2 Трансформеры без FieldGroup DSL

#### Верификация
- **Файлы**: `target_transformer.py`, `document_similarity_transformer.py`, `cell_line_transformer.py`, `compound_record_transformer.py`, `document_term_transformer.py`
- **Строки**: Полные файлы
- **Причина НЕ использования**:
  - `target_transformer.py` (166 LOC) — работает со списками компонентов, использует `extract_list_field`
  - `document_similarity_transformer.py` (94 LOC) — вычисляет derived поля (avg_tani, max_tani)
  - `cell_line_transformer.py` (73 LOC) — простой маппинг с domain normalization
  - `compound_record_transformer.py` (73 LOC) — простой маппинг с domain normalization
  - `document_term_transformer.py` (222 LOC) — 1:M relationship extraction (derived entity)

#### Анализ

| Transformer | LOC | Причина не использовать FieldGroup | Рекомендация |
|-------------|-----|-----------------------------------|--------------|
| `target_transformer` | 166 | List aggregation pattern | Оставить как есть |
| `document_similarity` | 94 | Derived calculations | Оставить как есть |
| `cell_line` | 73 | Domain normalization | Можно мигрировать (LOW) |
| `compound_record` | 73 | Domain normalization | Можно мигрировать (LOW) |
| `document_term` | 222 | 1:M extraction | Оставить как есть |

#### Вывод

Миграция на FieldGroup DSL для `cell_line_transformer` и `compound_record_transformer` возможна, но **не приоритетна** — выигрыш минимален (5-10 LOC), файлы уже маленькие и читаемые.

**Приоритет**: P3 (LOW)

---

## 3. Адаптеры — Анализ

### 3.1 Общие паттерны

| Паттерн | Реализация | Статус |
|---------|------------|--------|
| Health check template | `BaseHttpAdapter._probe_health()` | ✅ Уже реализовано |
| Error handling | `ErrorService` + `_error_handler` | ✅ Уже реализовано |
| Pagination | `PaginatedFetcherMixin` | ✅ Уже реализовано |
| Metrics | `AdapterMetrics` | ✅ Уже реализовано |

### 3.2 Анализ адаптеров

| Адаптер | LOC | Base Class | Специфика |
|---------|-----|------------|-----------|
| `ChemblAdapter` | 692 | `BaseHttpAdapter` | Entity mapper, health-aware batching |
| `UniProtAdapter` | 348 | `BaseHttpAdapter` + `PaginatedFetcherMixin` | FASTA parsing, cursor pagination |
| `PubChemAdapter` | 305 | `BaseSyncAdapter` | Sync wrapper for pubchempy |
| `PubMedAdapter` | 452 | `BaseHttpAdapter` | XML parsing, email requirement |
| `CrossRefAdapter` | 393 | `BaseHttpAdapter` | DOI-based fetching |
| `SemanticScholarAdapter` | 540 | `BaseHttpAdapter` | Paper metadata |
| `OpenAlexAdapter` | 580 | `BaseHttpAdapter` | Works metadata |

### 3.3 Вывод

Адаптеры **не показывают значительного дублирования**:
- Общая логика уже вынесена в базовые классы
- Каждый адаптер имеет уникальный контракт API
- Специфика провайдеров требует разной обработки

**Рекомендация**: Не требуется рефакторинг

---

## 4. Storage Writers — Анализ

### 4.1 Иерархия

```
BaseDeltaWriter (282 LOC)
    │
    ├── SilverWriter (701 LOC)
    │       └── Delta merge/upsert, content hash
    │
    └── GoldWriter (643 LOC)
            └── CSV export, SCD2, audit

BronzeWriter (603 LOC)
    └── JSONL + zstd, JSON validation
```

### 4.2 Анализ делегирования

| Writer | LOC | Делегирует в | Статус |
|--------|-----|--------------|--------|
| `BronzeWriter` | 603 | `atomic`, compression | ✅ Когезивен |
| `SilverWriter` | 701 | `BaseDeltaWriter`, policies | ✅ Когезивен |
| `GoldWriter` | 643 | `CsvExporter`, `AuditPort` | ✅ Когезивен |

### 4.3 Вывод

Storage writers **не требуют декомпозиции**:
- Каждый writer имеет свою специфику medallion layer
- Общая Delta logic уже в `BaseDeltaWriter`
- Режимы записи (MERGE/APPEND/SCD2) когезивны в пределах writer'а

**Рекомендация**: Не требуется рефакторинг (подтверждено в refactoring-plan.md)

---

## 5. Матрица приоритизации

| # | Категория | Impact | Complexity | LOC | Приоритет | Статус |
|---|-----------|--------|------------|-----|-----------|--------|
| 1 | `renames` param для `flatten_nested_dict` | MEDIUM | LOW | -20 | **P1** | 🟡 TODO |
| 2 | FieldGroup для cell_line/compound_record | LOW | LOW | -10 | P3 | ⚪ Optional |
| 3 | Адаптеры | - | - | 0 | - | ✅ Не требуется |
| 4 | Storage writers | - | - | 0 | - | ✅ Не требуется |

---

## 6. План рефакторинга

### Фаза 1 (P1): Добавить `renames` в `flatten_nested_dict`

**Файлы для изменения:**
1. `src/bioetl/application/core/transform_utils.py` — добавить параметр
2. `src/bioetl/application/pipelines/chembl/molecule_transformer.py` — использовать параметр
3. `tests/unit/application/core/test_transform_utils.py` — добавить тесты

**Критерии приёмки:**
- [ ] `flatten_nested_dict` принимает `renames: dict[str, str] | None = None`
- [ ] `molecule_transformer.py` использует `renames` вместо local functions
- [ ] Тесты проходят: `pytest tests/unit/application/core/test_transform_utils.py -v`
- [ ] Architecture tests: `pytest tests/architecture/ -v`

### Фаза 2 (P3): Optional — FieldGroup migration

**Не приоритетно** — файлы уже маленькие и читаемые.

---

## 7. Риски и митигации

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Поломка обратной совместимости | LOW | `renames` — optional parameter с default `None` |
| Пропуск тестов | LOW | Добавить unit-тесты для `renames` |
| Регрессия в трансформерах | LOW | Запустить полный тест-сьют |

---

## 8. Проверочные команды

```bash
# Перед рефакторингом
pytest tests/unit/application/core/test_transform_utils.py -v
pytest tests/unit/application/pipelines/chembl/ -v

# После рефакторинга
make lint
make test
pytest tests/architecture/ -v
```

---

*Документ подготовлен согласно протоколу двойной верификации (REQ-ARCH-040)*
