# RF-CONFIG-STRUCTURE: Промпты для выполнения

**Сопутствующий документ:** `RF-CONFIG-STRUCTURE-consolidated.md` v2.0.0
**Дата:** 2026-02-13

Каждый промпт ниже — самодостаточная инструкция для AI-агента.
Выполнять в порядке Фаза 1 → 6. Внутри фазы шаги можно
параллелизировать там, где это отмечено.

---

## Фаза 1: Исправления типов на уровне кода

### Промпт 1.1: Сужение типа `silver_filters`

```
ЗАДАЧА: Сузить тип поля `silver_filters` с `SilverFilterConfig | GoldFilterConfig | None`
до `SilverFilterConfig | None` по всей кодовой базе.

КОНТЕКСТ:
- `PipelineConfig.silver_filters` в `src/bioetl/domain/config/pipeline.py:49` имеет тип
  `SilverFilterConfig | GoldFilterConfig | None`. `| GoldFilterConfig` — утечка типа:
  Silver-фильтры всегда должны быть типизированы как `SilverFilterConfig`.
- Весь infrastructure-код уже оборачивает Gold-конфиги через `SilverFilterConfig.from_gold_filter_config()`.

ФАЙЛЫ ДЛЯ МОДИФИКАЦИИ (верифицировать каждый через grep):
1. src/bioetl/domain/config/pipeline.py — объявление поля (строка 49) и TYPE_CHECKING импорт (строка 19)
2. src/bioetl/application/core/base_transformer.py — сигнатура конструктора, принимающего silver_filters
3. src/bioetl/application/pipelines/*/transformer.py — все ~10 файлов трансформеров
4. src/bioetl/composition/factories/pipeline_factory.py — где конструируется PipelineConfig
5. src/bioetl/composition/factories/transformer_factory.py — где трансформеры получают фильтры

ШАГИ:
1. Запустить: grep -rn "GoldFilterConfig" src/bioetl/ --include="*.py" | grep -i silver
   чтобы найти все места, где GoldFilterConfig фигурирует в silver-контексте.
2. В каждом файле заменить `SilverFilterConfig | GoldFilterConfig | None` на `SilverFilterConfig | None`.
3. Удалить неиспользуемые импорты GoldFilterConfig, где они использовались только для типа silver_filters.
4. Запустить: mypy --strict src/bioetl/
5. Запустить: pytest tests/architecture/ -v
6. Запустить: pytest tests/unit/ -x --timeout=60

НЕ менять никакое runtime-поведение. Это изменение только аннотаций типов.
```

### Промпт 1.2: Выделение BaseFilterConfig и разрыв наследования SilverFilterConfig

```
ЗАДАЧА: Рефакторинг domain-фильтрации для использования общего базового класса BaseFilterConfig
вместо наследования SilverFilterConfig от GoldFilterConfig.

КОНТЕКСТ:
- Сейчас `SilverFilterConfig(GoldFilterConfig)` в `src/bioetl/domain/filtering/silver_config.py:17`
- Это означает, что `isinstance(silver_cfg, GoldFilterConfig)` возвращает True — ПЛОХО для номинальной типизации.
- Цель: И GoldFilterConfig, и SilverFilterConfig наследуют от приватного BaseFilterConfig.
  Ни один не является подклассом другого.

ДИЗАЙН:
1. Создать `src/bioetl/domain/filtering/_base_filter_config.py`:
   - Перенести ВСЮ логику из GoldFilterConfig сюда: `should_include()`, все `_check_*` методы,
     dispatch-таблицу `_OPERATOR_CHECKERS`, `is_empty()`.
   - Имя класса: `BaseFilterConfig`
   - Тот же frozen dataclass с теми же полями.
   - Добавить classmethod `from_base(cls, other: BaseFilterConfig) -> Self` для кросс-типовой конвертации.

2. Модифицировать `src/bioetl/domain/filtering/gold_config.py`:
   - Изменить `GoldFilterConfig` на наследование от `BaseFilterConfig` вместо собственного определения.
   - Сохранить docstring, объясняющий назначение Gold-слоя.
   - Тело класса должно быть минимальным (только docstring или `pass`).

3. Модифицировать `src/bioetl/domain/filtering/silver_config.py`:
   - Изменить `SilverFilterConfig` на наследование от `BaseFilterConfig` (НЕ GoldFilterConfig).
   - Заменить `from_gold_filter_config(config: GoldFilterConfig)` на `from_base(other: BaseFilterConfig)`.
   - Обновить docstring.

4. Модифицировать `src/bioetl/domain/filtering/__init__.py`:
   - Экспортировать `BaseFilterConfig` (но документировать как внутренний — потребители должны использовать Gold/Silver).

5. Обновить infrastructure:
   - `src/bioetl/infrastructure/schemas/filter_config.py` — если есть `to_silver_domain()`,
     обновить вызов фабрики с `SilverFilterConfig.from_gold_filter_config()` на `SilverFilterConfig.from_base()`.
   - `src/bioetl/infrastructure/config/_base.py` — аналогичное обновление.
   - `src/bioetl/infrastructure/config/filter_config_loader.py` — обновить возвращаемый тип при необходимости.

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/ -v
- pytest tests/architecture/ -v
- Подтвердить: `isinstance(SilverFilterConfig(...), GoldFilterConfig)` — False
- Подтвердить: `isinstance(GoldFilterConfig(...), SilverFilterConfig)` — False
- Подтвердить: оба `should_include()` работают идентично (одна и та же базовая логика)

КРИТИЧЕСКИ ВАЖНО: Ноль дублирования кода. Вся логика фильтрации живёт только в BaseFilterConfig.
```

### Промпт 1.3: Сужение типов write mode в TableConfig (опционально)

```
ЗАДАЧА: Убрать `| str` из объявлений полей write mode в TableConfig.

КОНТЕКСТ:
- `src/bioetl/domain/config/table.py:31-32` объявляет:
    silver_write_mode: SilverWriteMode | str = SilverWriteMode.MERGE
    gold_write_mode: GoldWriteMode | str = GoldWriteMode.APPEND
- `__post_init__` (строки 37-50) всегда конвертирует строки в enum через `convert_write_mode()`.
- В runtime значение всегда enum, но mypy видит `SilverWriteMode | str`.

ШАГИ:
1. Сначала верифицировать, что ВСЕ точки конструирования передают enum-значения или проходят через __post_init__:
   grep -rn "silver_write_mode\|gold_write_mode" src/bioetl/ --include="*.py"
   grep -rn "SilverWriteMode\|GoldWriteMode" src/bioetl/ --include="*.py"

2. Если безопасно, изменить объявления в table.py:
   silver_write_mode: SilverWriteMode = SilverWriteMode.MERGE
   gold_write_mode: GoldWriteMode = GoldWriteMode.APPEND

3. Перенести конвертацию string→enum на границу infrastructure:
   - src/bioetl/infrastructure/config/_base.py (yaml_config_to_domain или эквивалент)
   - Убедиться, что строки из YAML конвертируются ДО конструирования TableConfig.

4. Обновить тип возврата PipelineConfig.write_mode (если ещё существует):
   SilverWriteMode | str → SilverWriteMode

5. Убрать `| str` из type hints всех вызывающих модулей.

6. Запустить: mypy --strict src/bioetl/
7. Запустить: pytest tests/ -x --timeout=120

ПРОПУСТИТЬ этот промпт, если grep в шаге 1 выявит вызовы, передающие сырые строки
без прохождения через __post_init__. В этом случае сначала исправить эти вызовы.
```

---

## Фаза 2: Улучшение загрузчиков в infrastructure

### Промпт 2.1: Загрузчик DQ конфигов — унифицированные имена полей с поддержкой алиасов

```
ЗАДАЧА: Добавить поддержку алиасов в DQConfigLoader, чтобы унифицированный ключ `field_validations`
работал на ВСЕХ уровнях иерархии наряду с существующими уровне-специфичными ключами.

КОНТЕКСТ:
- Файл: src/bioetl/infrastructure/config/dq_config_loader.py
- Сейчас загрузчик ожидает:
  - _defaults.yaml: `common_field_validations`, `common_cross_field_validations`, `common_conditional_validations`
  - providers/*.yaml: `provider_field_validations` и т.д.
  - entities/*/*.yaml: `entity_field_validations` и т.д.
- Мы хотим ТАКЖЕ принимать универсальный ключ `field_validations` на любом уровне,
  автоматически трактуя его как уровне-специфичный ключ.

РЕАЛИЗАЦИЯ:
1. Прочитать текущую логику нормализации (вероятно в методе `_normalize_*`).
2. Добавить шаг нормализации, выполняемый ДО существующего слияния:
   ```python
   def _normalize_level_keys(self, data: dict, level: str) -> dict:
       """Маппинг универсального 'field_validations' на уровне-специфичный ключ, если он ещё не задан."""
       prefix_map = {"defaults": "common", "provider": "provider", "entity": "entity"}
       prefix = prefix_map[level]
       for suffix in ("field_validations", "cross_field_validations", "conditional_validations"):
           universal_key = suffix
           level_key = f"{prefix}_{suffix}"
           if universal_key in data and level_key not in data:
               data[level_key] = data.pop(universal_key)
       return data
   ```
3. Вызывать эту нормализацию после загрузки каждого YAML-файла, перед слиянием.
4. Добавить `dq_overrides` как алиас для `dq_rules` в загрузке pipeline-конфигов
   (в pipeline_config_loader.py).

ВЕРИФИКАЦИЯ:
- Существующие тесты проходят без изменений (старый формат работает).
- Написать маленький тест: YAML с `field_validations` на уровне entity → тот же доменный объект,
  что и YAML с `entity_field_validations`.
- pytest tests/unit/infrastructure/config/ -v
```

### Промпт 2.2: Source-конфиги — поддержка двух форматов

```
ЗАДАЧА: Обновить загрузку source-конфигов для приёма как старого вложенного формата, так и нового плоского.

КОНТЕКСТ:
- Файл: src/bioetl/composition/providers/_config_helpers.py
- Старый формат: `source.provider_config.base_url`, `source.batch_size` и т.д.
- Новый формат: `api.base_url`, `client.timeout_sec`, `batch.api_batch_size` и т.д.

РЕАЛИЗАЦИЯ:
1. Прочитать _config_helpers.py для понимания текущего парсинга.
2. Добавить нормализацию, конвертирующую новый формат в старый внутри:
   ```python
   def _normalize_source_config(raw: dict) -> dict:
       """Принять как старый (source.provider_config), так и новый (api/client/batch) форматы."""
       if "api" in raw and "source" not in raw:
           # Новый формат → конвертация в старый для совместимости
           raw["source"] = {
               "provider_config": {
                   "base_url": raw["api"]["base_url"],
                   "auth_type": raw["api"].get("auth_type", "public"),
                   ...
               },
               "batch_size": raw.get("batch", {}).get("api_batch_size", 100),
               ...
           }
       return raw
   ```
3. Применить эту нормализацию в `_get_source_config()` или в месте загрузки YAML.

ВЕРИФИКАЦИЯ:
- Существующие source-конфиги загружаются корректно (старый формат).
- Вручную протестировать с одним сконвертированным source-конфигом (новый формат).
- pytest tests/ -k "source_config or adapter" -v
```

### Промпт 2.3: Загрузчик конфигов фильтров — алиас пути

```
ЗАДАЧА: Обновить FilterConfigLoader для поиска как в `configs/filter/`, так и в `configs/filters/`.

КОНТЕКСТ:
- Файл: src/bioetl/infrastructure/config/filter_config_loader.py
- Сейчас: жёстко задан путь `configs/filter/`.
- Цель: Сначала пробовать `configs/filters/`, fallback на `configs/filter/`.

РЕАЛИЗАЦИЯ:
1. Найти, где задаётся корневой путь конфигов фильтров (вероятно в __init__ или атрибуте класса).
2. Добавить fallback-логику:
   ```python
   filter_root = self._configs_root / "filters"
   if not filter_root.exists():
       filter_root = self._configs_root / "filter"
   ```
3. Тот же паттерн для DQ: пробовать `configs/quality/`, затем `configs/dq/`.
4. То же для data_schema: пробовать `configs/schemas/`, затем `configs/data_schema/`.

ВЕРИФИКАЦИЯ:
- Существующие пути работают (переименование каталогов ещё не выполнено).
- pytest tests/unit/infrastructure/config/ -v
```

---

## Фаза 3: Миграция вызовов и удаление свойств

### Промпт 3.1: Добавление effective_silver_table / effective_gold_table

```
ЗАДАЧА: Добавить свойства `effective_silver_table` и `effective_gold_table` в PipelineConfig.

КОНТЕКСТ:
- Файл: src/bioetl/domain/config/pipeline.py
- Множество вызывающих модулей используют паттерн `config.silver_table or f"{config.provider}.{config.entity_type}"`.
- Централизовать эту fallback-логику.

РЕАЛИЗАЦИЯ:
Добавить после секции существующих convenience-свойств:

```python
@property
def effective_silver_table(self) -> str:
    """Имя Silver-таблицы с fallback на provider.entity."""
    return self.table.silver_table or f"{self.provider}.{self.entity_type}"

@property
def effective_gold_table(self) -> str:
    """Имя Gold-таблицы с fallback на provider.entity."""
    return self.table.gold_table or f"{self.provider}.{self.entity_type}"
```

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/unit/domain/config/ -v
```

### Промпт 3.2: Миграция всех вызовов с convenience-свойств на config.table.*

```
ЗАДАЧА: Заменить все использования convenience-свойств PipelineConfig на каноничный
доступ через config.table.* или новые effective_*-свойства.

КОНТЕКСТ:
- PipelineConfig имеет 7 convenience-свойств, проксирующих к config.table.*:
  primary_keys, silver_table, gold_table, write_mode, gold_write_mode, partition_cols, on_schema_mismatch
- Они будут удалены. Все вызывающие модули должны использовать config.table.* напрямую.
- Для silver_table/gold_table с fallback-паттерном использовать config.effective_silver_table/effective_gold_table.

ШАГИ:
1. Выполнить исчерпывающий поиск:
   grep -rn 'config\.primary_keys\b' src/bioetl/ --include="*.py" | grep -v 'table\.primary_keys' | grep -v '_test\.'
   grep -rn 'config\.silver_table\b' src/bioetl/ --include="*.py" | grep -v 'table\.silver_table' | grep -v 'effective_silver'
   grep -rn 'config\.gold_table\b' src/bioetl/ --include="*.py" | grep -v 'table\.gold_table' | grep -v 'effective_gold'
   grep -rn 'config\.write_mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.gold_write_mode\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.partition_cols\b' src/bioetl/ --include="*.py" | grep -v 'table\.'
   grep -rn 'config\.on_schema_mismatch\b' src/bioetl/ --include="*.py" | grep -v 'table\.'

2. Также проверить `source_config.silver_table`, `source_config.primary_keys` и т.д. в composite-коде.

3. Для каждого совпадения применить миграцию:
   - config.primary_keys → config.table.primary_keys
   - config.silver_table → config.effective_silver_table (если есть fallback-паттерн) или config.table.silver_table
   - config.gold_table → config.effective_gold_table (если есть fallback-паттерн) или config.table.gold_table
   - config.write_mode → config.table.silver_write_mode
   - config.gold_write_mode → config.table.gold_write_mode
   - config.partition_cols → config.table.partition_cols
   - config.on_schema_mismatch → config.table.on_schema_mismatch

4. КРИТИЧЕСКИ ВАЖНО: Также обновить тестовые файлы, ссылающиеся на эти свойства.

ВЕРИФИКАЦИЯ:
- Все grep-команды из шага 1 возвращают 0 результатов (кроме определений самих свойств).
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
```

### Промпт 3.3: Удаление convenience-свойств из PipelineConfig

```
ЗАДАЧА: Удалить 7 convenience-свойств из PipelineConfig.

ПРЕДУСЛОВИЕ: Промпт 3.2 ПОЛНОСТЬЮ ВЫПОЛНЕН и верифицирован.

КОНТЕКСТ:
- Файл: src/bioetl/domain/config/pipeline.py
- Строки ~112-145 содержат 7 свойств: primary_keys, silver_table, gold_table,
  write_mode, gold_write_mode, partition_cols, on_schema_mismatch.

ШАГИ:
1. Ещё раз запустить grep, чтобы убедиться что вызовов НЕ осталось:
   grep -rn 'config\.\(primary_keys\|silver_table\|gold_table\|write_mode\|gold_write_mode\|partition_cols\|on_schema_mismatch\)\b' src/bioetl/ --include="*.py" | grep -v 'self\.table\.' | grep -v 'effective_' | grep -v '_test\.'

2. Удалить свойства из pipeline.py (строки 107-145 приблизительно).
   Оставить: lock_key, effective_silver_table, effective_gold_table.

3. Обновить docstring класса — убрать упоминание convenience-свойств,
   указать что config.table.* — каноничный путь доступа.

4. Удалить импорты GoldWriteMode, SilverWriteMode, если они больше не используются в этом файле.

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
- grep -rn "convenience" src/bioetl/domain/config/pipeline.py должен вернуть 0.
```

---

## Фаза 4: Миграция YAML конфигов

### Промпт 4.1: Исправление имён сущностей в source-конфигах

```
ЗАДАЧА: Заменить устаревшие имена сущностей в файлах configs/sources/*.yaml.

КОНТЕКСТ:
- ADR-024 переименовал document → publication, но source-конфиги по-прежнему используют старые имена.
- Файл: configs/sources/chembl.yaml (и любые другие source-файлы с "document").

ШАГИ:
1. grep -rn "document" configs/sources/ для нахождения всех вхождений.
2. Заменить:
   - document → publication
   - document_similarity → publication_similarity
   - document_term → publication_term
3. НЕ менять описательный текст или комментарии, которые обсуждают само переименование.

ВЕРИФИКАЦИЯ:
- grep -rn "^\s*- document\b" configs/sources/ возвращает 0 результатов.
- Запустить интеграционные тесты загрузки конфигов, если доступны.
```

### Промпт 4.2: Упрощение pipeline-конфигов до convention-based минимального стиля

```
ЗАДАЧА: Удалить дублированные поля из всех YAML-файлов pipeline-конфигов,
оставив только convention-based минимальный стиль.

КОНТЕКСТ:
- ADR-029 установил конвенционное авто-вычисление путей, пробрасывание primary_key и т.д.
- Многие pipeline-конфиги всё ещё содержат явные избыточные поля.

ДЛЯ КАЖДОГО ФАЙЛА в configs/pipelines/{provider}/{entity}.yaml:

УДАЛИТЬ эти поля (они авто-вычисляются по конвенции):
- source_file
- dq_config_file
- data_schema_file
- filter_config_file
- sink.bronze.path
- sink.silver.path
- sink.gold.path
- sink.silver.primary_key (авто-пробрасывается из top-level primary_keys)
- sink.silver.sort_by (авто-пробрасывается из primary_keys)
- sink.gold.sort_by (авто-пробрасывается из primary_keys)
- sink.silver.csv_export.path (авто-вычисляется из пути sink)
- sink.gold.csv_export.path (авто-вычисляется из пути sink)

ПЕРЕИМЕНОВАТЬ:
- dq_rules → dq_overrides (чтобы показать, что это переопределения, а не полный набор правил)

ОСТАВИТЬ:
- pipeline_name, provider, entity_type, version, description
- primary_keys, silver_table, gold_table
- sink.silver.partition_by (entity-специфичный, не авто-вычисляется)
- sink.silver.write_mode / sink.gold.write_mode (только если отличается от default)
- содержимое dq_overrides (field_validations, cross_field_validations, conditional_validations)
- Любые другие entity-специфичные переопределения

ПОРЯДОК:
1. Начать с chembl/molecule.yaml (самый многословный, 117 строк) как шаблон.
2. Применить ко всем 30 pipeline-конфигам.
3. Пропустить composite/ конфиги (у них другая структура).

ВЕРИФИКАЦИЯ:
- Загрузчик конфигов по-прежнему создаёт идентичные доменные объекты PipelineConfig.
- Запустить: pytest tests/ -k "config" -v
```

### Промпт 4.3: Унификация именования DQ полей в YAML файлах

```
ЗАДАЧА: Переименовать ключи DQ-валидаций на унифицированные имена во всех YAML-файлах.

КОНТЕКСТ:
- Фаза 2.1 добавила поддержку алиасов в загрузчике, так что оба варианта ключей работают.
- Теперь мигрируем все YAML-файлы на новые унифицированные ключи.

ПЕРЕИМЕНОВАНИЯ:
| Уровень файла | Старый ключ | Новый ключ |
|--------------|-------------|-----------|
| configs/dq/_defaults.yaml | common_field_validations | field_validations |
| configs/dq/_defaults.yaml | common_cross_field_validations | cross_field_validations |
| configs/dq/_defaults.yaml | common_conditional_validations | conditional_validations |
| configs/dq/providers/*.yaml | provider_field_validations | field_validations |
| configs/dq/providers/*.yaml | provider_cross_field_validations | cross_field_validations |
| configs/dq/providers/*.yaml | provider_conditional_validations | conditional_validations |
| configs/dq/entities/*/*.yaml | entity_field_validations | field_validations |
| configs/dq/entities/*/*.yaml | entity_cross_field_validations | cross_field_validations |
| configs/dq/entities/*/*.yaml | entity_conditional_validations | conditional_validations |

ШАГИ:
1. Подсчитать файлы: find configs/dq/ -name "*.yaml" | wc -l
2. Для каждого файла применить переименования через sed или ручное редактирование.
3. Убедиться, что старых ключей не осталось: grep -rn "common_field_validations\|provider_field_validations\|entity_field_validations" configs/dq/

ВЕРИФИКАЦИЯ:
- Загрузчик создаёт идентичные доменные объекты DQConfig (поддержка алиасов из Фазы 2 обрабатывает оба варианта).
- pytest tests/ -k "dq" -v
```

### Промпт 4.4: Нормализация source-конфигов

```
ЗАДАЧА: Реструктуризировать все 7 YAML-файлов source-конфигов в единую схему.

КОНТЕКСТ:
- Фаза 2.2 добавила поддержку двух форматов в загрузчике.
- Теперь мигрируем YAML-файлы на новую плоскую структуру.

ЦЕЛЕВАЯ СХЕМА для каждого configs/sources/{provider}.yaml:

```yaml
version: "1.0.0"

api:
  base_url: <из source.provider_config.base_url>
  auth_type: <из source.provider_config.auth_type>
  api_key: <из source.provider_config.api_key, если есть>
  api_version: <из source.provider_config.api_version, если есть>

client:
  timeout_sec: <из source.provider_config.client.timeout_sec>
  max_retries: <из source.provider_config.client.max_retries>
  retry_base_delay: <если есть>
  retry_max_delay: <если есть>

batch:
  api_batch_size: <из source.batch_size ИЛИ source.provider_config.batch_size>
  page_size: <из source.provider_config.page_size>
  max_url_length: <из source.provider_config.max_url_length, если есть>

rate_limit:
  default:
    requests_per_second: <из rate_limit.requests_per_second>
    burst: <из rate_limit.burst>
  authenticated: <из rate_limit.with_api_key, если есть — переименовать>

circuit_breaker:
  failure_threshold: <из circuit_breaker.failure_threshold>
  recovery_timeout: <из circuit_breaker.recovery_timeout>

health_check:
  endpoint: <из health_check.endpoint>
  method: GET
  timeout_sec: <из health_check.timeout — добавить суффикс _sec>
  params: <из health_check.params, если есть>
  skip_on_429: <из health_check.skip_on_429, если есть>

retry:
  use_retry_after: <из retry.use_retry_after>

entities: <использовать канонические имена по ADR-024>
```

УДАЛИТЬ из source-конфигов:
- `dq_thresholds` (принадлежат только иерархии configs/dq/)
- `source.type` и `source.load_strategy` (если не используются загрузчиками)
- Дублированные записи `batch_size`

ФАЙЛЫ: configs/sources/chembl.yaml, crossref.yaml, openalex.yaml, pubchem.yaml,
pubmed.yaml, semanticscholar.yaml, uniprot.yaml

ВЕРИФИКАЦИЯ:
- Все фабрики адаптеров создают валидные экземпляры адаптеров.
- pytest tests/ -k "adapter or source" -v
```

### Промпт 4.5: Уменьшение _base.yaml

```
ЗАДАЧА: Сократить configs/pipelines/_base.yaml с ~491 строки до ~150 строк.

КОНТЕКСТ:
- ~60% _base.yaml — это документация/комментарии, дублирующие ADR-029 и RULES.md.
- Оставить только: значения по умолчанию с краткими inline-комментариями.
- Перенести подробную документацию в docs/03-guides/CONFIG-GUIDE.md.

ШАГИ:
1. Полностью прочитать configs/pipelines/_base.yaml.
2. Извлечь документационное содержимое в docs/03-guides/CONFIG-GUIDE.md (новый файл).
3. В _base.yaml оставить:
   - YAML-структуру со всеми значениями по умолчанию
   - Однострочные inline-комментарии для неочевидных defaults
   - Заголовки секций (# Identity, # Sink, # DQ и т.д.)
4. Удалить:
   - Многострочные объяснения
   - Блоки примеров использования
   - Ссылки на ADR (они относятся к гайду)
   - ASCII-арт / разделители

ВЕРИФИКАЦИЯ:
- Загрузчик конфигов создаёт идентичные defaults из упрощённого _base.yaml.
- pytest tests/ -k "config" -v
```

---

## Фаза 5: Реорганизация каталогов

### Промпт 5.1: Переименование каталогов конфигов

```
ЗАДАЧА: Переименовать каталоги конфигов в новые канонические имена.

ПРЕДУСЛОВИЕ: Фаза 2 (алиасы в загрузчиках) завершена и протестирована.

ПЕРЕИМЕНОВАНИЯ:
1. configs/dq/ → configs/quality/
2. configs/filter/ → configs/filters/
3. configs/data_schema/ → configs/schemas/
4. configs/composite/field_groups/ → configs/schemas/composite/field_groups/
5. configs/pipelines/_schema.json → configs/_schema/pipeline.json
6. configs/pipelines/_composite_schema.json → configs/_schema/composite.json

ШАГИ:
1. Создать новые каталоги: mkdir -p configs/quality configs/filters configs/schemas configs/_schema
2. Скопировать (не перемещать) всё содержимое:
   cp -r configs/dq/* configs/quality/
   cp -r configs/filter/* configs/filters/
   cp -r configs/data_schema/* configs/schemas/
   mkdir -p configs/schemas/composite/field_groups/
   cp configs/composite/field_groups/* configs/schemas/composite/field_groups/
   cp configs/pipelines/_schema.json configs/_schema/pipeline.json
   cp configs/pipelines/_composite_schema.json configs/_schema/composite.json
3. Запустить полный набор тестов — загрузчики должны найти новые пути первыми (алиасы из Фазы 2).
4. Если тесты проходят, удалить старые каталоги:
   rm -rf configs/dq/ configs/filter/ configs/data_schema/ configs/composite/
   rm configs/pipelines/_schema.json configs/pipelines/_composite_schema.json

ВЕРИФИКАЦИЯ:
- find configs/ -name "*.yaml" | wc -l — то же количество, что и до переименования.
- pytest tests/ -x --timeout=120
- Никаких ссылок на старые пути в коде загрузчиков (кроме fallback-логики из Фазы 2).
```

---

## Фаза 6: Очистка и финализация

### Промпт 6.1: Удаление алиасов обратной совместимости

```
ЗАДАЧА: Удалить поддержку старого формата (алиасы) из загрузчиков конфигов.

ПРЕДУСЛОВИЕ: Все YAML-файлы мигрированы (Фаза 4) и каталоги переименованы (Фаза 5).

ФАЙЛЫ:
- src/bioetl/infrastructure/config/dq_config_loader.py — удалить алиасы старых ключей
- src/bioetl/infrastructure/config/filter_config_loader.py — удалить fallback на старые пути
- src/bioetl/infrastructure/config/pipeline_config_loader.py — удалить алиас dq_rules
- src/bioetl/composition/providers/_config_helpers.py — удалить поддержку старого формата source

ШАГИ:
1. Убедиться, что файлов в старом формате не осталось:
   grep -rn "common_field_validations\|provider_field_validations\|entity_field_validations" configs/
   grep -rn "dq_rules:" configs/pipelines/
   ls configs/dq/ 2>/dev/null (не должен существовать)
   ls configs/filter/ 2>/dev/null (не должен существовать)
2. Удалить код алиасов/fallback, добавленный в Фазе 2.
3. Убрать любые deprecation-предупреждения.

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/
- pytest tests/ -x --timeout=120
```

### Промпт 6.2: Очистка validation.py

```
ЗАДАЧА: Удалить структурный шум из domain/config/validation.py, сохранив
семантически важную документацию.

ФАЙЛ: src/bioetl/domain/config/validation.py

УДАЛИТЬ:
- Комментарии-разделители секций (# ============, # ---- и т.д.)
- Многословный docstring модуля (оставить одну строку)
- Избыточные пробелы/форматирование

СОХРАНИТЬ (НЕ удалять):
- Docstring-и атрибутов ValidationConfig (диапазоны годов публикаций, молекулярных масс)
- Пояснения Literal для FieldValidation.validation_type (что означают "required", "not_null", "range")
- Inline-комментарии к Literal CrossFieldValidation.condition (что означают "all_present" и т.д.)
- Описания атрибутов ConditionalValidation

ВЕРИФИКАЦИЯ:
- mypy --strict src/bioetl/domain/config/validation.py
- pytest tests/unit/domain/config/ -v
```

### Промпт 6.3: Архитектурные и регрессионные тесты

```
ЗАДАЧА: Добавить тесты, валидирующие результаты рефакторинга.

НОВЫЕ ТЕСТОВЫЕ ФАЙЛЫ:

1. tests/architecture/test_filter_separation.py:
   - SilverFilterConfig НЕ является подклассом GoldFilterConfig
   - GoldFilterConfig НЕ является подклассом SilverFilterConfig
   - Оба ЯВЛЯЮТСЯ подклассами BaseFilterConfig
   - isinstance(SilverFilterConfig(...), GoldFilterConfig) — False
   - Никакой код за пределами domain/filtering/ не импортирует _base_filter_config напрямую

2. tests/unit/domain/config/test_effective_tables.py:
   - effective_silver_table возвращает table.silver_table, когда он задан
   - effective_silver_table возвращает "{provider}.{entity_type}" как fallback
   - effective_gold_table — аналогичные тесты

3. tests/integration/config/test_config_loading.py:
   - Загрузить каждый pipeline-конфиг из YAML → убедиться что PipelineConfig валиден
   - Загрузить DQ-конфиг с унифицированными ключами → убедиться что доменный объект такой же, как со старыми ключами
   - Загрузить source-конфиг в новом формате → убедиться что создание адаптера работает

4. tests/unit/domain/filtering/test_base_filter_config.py:
   - Параметризованный: и GoldFilterConfig, и SilverFilterConfig проходят идентичные
     тест-кейсы should_include() (доказывая, что общая базовая логика работает)

ВЕРИФИКАЦИЯ:
- pytest tests/ -x --timeout=120
- pytest --cov=src/bioetl --cov-fail-under=85
```

### Промпт 6.4: Обновление ADR и документации

```
ЗАДАЧА: Обновить архитектурную документацию для отражения изменений структуры конфигов.

ФАЙЛЫ ДЛЯ ОБНОВЛЕНИЯ:
1. docs/02-architecture/decisions/ — найти ADR-027, ADR-028, ADR-029:
   - Обновить все ссылки с configs/dq/ → configs/quality/
   - Обновить с configs/filter/ → configs/filters/
   - Обновить с configs/data_schema/ → configs/schemas/
   - Отметить унифицированное именование DQ-ключей

2. docs/00-project/RULES.md — если содержит ссылки на пути конфигов, обновить их.

3. Создать docs/03-guides/CONFIG-GUIDE.md (содержимое извлечено из _base.yaml в Фазе 4.5).

НЕ создавать файлы, которые уже существуют. Сначала проверить.

ВЕРИФИКАЦИЯ:
- grep -rn "configs/dq/" docs/ возвращает 0 (или только в исторических ADR, помеченных как superseded)
- grep -rn "configs/filter/" docs/ возвращает 0
- grep -rn "configs/data_schema/" docs/ возвращает 0
```

---

## Заметки по выполнению

### Параллелизация
- **Внутри Фазы 1:** Шаги 1.1 и 1.3 независимы. Шаг 1.2 зависит от 1.1.
- **Фазы 1 и 2:** Можно запускать параллельно (разные слои).
- **Фаза 3:** Последовательно (3.1 → 3.2 → 3.3). Зависит от Фазы 1.
- **Фаза 4:** Шаги 4.1, 4.3, 4.4, 4.5 можно параллелизировать. Шаг 4.2 должен быть последним.
  Зависит от Фазы 2.
- **Фаза 5:** Единый шаг, зависит от Фазы 4.
- **Фаза 6:** Шаги 6.1-6.4 можно параллелизировать. Зависит от Фазы 5.

### Откат
Каждая Фаза должна быть отдельным коммитом (или группой коммитов).
Откат = `git revert <phase-commit>`.

### Частота верификации
После КАЖДОГО выполненного промпта:
1. `mypy --strict src/bioetl/` (типобезопасность)
2. `pytest tests/architecture/ -v` (границы импортов)
3. `pytest tests/ -x --timeout=120` (полный набор тестов, fail-fast)
