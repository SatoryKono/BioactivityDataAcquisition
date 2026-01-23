# Отчёт аудита метаданных BioETL

**Дата:** 2026-01-19
**Аудитор:** Claude Code
**Версия RULES.md:** v5.10
**Ветка:** `claude/audit-bioetl-metadata-RmHcz`

---

## Резюме

| Метрика | Значение |
|---------|----------|
| Проверено схем | 21 |
| Проверено entity-классов | 15 |
| Критических проблем | 1 |
| Высокий приоритет | 1 |
| Средний приоритет | 1 |
| Низкий приоритет | 2 |
| Тестов метаданных | 65 (все проходят) |

---

## Критические проблемы

### [MDA-001] `_index` отсутствует в META_FIELDS

**Severity:** CRITICAL
**Файлы:**
- `src/bioetl/domain/transformations.py:29-36`
- `src/bioetl/domain/services/identity_service.py:25-34`

**Требование:** Audit prompt §Контекст (таблица "Обязательные метаполя")
**Текущее состояние:**

```python
# transformations.py:29-36
META_FIELDS = {
    "_ingestion_ts",
    "_run_id",
    "_run_type",
    "_dq_warn",
    "_dq_error",
    "_source_batch_id",
}
# _index ОТСУТСТВУЕТ!
```

**Влияние:**
1. `_index` включается в расчёт content hash
2. Одна и та же запись, обработанная в разных позициях батча, получит разные content_hash
3. Это приводит к ложным дубликатам в Silver layer при повторной обработке
4. Нарушает детерминизм и идемпотентность пайплайна

**Доказательство:**
- `column_order.py:33` определяет `_index` как системное поле в `SYSTEM_FIELDS_PREFIX`
- `base.py:63-67` (BaseEntity) определяет `_index` как обязательное поле с валидацией `>= 0`
- Тест `test_identity_service.py:134-144` проверяет META_FIELDS, но не включает `_index`

**Решение:**
```python
# Добавить в META_FIELDS в обоих файлах:
META_FIELDS = {
    "_ingestion_ts",
    "_run_id",
    "_run_type",
    "_dq_warn",
    "_dq_error",
    "_source_batch_id",
    "_index",  # <-- ДОБАВИТЬ
}
```

**Связанные тесты для обновления:**
- `tests/unit/domain/services/test_identity_service.py:134-144` - добавить `_index` в expected set

---

## Проблемы высокого приоритета

### [MDA-002] RULES.md §2.8.1 не документирует `_index` в META_FIELDS

**Severity:** HIGH
**Файл:** `docs/RULES.md:693`

**Текущее состояние:**
```
5. **Content Hash**: Исключать из расчёта хэша технические мета-поля:
   `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`.
   Реализация: `domain/transformations.py:META_FIELDS`.
```

**Проблема:**
- `_index` и `_source_batch_id` не упомянуты
- `_source_batch_id` уже в META_FIELDS (корректно)
- `_index` отсутствует в META_FIELDS (баг)
- Документация не синхронизирована с кодом

**Решение:**
Обновить RULES.md §2.8.1:
```
5. **Content Hash**: Исключать из расчёта хэша технические мета-поля:
   `_ingestion_ts`, `_run_id`, `_run_type`, `_source_batch_id`, `_index`, `_dq_*`.
   Реализация: `domain/transformations.py:META_FIELDS`.
```

---

## Проблемы среднего приоритета

### [MDA-003] `_dq_warn` и `_dq_error` не в BaseEntity

**Severity:** MEDIUM
**Файлы:**
- `src/bioetl/domain/entities/base.py` (не содержит DQ полей)
- `src/bioetl/domain/entities/chembl_structures.py:61-62` (определяет локально)
- `src/bioetl/domain/entities/publication_base.py:109-110` (определяет локально)

**Текущее состояние:**
- `BaseEntity` определяет: `entity_id`, `content_hash`, `run_id`, `run_type`, `ingestion_ts`, `_index`, `source_batch_id`
- `_dq_warn` и `_dq_error` определены только в некоторых entity-подклассах
- Трансформеры добавляют эти поля вручную в SilverRecord

**Влияние:**
- Несогласованность между entity-классами
- Дублирование кода добавления DQ полей в трансформерах
- Потенциальные ошибки при забытом добавлении полей

**Примеры ручного добавления:**
```python
# semanticscholar/transformer.py:201-202
"_dq_warn": False,
"_dq_error": False,

# crossref/transformer.py:163-164
"_dq_warn": False,
"_dq_error": False,
```

**Рекомендация:**
Рассмотреть добавление `_dq_warn` и `_dq_error` в BaseEntity с default=False, либо документировать текущий подход как осознанное решение.

---

## Проблемы низкого приоритета

### [MDA-004] ETLRecordSchema.index использует alias без underscore

**Severity:** LOW
**Файл:** `src/bioetl/domain/schemas/base.py:63-68`

**Текущее состояние:**
```python
index: Series[int] = pa.Field(
    alias="_index",  # alias с underscore
    nullable=False,
    ge=0,
    description="Sequential index of the record in the pipeline run.",
)
```

**Наблюдение:**
- Python атрибут называется `index`, alias в Pandera `_index`
- Это корректно и соответствует паттерну других полей (`run_id` → `_run_id`)
- Но может вызвать путаницу при чтении кода

**Статус:** INFO - не требует действий, соответствует общему паттерну.

### [MDA-005] Дублирование META_FIELDS в двух модулях

**Severity:** LOW
**Файлы:**
- `src/bioetl/domain/transformations.py:29-36`
- `src/bioetl/domain/services/identity_service.py:25-34`

**Наблюдение:**
Одинаковый набор полей определён в двух местах. Оба используются для разных целей:
- `transformations.py` - функциональный модуль для трансформаций
- `identity_service.py` - сервисный класс IdentityService

**Рекомендация:**
Рассмотреть вынос в общий модуль (`domain/constants.py`) и реэкспорт:
```python
# domain/constants.py
META_FIELDS: frozenset[str] = frozenset({...})

# transformations.py
from .constants import META_FIELDS

# identity_service.py
from bioetl.domain.constants import META_FIELDS
```

---

## Инвентаризация метаданных

### Обязательные поля по RULES.md §2.4

| Поле | Тип | Nullable | В ETLRecordSchema | В BaseEntity | В META_FIELDS | В Content Hash |
|------|-----|----------|-------------------|--------------|---------------|----------------|
| `entity_id` | str | No | ✅ | ✅ | ❌ | ✅ Да |
| `content_hash` | str | No | ✅ | ✅ | ❌ | — |
| `_run_id` | UUID | No | ✅ | ✅ | ✅ | ❌ Нет |
| `_run_type` | Enum | No | ✅ | ✅ | ✅ | ❌ Нет |
| `_source_batch_id` | UUID | Yes | ✅ | ✅ | ✅ | ❌ Нет |
| `_ingestion_ts` | Timestamp | No | ✅ | ✅ | ✅ | ❌ Нет |
| `_dq_warn` | bool | No | ✅ | ❌* | ✅ | ❌ Нет |
| `_dq_error` | bool | No | ✅ | ❌* | ✅ | ❌ Нет |
| `_index` | int | No | ✅ | ✅ | ⚠️ **НЕТ** | ⚠️ **ДА (баг)** |

\* `_dq_warn`/`_dq_error` определены в подклассах, не в BaseEntity

### Схемы наследующие ETLRecordSchema

Все 21 схема корректно наследуют от `ETLRecordSchema`:

| Провайдер | Схема | Наследование |
|-----------|-------|--------------|
| common | PublicationBaseSchema | ✅ |
| chembl | ActivitySchema | ✅ |
| chembl | AssaySchema | ✅ |
| chembl | AssayParametersSchema | ✅ |
| chembl | CellLineSchema | ✅ |
| chembl | CompoundRecordSchema | ✅ |
| chembl | DocumentSimilaritySchema | ✅ |
| chembl | DocumentTermSchema | ✅ |
| chembl | MoleculeSchema | ✅ |
| chembl | MoleculeFormSchema | ✅ |
| chembl | ProteinClassificationSchema | ✅ |
| chembl | PublicationSchema | ✅ |
| chembl | TargetSchema | ✅ |
| chembl | TargetComponentSchema | ✅ |
| chembl | TargetRelationSchema | ✅ |
| pubchem | PubchemMoleculeSchema | ✅ |
| uniprot | UniprotTargetSchema | ✅ |
| uniprot | IsoformSchema | ✅ |
| crossref | AuthorSchema, FunderSchema, ReferenceSchema, PublicationSchema | ✅ |
| openalex | PublicationSchema | ✅ |
| semanticscholar | PublicationSchema | ✅ |

---

## Валидация тестами

### Тесты META_FIELDS и content hash

| Тест | Файл | Статус |
|------|------|--------|
| test_meta_fields_excluded | test_transformations.py:70-82 | ✅ PASS |
| test_meta_field_excluded_from_hash (parametrized) | test_identity_service.py:111-132 | ✅ PASS |
| test_all_meta_fields_in_constant | test_identity_service.py:134-144 | ✅ PASS* |
| test_hash_deterministic | test_transformations.py:125-130 | ✅ PASS |
| test_nan_and_inf_to_null | test_transformations.py:43-47 | ✅ PASS |
| test_float_rounding | test_transformations.py:49-53 | ✅ PASS |

\* Тест проходит, но не включает `_index` в expected set - требует обновления после фикса MDA-001

### Покрытие

```bash
uv run pytest tests/unit/domain/test_transformations.py \
              tests/unit/domain/services/test_identity_service.py -v
# Result: 65 passed
```

---

## Рекомендации по исправлению

### Немедленные действия (Critical)

1. **[MDA-001]** Добавить `_index` в META_FIELDS:
   - `src/bioetl/domain/transformations.py:29-36`
   - `src/bioetl/domain/services/identity_service.py:25-34`

2. Обновить тест `test_all_meta_fields_in_constant`:
   - `tests/unit/domain/services/test_identity_service.py:136-143`

### Плановые действия (High/Medium)

3. **[MDA-002]** Обновить документацию RULES.md §2.8.1

4. **[MDA-003]** Создать ADR для решения о расположении DQ полей:
   - Вариант A: Добавить в BaseEntity
   - Вариант B: Документировать текущий подход

### Рекомендации (Low)

5. **[MDA-005]** Рассмотреть консолидацию META_FIELDS в один модуль

---

## Связанные документы

- RULES.md §2.4 — Политика Backfill/Replay (метаполя)
- RULES.md §2.8 — Генерация Entity ID / Content Hash
- ADR-014 — Deterministic Writes
- `src/bioetl/domain/schemas/column_order.py` — Каноническое упорядочение колонок

---

## Чеклист перед закрытием аудита

- [x] Все CRITICAL/HIGH находки задокументированы
- [ ] Создан Issue для MDA-001 (требует действий)
- [x] Inventory таблица составлена
- [x] Тесты метаполей проходят (65 passed)
- [ ] RULES.md и код требуют синхронизации
- [x] Отчёт аудита завершён

---

*Отчёт создан в рамках аудита метаданных BioETL согласно audit prompt v1.0*
