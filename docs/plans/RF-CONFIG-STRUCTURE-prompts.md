# RF-CONFIG-STRUCTURE: Промпты для выполнения (v3)

**Сопутствующий документ:** `RF-CONFIG-STRUCTURE-consolidated.md` v3.0.0
**Дата:** 2026-02-15 | **Синхронизировано с main (коммит `2c360d5`)**

Промпты ниже содержат ТОЛЬКО оставшиеся задачи.
Выполненные шаги (1.1, 2.1, 2.2, 2.4, 2.5, 2.6) удалены.

---

## Оставшиеся промпты: 11 (было 16)

| # | Промпт | Фаза | Статус |
|---|--------|------|--------|
| 1 | BaseFilterConfig extraction | 1.2 | Не начато |
| 2 | Write mode type narrowing | 1.3 | Частично (опц.) |
| 3 | Source config dual format | 2.3 | Не начато (опц.) |
| 4 | effective_*_table properties | 3.1 | Не начато |
| 5 | Миграция вызовов | 3.2 | Не начато |
| 6 | Удаление convenience-свойств | 3.3 | Не начато |
| 7 | Исправление entity names | 4.1 | Не начато |
| 8 | Упрощение pipeline YAML | 4.2 | Не начато |
| 9 | Унификация DQ ключей YAML | 4.3 | Не начато |
| 10 | Переименование каталогов | 5.1 | Не начато |
| 11 | Архитектурные тесты | 6 | Частично |

---

## Промпт 1: Выделение BaseFilterConfig (Шаг 1.2)

```
ЗАДАЧА: Рефакторинг domain-фильтрации — создать общий базовый класс BaseFilterConfig
вместо наследования SilverFilterConfig от GoldFilterConfig.

КОНТЕКСТ (верифицировано на main, коммит 2c360d5):
- `SilverFilterConfig(GoldFilterConfig)` в `src/bioetl/domain/filtering/silver_config.py:17`
- `isinstance(silver_cfg, GoldFilterConfig)` возвращает True — нарушение номинальной типизации
- Infrastructure УЖЕ подготовлена:
  - `filter_config.py` — `SilverFiltersFileConfig.to_domain()` возвращает `SilverFilterConfig`
  - `_base.py` — `_build_silver_filters()` вызывает `SilverFilterConfig.from_gold_filter_config()`
  - `filter_config_loader.py` — возвращает `SilverFilterConfig` в кортеже
- Новые тесты: `tests/unit/domain/filtering/test_silver_config.py` уже существует (87 строк)

ДИЗАЙН:
1. Создать `src/bioetl/domain/filtering/_base_filter_config.py`:
   - Перенести ВСЮ логику из GoldFilterConfig: `should_include()`, `_check_*`, `_OPERATOR_CHECKERS`, `is_empty()`
   - Класс: `BaseFilterConfig` — frozen dataclass с теми же полями
   - Добавить `from_base(cls, other: BaseFilterConfig) -> Self`

2. `src/bioetl/domain/filtering/gold_config.py`:
   - `GoldFilterConfig(BaseFilterConfig)` — только docstring

3. `src/bioetl/domain/filtering/silver_config.py`:
   - `SilverFilterConfig(BaseFilterConfig)` (НЕ GoldFilterConfig)
   - `from_gold_filter_config` → `from_base(other: BaseFilterConfig)`

4. `src/bioetl/domain/filtering/__init__.py` — реэкспорт BaseFilterConfig

5. Infrastructure:
   - `infrastructure/schemas/filter_config.py` — `SilverFilterConfig.from_base()` вместо `.from_gold_filter_config()`
   - `infrastructure/config/_base.py` — аналогично

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/filtering/ -v
- pytest tests/architecture/ -v
- isinstance(SilverFilterConfig(...), GoldFilterConfig) → False
- isinstance(GoldFilterConfig(...), SilverFilterConfig) → False

КРИТИЧНО: Ноль дублирования. Вся логика ТОЛЬКО в BaseFilterConfig.
```

---

## Промпт 2: Сужение write_mode типов (Шаг 1.3, опционально)

```
ЗАДАЧА: Убрать `| str` из объявлений write mode в TableConfig.

КОНТЕКСТ (main, 2c360d5):
- `table.py:31-32`:
    silver_write_mode: SilverWriteMode | str = SilverWriteMode.MERGE
    gold_write_mode: GoldWriteMode | str = GoldWriteMode.APPEND
- `__post_init__` конвертирует через `convert_write_mode()`
- `_base.py` УЖЕ конвертирует на границе: `SilverWriteMode.from_string()`

ШАГИ:
1. grep -rn "silver_write_mode\|gold_write_mode" src/bioetl/ --include="*.py"
   — убедиться что все вызовы проходят через __post_init__ или передают enum.
2. Изменить в table.py:
   silver_write_mode: SilverWriteMode = SilverWriteMode.MERGE
   gold_write_mode: GoldWriteMode = GoldWriteMode.APPEND
3. mypy --strict src/bioetl/
4. pytest tests/ -x --timeout=120
```

---

## Промпт 3: Source-конфиги — двойной формат (Шаг 2.3, опционально)

```
ЗАДАЧА: Добавить поддержку нового плоского формата source-конфигов.

КОНТЕКСТ:
- Файл: src/bioetl/composition/providers/_config_helpers.py
- Старый: source.provider_config.base_url
- Новый: api.base_url, client.timeout_sec, batch.api_batch_size

РЕАЛИЗАЦИЯ:
def _normalize_source_config(raw: dict) -> dict:
    if "api" in raw and "source" not in raw:
        raw["source"] = {
            "provider_config": {
                "base_url": raw["api"]["base_url"],
                "auth_type": raw["api"].get("auth_type", "public"),
                "client": raw.get("client", {}),
                ...
            },
            "batch_size": raw.get("batch", {}).get("api_batch_size", 100),
        }
        # Перенести rate_limit, circuit_breaker, health_check, retry, entities
        for key in ("rate_limit", "circuit_breaker", "health_check", "retry", "entities"):
            if key in raw:
                raw[key] = raw[key]
    return raw

ВЕРИФИКАЦИЯ:
- Существующие конфиги загружаются (старый формат)
- pytest tests/ -k "source_config or adapter" -v

ПРИМЕЧАНИЕ: Этот шаг ОПЦИОНАЛЕН. Можно вместо него мигрировать YAML + загрузчик атомарно.
```

---

## Промпт 4: Добавление effective_*_table (Шаг 3.1)

```
ЗАДАЧА: Добавить effective_silver_table и effective_gold_table в PipelineConfig.

ФАЙЛ: src/bioetl/domain/config/pipeline.py (после строки 145)

ДОБАВИТЬ:
@property
def effective_silver_table(self) -> str:
    """Имя Silver-таблицы с fallback на provider.entity."""
    return self.table.silver_table or f"{self.provider}.{self.entity_type}"

@property
def effective_gold_table(self) -> str:
    """Имя Gold-таблицы с fallback на provider.entity."""
    return self.table.gold_table or f"{self.provider}.{self.entity_type}"

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/config/ -v
```

---

## Промпт 5: Миграция вызовов (Шаг 3.2)

```
ЗАДАЧА: Заменить все использования convenience-свойств PipelineConfig
на config.table.* или config.effective_*.

ПРЕДУСЛОВИЕ: Промпт 4 выполнен.

ШАГИ:
1. Исчерпывающий поиск:
   grep -rn 'config\.primary_keys\b' src/bioetl/ --include="*.py" | grep -v 'table\.primary_keys' | grep -v '_test\.'
   grep -rn 'config\.silver_table\b' src/bioetl/ --include="*.py" | grep -v 'table\.silver_table' | grep -v 'effective_silver'
   grep -rn 'config\.gold_table\b' src/bioetl/ --include="*.py" | grep -v 'table\.gold_table' | grep -v 'effective_gold'
   grep -rn 'config\.write_mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.gold_write_mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.partition_cols\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.on_schema_mismatch\b' src/bioetl/ --include="*.py" | grep -v 'table\.'

2. Также: source_config.silver_table, source_config.primary_keys в composite-коде.

3. Маппинг:
   config.primary_keys → config.table.primary_keys
   config.silver_table → config.effective_silver_table (с fallback) или config.table.silver_table
   config.gold_table → config.effective_gold_table (с fallback) или config.table.gold_table
   config.write_mode → config.table.silver_write_mode
   config.gold_write_mode → config.table.gold_write_mode
   config.partition_cols → config.table.partition_cols
   config.on_schema_mismatch → config.table.on_schema_mismatch

4. Обновить тесты.

ВЕРИФИКАЦИЯ:
- grep из шага 1 возвращают 0 результатов (кроме определений свойств)
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
```

---

## Промпт 6: Удаление convenience-свойств (Шаг 3.3)

```
ЗАДАЧА: Удалить 7 convenience-свойств из PipelineConfig.

ПРЕДУСЛОВИЕ: Промпт 5 ПОЛНОСТЬЮ выполнен.

ФАЙЛ: src/bioetl/domain/config/pipeline.py (строки ~112-145)

УДАЛИТЬ: primary_keys, silver_table, gold_table, write_mode, gold_write_mode,
partition_cols, on_schema_mismatch

ОСТАВИТЬ: lock_key, effective_silver_table, effective_gold_table

ШАГИ:
1. Финальный grep — убедиться что вызовов не осталось
2. Удалить свойства
3. Обновить docstring класса
4. Удалить неиспользуемые импорты

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
```

---

## Промпт 7: Исправление entity names (Шаг 4.1)

```
ЗАДАЧА: document → publication в configs/sources/*.yaml

ШАГИ:
1. grep -rn "document" configs/sources/
2. Заменить:
   - document → publication
   - document_similarity → publication_similarity
   - document_term → publication_term
3. НЕ менять комментарии, обсуждающие переименование.

ВЕРИФИКАЦИЯ:
- grep -rn "^\s*- document\b" configs/sources/ → 0 результатов
```

---

## Промпт 8: Упрощение pipeline YAML (Шаг 4.2)

```
ЗАДАЧА: Удалить дублированные поля из pipeline YAML, convention-based minimal стиль.

КОНТЕКСТ: config_loader.py (2c360d5) УЖЕ авто-вычисляет:
- source_file, dq_config_file, filter_config_file, column_groups_file
- sink.*.path (из provider + entity_type)
- sink.silver.primary_key (из primary_keys)
- sink.*.sort_by.columns (из primary_keys)

ДЛЯ КАЖДОГО configs/pipelines/{provider}/{entity}.yaml:

УДАЛИТЬ: source_file, dq_config_file, data_schema_file, filter_config_file,
sink.*.path, sink.silver.primary_key, sink.*.sort_by, sink.*.csv_export.path

ПЕРЕИМЕНОВАТЬ: dq_overrides → dq_overrides

ОСТАВИТЬ: pipeline_name, provider, entity_type, version, description,
primary_keys, silver_table, gold_table, sink.silver.partition_by,
write_mode (если не default), dq_overrides (содержимое)

ПОРЯДОК: chembl/molecule.yaml (117 строк) → все остальные. Пропустить composite/.

ВЕРИФИКАЦИЯ:
- pytest tests/ -k "config" -v
```

---

## Промпт 9: Унификация DQ ключей в YAML (Шаг 4.3)

```
ЗАДАЧА: Переименовать DQ ключи на unified naming во всех YAML.

КОНТЕКСТ: Загрузчик (2c360d5) уже поддерживает оба формата через нормализацию.

ПЕРЕИМЕНОВАНИЯ:
- configs/quality/_defaults.yaml: common_field_validations → field_validations
- configs/quality/providers/*.yaml: provider_field_validations → field_validations
- configs/quality/entities/*/*.yaml: entity_field_validations → field_validations
Аналогично для cross_field_validations и conditional_validations.

ШАГИ:
1. find configs/quality/ -name "*.yaml" | wc -l
2. Применить переименования
3. grep -rn "common_field_validations\|provider_field_validations\|entity_field_validations" configs/quality/ → 0

ВЕРИФИКАЦИЯ:
- pytest tests/ -k "dq" -v
```

---

## Промпт 10: Переименование каталогов (Шаг 5.1)

```
ЗАДАЧА: Переименовать каталоги конфигов.

ПРЕДУСЛОВИЕ: Промпты 7-9 (YAML миграция) выполнены.
Загрузчики УЖЕ поддерживают новые пути (fallback из PR #2122).

ПЕРЕИМЕНОВАНИЯ:
1. configs/quality/ → configs/quality/
2. configs/filters/ → configs/filters/
3. configs/schemas/ → configs/schemas/
4. configs/composite/field_groups/ → configs/schemas/composite/field_groups/
5. configs/pipelines/_schema.json → configs/_schema/pipeline.json
6. configs/pipelines/_composite_schema.json → configs/_schema/composite.json

ШАГИ:
1. mkdir -p configs/quality configs/filters configs/schemas configs/_schema
2. cp -r (скопировать содержимое)
3. pytest tests/ -x --timeout=120
4. Если ОК — rm -rf старых каталогов

ВЕРИФИКАЦИЯ:
- find configs/ -name "*.yaml" | wc -l — то же количество
- pytest tests/ -x --timeout=120
```

---

## Промпт 11: Архитектурные тесты и финализация (Фаза 6)

```
ЗАДАЧА: Добавить тесты рефакторинга и удалить fallback-код.

ПРЕДУСЛОВИЯ: Все промпты 1-10 выполнены.

НОВЫЕ ТЕСТЫ:
1. tests/architecture/test_filter_separation.py:
   - SilverFilterConfig НЕ подкласс GoldFilterConfig
   - Оба подклассы BaseFilterConfig
   - isinstance(Silver(...), Gold) → False

2. tests/unit/domain/config/test_effective_tables.py:
   - effective_silver_table с silver_table и без
   - effective_gold_table с gold_table и без

3. tests/unit/domain/filtering/test_base_filter_config.py:
   - Параметризованный: Gold и Silver проходят одинаковые should_include() тесты

ОЧИСТКА:
- Удалить fallback-код из dq_config_loader.py, filter_config_loader.py
- Удалить алиас dq_overrides из pipeline_config.py (оставить только dq_overrides)
- grep -rn "common_field_validations\|provider_field_validations" configs/ → 0
- grep -rn "configs/quality/" docs/ → 0

ДОКУМЕНТАЦИЯ:
- Обновить ADR-027, ADR-028, ADR-029 с новыми путями
- Создать docs/03-guides/CONFIG-GUIDE.md (из _base.yaml)

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
- pytest --cov=src/bioetl --cov-fail-under=85
```

---

## Заметки по выполнению

### Параллелизация
- **Промпты 1, 2, 3:** Независимы, можно параллельно
- **Промпты 4 → 5 → 6:** Строго последовательно
- **Промпты 7, 8, 9:** Независимы, можно параллельно (все YAML)
- **Промпт 10:** Зависит от 7-9
- **Промпт 11:** Зависит от всех

### Частота верификации
После КАЖДОГО промпта:
1. `mypy --strict src/bioetl/`
2. `pytest tests/architecture/ -v`
3. `pytest tests/ -x --timeout=120`
