# Промты для исправления ветки codex/refactor-filtering-configuration-classes

> Результат аудита от 2026-02-13. Каждый промт — самодостаточная задача.
> Порядок выполнения: FIX-1 → FIX-2 → FIX-3 → FIX-4 → FIX-5 → FIX-6 → FIX-7.

---

## FIX-1: Откатить удаление str→enum конвертации в TableConfig (CRITICAL)

```
Контекст: В ветке codex/refactor-filtering-configuration-classes из файла
src/bioetl/domain/config/table.py была удалена конвертация str→enum
в __post_init__. Тип полей изменён с `SilverWriteMode | str` на
`SilverWriteMode`. Но Python dataclass не валидирует типы при инициализации —
строки молча сохраняются. Это ломает:
- tests/architecture/test_write_mode_types.py (3 теста)
- tests/unit/application/core/test_preflight_service.py (3 теста)
- Любой код, создающий TableConfig со строковым write_mode.

Задача: Восстановить исходный файл src/bioetl/domain/config/table.py
из main-ветки. Конкретно:

1. Вернуть import: `from bioetl.domain.config._converters import convert_write_mode, freeze_sequences`
2. Вернуть тип `SilverWriteMode | str` и `GoldWriteMode | str` для полей
3. Вернуть в __post_init__ блоки:
   ```python
   object.__setattr__(
       self, "silver_write_mode",
       convert_write_mode(self.silver_write_mode, SilverWriteMode),
   )
   object.__setattr__(
       self, "gold_write_mode",
       convert_write_mode(self.gold_write_mode, GoldWriteMode),
   )
   ```

Также восстановить тип `SilverWriteMode | str` (вместо голого `SilverWriteMode`)
в файлах:
- src/bioetl/composition/factories/services_factory.py — параметры
  silver_write_mode и gold_write_mode метода _configure_services
- src/bioetl/domain/config/pipeline.py — свойства write_mode и gold_write_mode

Изменение типов в _extract_write_modes (infrastructure/config/_base.py)
на `tuple[SilverWriteMode, GoldWriteMode]` корректно и должно остаться.

НЕ ТРОГАТЬ тесты — после отката они должны проходить как есть.
```

---

## FIX-2: Откатить извлечение BaseFilterConfig (CRITICAL)

```
Контекст: В ветке codex/refactor-filtering-configuration-classes логика
фильтрации была извлечена в новый файл
src/bioetl/domain/filtering/_base_filter_config.py (класс BaseFilterConfig).
GoldFilterConfig и SilverFilterConfig стали наследниками BaseFilterConfig
вместо прежней иерархии (SilverFilterConfig → GoldFilterConfig).

Это ломает API: метод from_gold_filter_config переименован в from_base,
вызовы в infrastructure не совместимы с main, класс BaseFilterConfig
экспортирован публично через underscore-prefixed модуль.

Задача: Восстановить оригинальные 3 файла domain слоя из main:

1. УДАЛИТЬ файл src/bioetl/domain/filtering/_base_filter_config.py

2. Восстановить src/bioetl/domain/filtering/gold_config.py из main:
   - Класс GoldFilterConfig должен содержать все методы inline
     (should_include, _check_*, _is_empty_value, is_empty и т.д.)
   - Модуль-уровневый _OPERATOR_CHECKERS dict
   - Все импорты (Callable, Any, FilterOperator, etc.)

3. Восстановить src/bioetl/domain/filtering/silver_config.py из main:
   - SilverFilterConfig(GoldFilterConfig) — наследует от GoldFilterConfig
   - Метод from_gold_filter_config (НЕ from_base)
   - Полная docstring

4. Восстановить src/bioetl/domain/filtering/__init__.py из main:
   - Убрать import и __all__-запись для BaseFilterConfig

5. Адаптировать вызывающий код в infrastructure к оригинальному API:
   - src/bioetl/infrastructure/config/_base.py:120 —
     заменить `SilverFilterConfig.from_base(gold)` на
     `SilverFilterConfig.from_gold_filter_config(gold)`
   - src/bioetl/infrastructure/schemas/filter_config.py:108 —
     заменить `SilverFilterConfig.from_base(super().to_domain())` на
     `SilverFilterConfig.from_gold_filter_config(super().to_domain())`

6. В тестах tests/unit/domain/filtering/test_silver_config.py:
   - Если тест ссылается на from_base — заменить на from_gold_filter_config
   - Если тест проверяет issubclass(SilverFilterConfig, GoldFilterConfig) is False —
     заменить на True (Silver НАСЛЕДУЕТ от Gold в оригинальной иерархии)
```

---

## FIX-3: Скорректировать типизацию silver_filters в transformer signatures (HIGH)

```
Контекст: В ветке codex тип параметра silver_filters изменён с
`SilverFilterConfig | GoldFilterConfig | None` на `SilverFilterConfig | None`
во всех трансформерах. Это КОРРЕКТНОЕ изменение — оно усиливает
типобезопасность и предотвращает случайное использование GoldFilterConfig
в Silver-слоте.

Задача: Убедиться, что после применения FIX-1 и FIX-2 изменение типа
silver_filters параметра остаётся корректным.

Поскольку в оригинальной иерархии SilverFilterConfig наследует GoldFilterConfig,
тип `SilverFilterConfig | None` принимает SilverFilterConfig, а
`GoldFilterConfig | None` — оба типа. Поэтому сужение типа с
`SilverFilterConfig | GoldFilterConfig | None` до `SilverFilterConfig | None`
корректно и полезно.

Файлы, где тип уже изменён (оставить как есть):
- src/bioetl/application/core/base_transformer.py
- src/bioetl/application/pipelines/chembl/base_chembl_transformer.py
- src/bioetl/application/pipelines/chembl/publication_transformer.py
- src/bioetl/application/pipelines/crossref/transformer.py
- src/bioetl/application/pipelines/openalex/transformer.py
- src/bioetl/application/pipelines/pubchem/transformer.py
- src/bioetl/application/pipelines/pubmed/transformer.py
- src/bioetl/application/pipelines/semanticscholar/transformer.py
- src/bioetl/application/pipelines/uniprot/idmapping_transformer.py
- src/bioetl/application/pipelines/uniprot/transformer.py
- src/bioetl/composition/factories/pipeline_factory.py
- src/bioetl/composition/factories/transformer_factory.py
- src/bioetl/domain/config/pipeline.py (поле silver_filters)

Проверить: удалённый `cast` import в crossref, openalex, semanticscholar
трансформерах. Если cast больше нигде не используется в файле — удаление
корректно.
```

---

## FIX-4: Скорректировать SilverFiltersFileConfig.to_domain() тип возврата (HIGH)

```
Контекст: В ветке codex SilverFiltersFileConfig.to_domain() в файле
src/bioetl/infrastructure/schemas/filter_config.py изменён с возврата
GoldFilterConfig на SilverFilterConfig. FilterConfigLoader.load() также
изменён с `tuple[InputFilterConfig, GoldFilterConfig, GoldFilterConfig, ExtractionParams]`
на `tuple[InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]`.

Эти изменения КОРРЕКТНЫ и усиливают типобезопасность. Однако после FIX-2
(откат from_base → from_gold_filter_config) нужно адаптировать реализацию.

Задача:

1. В src/bioetl/infrastructure/schemas/filter_config.py:
   Класс SilverFiltersFileConfig — метод to_domain():
   ```python
   def to_domain(self) -> SilverFilterConfig:
       return SilverFilterConfig.from_gold_filter_config(super().to_domain())
   ```
   (Использовать from_gold_filter_config вместо from_base)

2. В src/bioetl/infrastructure/schemas/filter_config.py:
   Класс FilterConfigFile — метод to_domain():
   Тип возврата должен быть:
   `tuple[DomainInputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]`

3. В src/bioetl/infrastructure/config/filter_config_loader.py:
   - Тип FilterConfigLoader generic:
     `BaseConfigLoader[tuple[InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]]`
   - Метод load() возвращает:
     `tuple[InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]`
   - Добавить import SilverFilterConfig из bioetl.domain.filtering

4. Тесты (оставить как есть из codex-ветки):
   - tests/unit/infrastructure/config/test_filter_config_loader.py
   - tests/unit/infrastructure/schemas/test_filter_config.py
```

---

## FIX-5: dq_rules → dq_overrides rename (MEDIUM, оставить как есть)

```
Контекст: В ветке codex поле dq_rules в PipelineYamlConfig переименовано
в dq_overrides с backward-compatible AliasChoices("dq_overrides", "dq_rules", "dq").
Это КОРРЕКТНОЕ изменение. Аудит не выявил проблем.

Задача: Убедиться, что все вызовы dq_rules заменены на dq_overrides:

1. src/bioetl/infrastructure/schemas/pipeline_config.py:
   - Поле: `dq_overrides: DQConfig` с validation_alias=AliasChoices("dq_overrides", "dq_rules", "dq")
   - serialization_alias="dq_overrides"

2. src/bioetl/infrastructure/config/pipeline_config_loader.py:
   - _has_inline_dq_rules → _has_inline_dq_overrides
   - _normalize_inline_dq_rules → _normalize_inline_dq_overrides
   - Все обращения yaml_config.dq_rules → yaml_config.dq_overrides

3. src/bioetl/infrastructure/config/_base.py:
   - yaml_config.dq_rules.to_domain() → yaml_config.dq_overrides.to_domain()

4. Тесты: проверить что тесты dq_overrides + legacy dq_rules alias работают.

НЕ ТРЕБУЕТ ИЗМЕНЕНИЙ если уже реализовано как в codex-ветке. Просто верифицировать.
```

---

## FIX-6: Директории filter→filters, dq→quality с fallback (MEDIUM, оставить как есть)

```
Контекст: В ветке codex добавлена логика fallback для директорий конфигов:
- configs/filters (new) → configs/filter (legacy)
- configs/quality (new) → configs/dq (legacy)
- configs/schemas (new) → configs/data_schema (legacy)

Реализация через _PATH_ALIAS_GROUPS, _resolve_with_path_aliases,
_resolve_dq_path, _resolve_filter_path.

Задача: Верифицировать корректность и оставить как есть. Проверить:

1. src/bioetl/infrastructure/config_loader.py:
   - _PATH_ALIAS_GROUPS tuple определён
   - _resolve_with_path_aliases корректно обрабатывает обе стороны
   - _apply_file_reference_defaults использует новые пути:
     dq_config_file → ../../quality/..., filter_config_file → ../../filters/...

2. src/bioetl/infrastructure/config/dq_config_loader.py:
   - _dq_roots = (configs_root / "quality", configs_root / "dq")
   - _resolve_dq_path с fallback

3. src/bioetl/infrastructure/config/filter_config_loader.py:
   - _filter_roots = (configs_root / "filters", configs_root / "filter")
   - _resolve_filter_path с fallback

4. Тесты fallback-логики:
   - test_dq_loader_prefers_new_quality_dir
   - test_dq_loader_falls_back_to_legacy_dq_dir
   - test_filter_loader_prefers_new_filters_dir
   - test_filter_loader_falls_back_to_legacy_filter_dir
   - test_filter_config_legacy_path_fallback
   - test_data_schema_legacy_path_fallback

НЕ ТРЕБУЕТ ИЗМЕНЕНИЙ. Просто верифицировать после применения FIX-1..FIX-4.
```

---

## FIX-7: Декомпозировать _normalize_source_config (LOW, отдельный PR)

```
Контекст: Функция _normalize_source_config в
src/bioetl/infrastructure/config_loader.py (~130 LOC, CC>15) содержит
избыточно сложную логику нормализации с дублированием паттерна
timeout/timeout_sec конвертации.

Задача (рекомендация для отдельного PR):

1. Извлечь helper-функции:
   - _normalize_rate_limit(source: dict) -> dict
     Логика: with_api_key ↔ authenticated alias
   - _normalize_health_check(source: dict) -> dict
     Логика: timeout ↔ timeout_sec alias
   - _normalize_client_timeout(client: dict) -> dict
     Логика: timeout ↔ timeout_sec alias (переиспользовать для 4 мест)
   - _project_legacy_to_new_style(source: dict, provider_config: dict) -> None
     Логика: provider_config.* → api/client/batch
   - _consume_new_style_to_legacy(source: dict) -> dict
     Логика: api/client/batch → provider_config.*

2. Добавить unit-тесты для edge cases:
   - Пустой provider_config
   - Конфликт api + provider_config.base_url
   - batch как int vs dict
   - Отсутствие source ключа

3. Добавить docstring с примерами входных/выходных форматов.

Этот FIX не блокирующий. Текущий код работает корректно, но нарушает
принцип single responsibility и затрудняет code review.
```

---

## Чек-лист верификации после применения всех фиксов

```
После применения FIX-1..FIX-6, выполнить:

1. Запуск архитектурных тестов:
   pytest tests/architecture/ -v

2. Запуск unit-тестов domain:
   pytest tests/unit/domain/ -v

3. Запуск unit-тестов infrastructure:
   pytest tests/unit/infrastructure/ -v

4. Запуск type-check:
   mypy --strict src/bioetl/domain/config/table.py
   mypy --strict src/bioetl/domain/filtering/

5. Проверка import boundaries:
   grep -rn "from bioetl.infrastructure" src/bioetl/domain/ --include="*.py"
   # Должно быть пусто

6. Проверка что _base_filter_config.py удалён:
   test ! -f src/bioetl/domain/filtering/_base_filter_config.py

7. Проверка что from_gold_filter_config используется (НЕ from_base):
   grep -rn "from_base" src/bioetl/ --include="*.py"
   # Должно быть пусто

8. Проверка backward-compatibility dq_rules alias:
   python -c "
   from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
   cfg = PipelineYamlConfig.model_validate({
       'pipeline_name': 'test', 'provider': 'p', 'entity_type': 'e',
       'primary_keys': ['id'], 'silver_table': 'silver.t',
       'dq_rules': {'soft_fail_threshold': 0.1}
   })
   assert cfg.dq_overrides.soft_fail_threshold == 0.1
   print('dq_rules alias OK')
   "
```
