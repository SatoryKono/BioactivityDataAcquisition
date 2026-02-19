# Промты для исправления ветки codex/refactor-filtering-configuration-classes

> Результат аудита от 2026-02-13. Каждый промт — самодостаточная задача.
> Порядок выполнения: FIX-1 → FIX-2 → FIX-3 → FIX-4 → FIX-5 → FIX-6 → FIX-7.

---

## FIX-1: Откатить удаление str→enum конвертации в TableConfig (CRITICAL)

```
Контекст: В ветке codex/refactor-filtering-configuration-classes из файла
src/bioetl/domain/config/table.py была удалена конвертация str→enum
в --post-init--. Тип полей изменён с `SilverWriteMode | str` на
`SilverWriteMode`. Но Python dataclass не валидирует типы при инициализации —
строки молча сохраняются. Это ломает:
- tests/architecture/test-write-mode-types.py (3 теста)
- tests/unit/application/core/test-preflight-service.py (3 теста)
- Любой код, создающий TableConfig со строковым write-mode.

Задача: Восстановить исходный файл src/bioetl/domain/config/table.py
из main-ветки. Конкретно:

1. Вернуть import: `from bioetl.domain.config.-converters import convert-write-mode, freeze-sequences`
2. Вернуть тип `SilverWriteMode | str` и `GoldWriteMode | str` для полей
3. Вернуть в --post-init-- блоки:
   ```python
   object.--setattr--(
       self, "silver-write-mode",
       convert-write-mode(self.silver-write-mode, SilverWriteMode),
   )
   object.--setattr--(
       self, "gold-write-mode",
       convert-write-mode(self.gold-write-mode, GoldWriteMode),
   )
   ```

Также восстановить тип `SilverWriteMode | str` (вместо голого `SilverWriteMode`)
в файлах:
- src/bioetl/composition/factories/services-factory.py — параметры
  silver-write-mode и gold-write-mode метода -configure-services
- src/bioetl/domain/config/pipeline.py — свойства write-mode и gold-write-mode

Изменение типов в -extract-write-modes (infrastructure/config/-base.py)
на `tuple[SilverWriteMode, GoldWriteMode]` корректно и должно остаться.

НЕ ТРОГАТЬ тесты — после отката они должны проходить как есть.
```

---

## FIX-2: Откатить извлечение BaseFilterConfig (CRITICAL)

```
Контекст: В ветке codex/refactor-filtering-configuration-classes логика
фильтрации была извлечена в новый файл
src/bioetl/domain/filtering/-base-filter-config.py (класс BaseFilterConfig).
GoldFilterConfig и SilverFilterConfig стали наследниками BaseFilterConfig
вместо прежней иерархии (SilverFilterConfig → GoldFilterConfig).

Это ломает API: метод from-gold-filter-config переименован в from-base,
вызовы в infrastructure не совместимы с main, класс BaseFilterConfig
экспортирован публично через underscore-prefixed модуль.

Задача: Восстановить оригинальные 3 файла domain слоя из main:

1. УДАЛИТЬ файл src/bioetl/domain/filtering/-base-filter-config.py

2. Восстановить src/bioetl/domain/filtering/gold-config.py из main:
   - Класс GoldFilterConfig должен содержать все методы inline
     (should-include, -check-*, -is-empty-value, is-empty и т.д.)
   - Модуль-уровневый -OPERATOR-CHECKERS dict
   - Все импорты (Callable, Any, FilterOperator, etc.)

3. Восстановить src/bioetl/domain/filtering/silver-config.py из main:
   - SilverFilterConfig(GoldFilterConfig) — наследует от GoldFilterConfig
   - Метод from-gold-filter-config (НЕ from-base)
   - Полная docstring

4. Восстановить src/bioetl/domain/filtering/--init--.py из main:
   - Убрать import и --all---запись для BaseFilterConfig

5. Адаптировать вызывающий код в infrastructure к оригинальному API:
   - src/bioetl/infrastructure/config/-base.py:120 —
     заменить `SilverFilterConfig.from-base(gold)` на
     `SilverFilterConfig.from-gold-filter-config(gold)`
   - src/bioetl/infrastructure/schemas/filter-config.py:108 —
     заменить `SilverFilterConfig.from-base(super().to-domain())` на
     `SilverFilterConfig.from-gold-filter-config(super().to-domain())`

6. В тестах tests/unit/domain/filtering/test-silver-config.py:
   - Если тест ссылается на from-base — заменить на from-gold-filter-config
   - Если тест проверяет issubclass(SilverFilterConfig, GoldFilterConfig) is False —
     заменить на True (Silver НАСЛЕДУЕТ от Gold в оригинальной иерархии)
```

---

## FIX-3: Скорректировать типизацию silver-filters в transformer signatures (HIGH)

```
Контекст: В ветке codex тип параметра silver-filters изменён с
`SilverFilterConfig | GoldFilterConfig | None` на `SilverFilterConfig | None`
во всех трансформерах. Это КОРРЕКТНОЕ изменение — оно усиливает
типобезопасность и предотвращает случайное использование GoldFilterConfig
в Silver-слоте.

Задача: Убедиться, что после применения FIX-1 и FIX-2 изменение типа
silver-filters параметра остаётся корректным.

Поскольку в оригинальной иерархии SilverFilterConfig наследует GoldFilterConfig,
тип `SilverFilterConfig | None` принимает SilverFilterConfig, а
`GoldFilterConfig | None` — оба типа. Поэтому сужение типа с
`SilverFilterConfig | GoldFilterConfig | None` до `SilverFilterConfig | None`
корректно и полезно.

Файлы, где тип уже изменён (оставить как есть):
- src/bioetl/application/core/base-transformer.py
- src/bioetl/application/pipelines/chembl/base-chembl-transformer.py
- src/bioetl/application/pipelines/chembl/publication-transformer.py
- src/bioetl/application/pipelines/crossref/transformer.py
- src/bioetl/application/pipelines/openalex/transformer.py
- src/bioetl/application/pipelines/pubchem/transformer.py
- src/bioetl/application/pipelines/pubmed/transformer.py
- src/bioetl/application/pipelines/semanticscholar/transformer.py
- src/bioetl/application/pipelines/uniprot/idmapping-transformer.py
- src/bioetl/application/pipelines/uniprot/transformer.py
- src/bioetl/composition/factories/pipeline-factory.py
- src/bioetl/composition/factories/transformer-factory.py
- src/bioetl/domain/config/pipeline.py (поле silver-filters)

Проверить: удалённый `cast` import в crossref, openalex, semanticscholar
трансформерах. Если cast больше нигде не используется в файле — удаление
корректно.
```

---

## FIX-4: Скорректировать SilverFiltersFileConfig.to-domain() тип возврата (HIGH)

```
Контекст: В ветке codex SilverFiltersFileConfig.to-domain() в файле
src/bioetl/infrastructure/schemas/filter-config.py изменён с возврата
GoldFilterConfig на SilverFilterConfig. FilterConfigLoader.load() также
изменён с `tuple[InputFilterConfig, GoldFilterConfig, GoldFilterConfig, ExtractionParams]`
на `tuple[InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]`.

Эти изменения КОРРЕКТНЫ и усиливают типобезопасность. Однако после FIX-2
(откат from-base → from-gold-filter-config) нужно адаптировать реализацию.

Задача:

1. В src/bioetl/infrastructure/schemas/filter-config.py:
   Класс SilverFiltersFileConfig — метод to-domain():
   ```python
   def to-domain(self) -> SilverFilterConfig:
       return SilverFilterConfig.from-gold-filter-config(super().to-domain())
   ```
   (Использовать from-gold-filter-config вместо from-base)

2. В src/bioetl/infrastructure/schemas/filter-config.py:
   Класс FilterConfigFile — метод to-domain():
   Тип возврата должен быть:
   `tuple[DomainInputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]`

3. В src/bioetl/infrastructure/config/filter-config-loader.py:
   - Тип FilterConfigLoader generic:
     `BaseConfigLoader[tuple[InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]]`
   - Метод load() возвращает:
     `tuple[InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]`
   - Добавить import SilverFilterConfig из bioetl.domain.filtering

4. Тесты (оставить как есть из codex-ветки):
   - tests/unit/infrastructure/config/test-filter-config-loader.py
   - tests/unit/infrastructure/schemas/test-filter-config.py
```

---

## FIX-5: dq-overrides → dq-overrides rename (MEDIUM, оставить как есть)

```
Контекст: В ветке codex поле dq-overrides в PipelineYamlConfig переименовано
в dq-overrides с backward-compatible AliasChoices("dq-overrides", "dq-overrides", "dq").
Это КОРРЕКТНОЕ изменение. Аудит не выявил проблем.

Задача: Убедиться, что все вызовы dq-overrides заменены на dq-overrides:

1. src/bioetl/infrastructure/schemas/pipeline-config.py:
   - Поле: `dq-overrides: DQConfig` с validation-alias=AliasChoices("dq-overrides", "dq-overrides", "dq")
   - serialization-alias="dq-overrides"

2. src/bioetl/infrastructure/config/pipeline-config-loader.py:
   - -has-inline-dq-overrides → -has-inline-dq-overrides
   - -normalize-inline-dq-overrides → -normalize-inline-dq-overrides
   - Все обращения yaml-config.dq-overrides → yaml-config.dq-overrides

3. src/bioetl/infrastructure/config/-base.py:
   - yaml-config.dq-overrides.to-domain() → yaml-config.dq-overrides.to-domain()

4. Тесты: проверить что тесты dq-overrides + legacy dq-overrides alias работают.

НЕ ТРЕБУЕТ ИЗМЕНЕНИЙ если уже реализовано как в codex-ветке. Просто верифицировать.
```

---

## FIX-6: Директории filter→filters, dq→quality с fallback (MEDIUM, оставить как есть)

```
Контекст: В ветке codex добавлена логика fallback для директорий конфигов:
- configs/filters (new) → configs/filter (legacy)
- configs/quality (new) → configs/dq (legacy)
- configs/schemas (new) → configs/data-schema (legacy)

Реализация через -PATH-ALIAS-GROUPS, -resolve-with-path-aliases,
-resolve-dq-path, -resolve-filter-path.

Задача: Верифицировать корректность и оставить как есть. Проверить:

1. src/bioetl/infrastructure/config-loader.py:
   - -PATH-ALIAS-GROUPS tuple определён
   - -resolve-with-path-aliases корректно обрабатывает обе стороны
   - -apply-file-reference-defaults использует новые пути:
     dq-config-file → ../../quality/..., filter-config-file → ../../filters/...

2. src/bioetl/infrastructure/config/dq-config-loader.py:
   - -dq-roots = (configs-root / "quality", configs-root / "dq")
   - -resolve-dq-path с fallback

3. src/bioetl/infrastructure/config/filter-config-loader.py:
   - -filter-roots = (configs-root / "filters", configs-root / "filter")
   - -resolve-filter-path с fallback

4. Тесты fallback-логики:
   - test-dq-loader-prefers-new-quality-dir
   - test-dq-loader-falls-back-to-legacy-dq-dir
   - test-filter-loader-prefers-new-filters-dir
   - test-filter-loader-falls-back-to-legacy-filter-dir
   - test-filter-config-legacy-path-fallback
   - test-data-schema-legacy-path-fallback

НЕ ТРЕБУЕТ ИЗМЕНЕНИЙ. Просто верифицировать после применения FIX-1..FIX-4.
```

---

## FIX-7: Декомпозировать -normalize-source-config (LOW, отдельный PR)

```
Контекст: Функция -normalize-source-config в
src/bioetl/infrastructure/config-loader.py (~130 LOC, CC>15) содержит
избыточно сложную логику нормализации с дублированием паттерна
timeout/timeout-sec конвертации.

Задача (рекомендация для отдельного PR):

1. Извлечь helper-функции:
   - -normalize-rate-limit(source: dict) -> dict
     Логика: with-api-key ↔ authenticated alias
   - -normalize-health-check(source: dict) -> dict
     Логика: timeout ↔ timeout-sec alias
   - -normalize-client-timeout(client: dict) -> dict
     Логика: timeout ↔ timeout-sec alias (переиспользовать для 4 мест)
   - -project-legacy-to-new-style(source: dict, provider-config: dict) -> None
     Логика: provider-config.* → api/client/batch
   - -consume-new-style-to-legacy(source: dict) -> dict
     Логика: api/client/batch → provider-config.*

2. Добавить unit-тесты для edge cases:
   - Пустой provider-config
   - Конфликт api + provider-config.base-url
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

6. Проверка что -base-filter-config.py удалён:
   test ! -f src/bioetl/domain/filtering/-base-filter-config.py

7. Проверка что from-gold-filter-config используется (НЕ from-base):
   grep -rn "from-base" src/bioetl/ --include="*.py"
   # Должно быть пусто

8. Проверка backward-compatibility dq-overrides alias:
   python -c "
   from bioetl.infrastructure.schemas.pipeline-config import PipelineYamlConfig
   cfg = PipelineYamlConfig.model-validate({
       'pipeline-name': 'test', 'provider': 'p', 'entity-type': 'e',
       'primary-keys': ['id'], 'silver-table': 'silver.t',
       'dq-overrides': {'soft-fail-threshold': 0.1}
   })
   assert cfg.dq-overrides.soft-fail-threshold == 0.1
   print('dq-overrides alias OK')
   "
```
