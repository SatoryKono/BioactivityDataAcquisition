# RF-FS-006 Baseline Plan

**Дата:** 2026-03-19  
**Тема:** Удалить или канонизировать orphan/wrapper candidates после подтверждения их реального статуса  
**Связанные находки:** `FS-003`  
**Основной scope:** `src/bioetl/composition/bootstrap/runtime/`, `src/bioetl/composition/factories/storage/`, `src/bioetl/domain/transformations/`, а также metadata wrapper chain вокруг `composite_metadata_helpers`

## Цель

`RF-FS-006` должен сократить структурный шум, но без ложной агрессии. По baseline есть набор статически “подозрительных” модулей, у которых не найдено входящих импортов в обычном проектном графе. Часть из них может быть реально мёртвой. Часть может использоваться динамически. Часть может существовать как compatibility façade или тонкий wrapper, который уже потерял смысл после прошлых refactor-wave. Ошибка здесь очень типична: удалить файлы на основе только static import scan и потом ломать runtime bootstrap, lazy loading или косвенные integration paths. Поэтому ключевая задача `RF-FS-006` — не удаление само по себе, а перевод каждого кандидата в подтверждённый статус: `dead`, `dynamic`, `retain`, `merge`.

## Базовый список кандидатов

На текущем baseline внимания требуют:
- отдельные модули в `src/bioetl/composition/bootstrap/runtime/`, включая `composite_support_service_builders.py`, `dq_bootstrap.py`, `logger_bootstrap.py` и соседние helpers;
- `src/bioetl/composition/factories/storage/storage_factory.py` и связанные `_bronze.py`, `_silver.py`, `_gold.py`, `_helpers.py`-модули;
- `src/bioetl/domain/transformations/coercion.py`, `drift.py`, `hashing.py`, `quality.py`;
- `src/bioetl/infrastructure/storage/metadata_builder_composite_helpers.py` как часть wrapper chain вместе с `src/bioetl/application/services/metadata_assemblers_helpers.py` и `src/bioetl/domain/services/composite_metadata_helpers.py`;
- дополнительно стоит держать в уме `src/bioetl/composition/types.py`, хотя он не обязательно войдёт в первую волну cleanup.

## Почему задача важна

Orphan/wrapper candidates вредят не только как потенциальный dead code. Они создают ложные точки входа в кодовую базу. Разработчик находит helper, который выглядит owner-модулем, а на деле является тонким мостом к другому owner. Это затрудняет поиск истины, плодит compatibility paths и размывает boundaries. Особенно опасны wrapper chains вокруг metadata/composite helpers: если доменный helper уже существует, дополнительные application/infrastructure wrappers должны либо давать layer-specific value, либо исчезнуть.

## Порядок выполнения

### Шаг 1. Подтвердить статусы

Это обязательный этап. Для каждого кандидата нужно понять:
- есть ли динамический импорт, registry registration, lazy bootstrap use или reflection-based lookup;
- используется ли модуль только как historical import path;
- дублирует ли он другой owner-модуль без добавления поведения;
- содержит ли он самостоятельную ценность.

Без этого шага любые delete/merge решения ненадёжны.

### Шаг 2. Отдельно разобрать metadata wrapper chain

Это самый сильный кандидат на merge. Если `domain/services/composite_metadata_helpers.py` уже является канонической реализацией, то `application/services/metadata_assemblers_helpers.py` и `infrastructure/storage/metadata_builder_composite_helpers.py` должны либо держать минимальные layer-specific adapters, либо быть слиты/упрощены. Здесь нельзя сохранять “wrapper ради wrapper”, если он только пересылает вызовы без собственной политики.

### Шаг 3. Разобрать runtime/bootstrap кандидатов

`composition/bootstrap/runtime` особенно чувствителен. Даже если модуль статически orphaned, он может вызываться через bootstrap mapping, registry hook или composition entrypoint. Поэтому для него нужен более строгий аудит: grep по project references, bootstrap route review, возможно targeted smoke tests.

### Шаг 4. Разобрать storage factory cluster

`composition/factories/storage` может содержать файлы, которые выглядят orphaned из-за того, что используются через re-export или indirect factory assembly. Здесь cleanup должен идти после проверки реального call graph, иначе легко удалить вспомогательный leaf и повредить composition path.

### Шаг 5. Разобрать domain/transformations

Эта зона потенциально проще. Если transformation modules не имеют проектных входящих импортов и не участвуют в documented façades, их можно либо удалить, либо перенести в более подходящий owner-модуль. Но сперва надо убедиться, что они не используются в scripts/tests/generated paths.

## Риски

Риск средний, а местами высокий. Для runtime/bootstrap модулей он ближе к высокому: статический orphan scan почти никогда не даёт достаточного основания для удаления. Для metadata wrappers риск состоит в том, что merge может сломать layering, если убрать не wrapper, а последнюю layer-specific адаптацию. Для `domain/transformations` риск ниже, но всё равно есть шанс удалить модуль, который используется косвенно или только в опциональной фиче.

## Минимизация рисков

- Разделить `RF-FS-006` на две волны: `confirm` и `cleanup`.
- Для каждого кандидата записывать явный статус и аргументацию.
- Не удалять bootstrap/storage files до targeted smoke/unit verification.
- Wrapper merge делать только там, где есть один канонический owner и нет реального layer-specific поведения.
- Если модуль intentionally dynamic, не считать его проблемой; вместо удаления оформить его через documented sanctioned façade.

## Верификация

На этапе подтверждения:

```bash
rg -n "<module_name>|<symbol_name>" src tests configs -g '*.py' -g '*.md' -g '*.yaml'
```

Для cleanup metadata chain:

```bash
./.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/storage/test_metadata_builder.py tests/unit/infrastructure/storage/test_metadata_builder_composite_helpers.py tests/unit/infrastructure/storage/test_metadata_writer.py tests/unit/application/services -q
```

Для bootstrap/storage cleanup:

```bash
./.venv/Scripts/python.exe -m pytest tests/unit/composition tests/unit/infrastructure/storage -q
```

Параллельно после каждого батча:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

После удаления/слияния модулей:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_forbidden_imports.py tests/architecture/test_layer_dependencies.py -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## Definition of Done

`RF-FS-006` считается завершённым только если:
- каждый orphan/wrapper candidate получил подтверждённый статус;
- реально мёртвые модули удалены;
- thin wrappers без собственной ценности слиты с каноническими owner-модулями;
- intentionally dynamic modules либо сохранены как есть с явной аргументацией, либо проведены через ясный façade;
- metadata helper chain больше не содержит бессмысленных промежуточных слоёв;
- cleanup не породил regressions в bootstrap/storage/tests.

Итоговая цель этого RF — уменьшить количество ложных owner-модулей и потенциального dead code, не ломая скрытые runtime use cases и не подменяя фактическую архитектуру чисто статическим анализом.
