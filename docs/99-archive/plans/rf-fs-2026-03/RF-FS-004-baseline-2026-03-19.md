# RF-FS-004 Baseline Plan

**Дата:** 2026-03-19  
**Тема:** Нормализовать topology конфигурации и убрать размазанность config concerns по слоям  
**Связанные находки:** `FS-007`  
**Основной scope:** `configs/`, `src/bioetl/domain/config/`, `src/bioetl/domain/composite/`, `src/bioetl/infrastructure/config/`, `src/bioetl/infrastructure/schemas/`, `src/bioetl/composition/factories/pipeline/`

## Актуализация на 2026-03-19 16:58

Этот baseline по сути остаётся без изменений. Последние test-ownership waves не затронули config topology напрямую и не снимают prerequisite на composition cycle cleanup. `RF-FS-004` всё ещё лучше открывать только после адресного продвижения по `RF-FS-001`, иначе те же composition/config файлы будут перемещаться повторно.

## Цель

`RF-FS-004` должен сделать ownership конфигурации однозначным. Сейчас проблема не в том, что проект “не умеет читать YAML”. Проблема в другом: config concerns одновременно живут в файловых `configs/`, в доменных config/value objects, в infrastructure loader/schema слоях и в composition helpers. Такая topology затрудняет ответ на базовый вопрос: где именно находится canonical truth о форме конфигурации, а где только адаптация или wiring. Для Hexagonal/DDD-системы это особенно вредно, потому что слой composition начинает впитывать config behavior, domain начинает выглядеть как storage schema каталог, а infrastructure держит и loading, и normalization, и compatibility seams одновременно.

## Базовый диагноз

По текущему состоянию в проекте есть:
- `configs/` с YAML/JSON schema артефактами;
- `src/bioetl/domain/config/` с domain-facing config models;
- `src/bioetl/domain/composite/` с composite-related config/value structures;
- `src/bioetl/infrastructure/config/` с loader/normalization code;
- `src/bioetl/infrastructure/schemas/` с pydantic/schema layer;
- `src/bioetl/composition/factories/pipeline/` с дополнительными config helpers и wiring.

Отдельно нужно учитывать, что часть legacy seams ещё существует по историческим причинам. Значит задача не может начаться с агрессивного удаления “всех дубликатов”. Сначала нужно классифицировать роли.

## Целевая модель ownership

Для этого RF стоит закрепить очень простое правило:
- файловая форма, schema parsing, loader behavior, compatibility normalization — `infrastructure`;
- immutable config models, domain-valid value objects и смысловые ограничения — `domain`;
- сборка конкретных pipeline/service graphs из уже валидированных конфигов — `composition`;
- исходные YAML/JSON schema артефакты — `configs/`.

Если composition знает про normalization details или schema branching, это smell. Если domain зависит от файловой формы конфигов, это тоже smell. Если infrastructure приходится воссоздавать domain-смысл, это сигнал дублирования.

## Порядок выполнения

### Шаг 1. Инвентаризация ролей

Нужно составить карту всех config-related модулей с пометками:
- source of truth;
- parser/loader;
- schema validator;
- compatibility shim;
- domain model;
- composition assembly helper.

Этот шаг обязателен. Без него cleanup превратится в борьбу с похожими именами, а не с responsibilities.

### Шаг 2. Composition cleanup

Самый подозрительный слой здесь — `composition/factories/pipeline`. Composition должен только связывать validated config objects с runtime dependencies. Если в нём живёт формальная config logic, её надо либо опустить в infrastructure, либо поднять в domain в зависимости от смысла. Это лучше делать после `RF-FS-001`, потому что часть composition cycles уже завязана на config wiring.

### Шаг 3. Infrastructure normalization

После прояснения роли composition надо привести `infrastructure/config` и `infrastructure/schemas` к читаемому split:
- loading/parsing;
- schema models;
- migration/legacy normalization;
- mapping to domain config objects.

Нельзя позволять одному модулю держать всё сразу, если это делает его gateway для всех последующих слоёв.

### Шаг 4. Domain cleanup

В `domain/config` и `domain/composite` нужно оставить только то, что действительно выражает бизнес/предметную форму конфигурации. Если там лежит файловой формат или транспортная совместимость, это надо убирать.

## Конкретные проблемные зоны

С высокой вероятностью потребуют внимания:
- `src/bioetl/composition/factories/pipeline/configs.py`
- `src/bioetl/composition/factories/pipeline/config_types.py`
- `src/bioetl/infrastructure/config/*`
- `src/bioetl/infrastructure/schemas/*`
- `src/bioetl/domain/config/*`
- части `src/bioetl/domain/composite/*`, которые дублируют infrastructure-facing semantics

Отдельный риск — повторно открыть legacy config/schema wave. Этого делать не нужно. `RF-FS-004` про ownership и topology, а не про массовую смену contract shape.

## Риски

Риск здесь высокий по двум причинам. Во-первых, config layer касается почти всех pipelines. Во-вторых, boundary drift часто маскируется compatibility logic, и легко сломать рабочий YAML corpus, если сначала двигать код, а потом разбираться, кто чем владеет. Второй риск — смешать этот RF с documentation/config-contract cleanup. Документация должна идти после стабилизации структуры, а не вместо неё. Третий риск — перенести слишком много доменного смысла в infrastructure, потому что там “и так уже есть schema models”.

## Минимизация рисков

- Выполнять этот RF после composition cycle cleanup.
- Сначала зафиксировать role map по всем config-related модулям.
- Не менять YAML corpus без необходимости; сначала стабилизировать ownership в Python-коде.
- Делать migration/legacy helpers отдельным подслоем, а не растворять их в canonical modules.

## Верификация

Обязательный набор:

```bash
./.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/config -q
./.venv/Scripts/python.exe -m pytest tests/architecture/test_config_ci_invariants.py tests/architecture/test_config_strict_keys.py tests/architecture/test_config_golden_master.py -q
```

Параллельно:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

После крупных import rewiring:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_forbidden_imports.py tests/architecture/test_layer_dependencies.py -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## Definition of Done

`RF-FS-004` можно закрывать только если:
- ownership config concerns читается однозначно по слоям;
- composition больше не держит лишнюю config business/normalization logic;
- infrastructure содержит parsing/schema/migration responsibilities, но не подменяет domain;
- domain содержит устойчивые config/value models без файлового шума;
- config-related tests и architecture gates зелёные.

Итоговая цель этого RF — сделать конфигурацию маршрутизируемой и понятной как архитектурный поток: `configs -> infrastructure -> domain -> composition`, без обратных дрейфов и лишних мостов.
