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
| 4 | effective-*-table properties | 3.1 | Не начато |
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
- `SilverFilterConfig(GoldFilterConfig)` в `src/bioetl/domain/filtering/silver-config.py:17`
- `isinstance(silver-cfg, GoldFilterConfig)` возвращает True — нарушение номинальной типизации
- Infrastructure УЖЕ подготовлена:
  - `filter-config.py` — `SilverFiltersFileConfig.to-domain()` возвращает `SilverFilterConfig`
  - `-base.py` — `-build-silver-filters()` вызывает `SilverFilterConfig.from-gold-filter-config()`
  - `filter-config-loader.py` — возвращает `SilverFilterConfig` в кортеже
- Новые тесты: `tests/unit/domain/filtering/test-silver-config.py` уже существует (87 строк)

ДИЗАЙН:
1. Создать `src/bioetl/domain/filtering/-base-filter-config.py`:
   - Перенести ВСЮ логику из GoldFilterConfig: `should-include()`, `-check-*`, `-OPERATOR-CHECKERS`, `is-empty()`
   - Класс: `BaseFilterConfig` — frozen dataclass с теми же полями
   - Добавить `from-base(cls, other: BaseFilterConfig) -> Self`

2. `src/bioetl/domain/filtering/gold-config.py`:
   - `GoldFilterConfig(BaseFilterConfig)` — только docstring

3. `src/bioetl/domain/filtering/silver-config.py`:
   - `SilverFilterConfig(BaseFilterConfig)` (НЕ GoldFilterConfig)
   - `from-gold-filter-config` → `from-base(other: BaseFilterConfig)`

4. `src/bioetl/domain/filtering/--init--.py` — реэкспорт BaseFilterConfig

5. Infrastructure:
   - `infrastructure/schemas/filter-config.py` — `SilverFilterConfig.from-base()` вместо `.from-gold-filter-config()`
   - `infrastructure/config/-base.py` — аналогично

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/filtering/ -v
- pytest tests/architecture/ -v
- isinstance(SilverFilterConfig(...), GoldFilterConfig) → False
- isinstance(GoldFilterConfig(...), SilverFilterConfig) → False

КРИТИЧНО: Ноль дублирования. Вся логика ТОЛЬКО в BaseFilterConfig.
```

---

## Промпт 2: Сужение write-mode типов (Шаг 1.3, опционально)

```
ЗАДАЧА: Убрать `| str` из объявлений write mode в TableConfig.

КОНТЕКСТ (main, 2c360d5):
- `table.py:31-32`:
    silver-write-mode: SilverWriteMode | str = SilverWriteMode.MERGE
    gold-write-mode: GoldWriteMode | str = GoldWriteMode.APPEND
- `--post-init--` конвертирует через `convert-write-mode()`
- `-base.py` УЖЕ конвертирует на границе: `SilverWriteMode.from-string()`

ШАГИ:
1. grep -rn "silver-write-mode\|gold-write-mode" src/bioetl/ --include="*.py"
   — убедиться что все вызовы проходят через --post-init-- или передают enum.
2. Изменить в table.py:
   silver-write-mode: SilverWriteMode = SilverWriteMode.MERGE
   gold-write-mode: GoldWriteMode = GoldWriteMode.APPEND
3. mypy --strict src/bioetl/
4. pytest tests/ -x --timeout=120
```

---

## Промпт 3: Source-конфиги — двойной формат (Шаг 2.3, опционально)

```
ЗАДАЧА: Добавить поддержку нового плоского формата source-конфигов.

КОНТЕКСТ:
- Файл: src/bioetl/composition/providers/-config-helpers.py
- Старый: source.provider-config.base-url
- Новый: api.base-url, client.timeout-sec, batch.api-batch-size

РЕАЛИЗАЦИЯ:
def -normalize-source-config(raw: dict) -> dict:
    if "api" in raw and "source" not in raw:
        raw["source"] = {
            "provider-config": {
                "base-url": raw["api"]["base-url"],
                "auth-type": raw["api"].get("auth-type", "public"),
                "client": raw.get("client", {}),
                ...
            },
            "batch-size": raw.get("batch", {}).get("api-batch-size", 100),
        }
        # Перенести rate-limit, circuit-breaker, health-check, retry, entities
        for key in ("rate-limit", "circuit-breaker", "health-check", "retry", "entities"):
            if key in raw:
                raw[key] = raw[key]
    return raw

ВЕРИФИКАЦИЯ:
- Существующие конфиги загружаются (старый формат)
- pytest tests/ -k "source-config or adapter" -v

ПРИМЕЧАНИЕ: Этот шаг ОПЦИОНАЛЕН. Можно вместо него мигрировать YAML + загрузчик атомарно.
```

---

## Промпт 4: Добавление effective-*-table (Шаг 3.1)

```
ЗАДАЧА: Добавить effective-silver-table и effective-gold-table в PipelineConfig.

ФАЙЛ: src/bioetl/domain/config/pipeline.py (после строки 145)

ДОБАВИТЬ:
@property
def effective-silver-table(self) -> str:
    """Имя Silver-таблицы с fallback на provider.entity."""
    return self.table.silver-table or f"{self.provider}.{self.entity-type}"

@property
def effective-gold-table(self) -> str:
    """Имя Gold-таблицы с fallback на provider.entity."""
    return self.table.gold-table or f"{self.provider}.{self.entity-type}"

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/config/ -v
```

---

## Промпт 5: Миграция вызовов (Шаг 3.2)

```
ЗАДАЧА: Заменить все использования convenience-свойств PipelineConfig
на config.table.* или config.effective-*.

ПРЕДУСЛОВИЕ: Промпт 4 выполнен.

ШАГИ:
1. Исчерпывающий поиск:
   grep -rn 'config\.primary-keys\b' src/bioetl/ --include="*.py" | grep -v 'table\.primary-keys' | grep -v '-test\.'
   grep -rn 'config\.silver-table\b' src/bioetl/ --include="*.py" | grep -v 'table\.silver-table' | grep -v 'effective-silver'
   grep -rn 'config\.gold-table\b' src/bioetl/ --include="*.py" | grep -v 'table\.gold-table' | grep -v 'effective-gold'
   grep -rn 'config\.write-mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.gold-write-mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.partition-cols\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.on-schema-mismatch\b' src/bioetl/ --include="*.py" | grep -v 'table\.'

2. Также: source-config.silver-table, source-config.primary-keys в composite-коде.

3. Маппинг:
   config.primary-keys → config.table.primary-keys
   config.silver-table → config.effective-silver-table (с fallback) или config.table.silver-table
   config.gold-table → config.effective-gold-table (с fallback) или config.table.gold-table
   config.write-mode → config.table.silver-write-mode
   config.gold-write-mode → config.table.gold-write-mode
   config.partition-cols → config.table.partition-cols
   config.on-schema-mismatch → config.table.on-schema-mismatch

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

УДАЛИТЬ: primary-keys, silver-table, gold-table, write-mode, gold-write-mode,
partition-cols, on-schema-mismatch

ОСТАВИТЬ: lock-key, effective-silver-table, effective-gold-table

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
   - document-similarity → publication-similarity
   - document-term → publication-term
3. НЕ менять комментарии, обсуждающие переименование.

ВЕРИФИКАЦИЯ:
- grep -rn "^\s*- document\b" configs/sources/ → 0 результатов
```

---

## Промпт 8: Упрощение pipeline YAML (Шаг 4.2)

```
ЗАДАЧА: Удалить дублированные поля из pipeline YAML, convention-based minimal стиль.

КОНТЕКСТ: config-loader.py (2c360d5) УЖЕ авто-вычисляет:
- source-file, dq-config-file, filter-config-file, column-groups-file
- sink.*.path (из provider + entity-type)
- sink.silver.primary-key (из primary-keys)
- sink.*.sort-by.columns (из primary-keys)

ДЛЯ КАЖДОГО configs/pipelines/{provider}/{entity}.yaml:

УДАЛИТЬ: source-file, dq-config-file, data-schema-file, filter-config-file,
sink.*.path, sink.silver.primary-key, sink.*.sort-by, sink.*.csv-export.path

ПЕРЕИМЕНОВАТЬ: dq-overrides → dq-overrides

ОСТАВИТЬ: pipeline-name, provider, entity-type, version, description,
primary-keys, silver-table, gold-table, sink.silver.partition-by,
write-mode (если не default), dq-overrides (содержимое)

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
- configs/quality/-defaults.yaml: common-field-validations → field-validations
- configs/quality/providers/*.yaml: provider-field-validations → field-validations
- configs/quality/entities/*/*.yaml: entity-field-validations → field-validations
Аналогично для cross-field-validations и conditional-validations.

ШАГИ:
1. find configs/quality/ -name "*.yaml" | wc -l
2. Применить переименования
3. grep -rn "common-field-validations\|provider-field-validations\|entity-field-validations" configs/quality/ → 0

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
4. configs/composite/field-groups/ → configs/schemas/composite/field-groups/
5. configs/pipelines/-schema.json → configs/-schema/pipeline.json
6. configs/pipelines/-composite-schema.json → configs/-schema/composite.json

ШАГИ:
1. mkdir -p configs/quality configs/filters configs/schemas configs/-schema
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
1. tests/architecture/test-filter-separation.py:
   - SilverFilterConfig НЕ подкласс GoldFilterConfig
   - Оба подклассы BaseFilterConfig
   - isinstance(Silver(...), Gold) → False

2. tests/unit/domain/config/test-effective-tables.py:
   - effective-silver-table с silver-table и без
   - effective-gold-table с gold-table и без

3. tests/unit/domain/filtering/test-base-filter-config.py:
   - Параметризованный: Gold и Silver проходят одинаковые should-include() тесты

ОЧИСТКА:
- Удалить fallback-код из dq-config-loader.py, filter-config-loader.py
- Удалить алиас dq-overrides из pipeline-config.py (оставить только dq-overrides)
- grep -rn "common-field-validations\|provider-field-validations" configs/ → 0
- grep -rn "configs/quality/" docs/ → 0

ДОКУМЕНТАЦИЯ:
- Обновить ADR-027, ADR-028, ADR-029 с новыми путями
- Создать docs/03-guides/CONFIG-GUIDE.md (из -base.yaml)

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
