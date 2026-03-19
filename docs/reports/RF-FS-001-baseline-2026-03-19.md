# RF-FS-001 Baseline Plan

**Дата:** 2026-03-19  
**Тема:** Разорвать циклы импортов в composition и соседних runtime-кластерах  
**Связанные находки:** `FS-004`, `FS-005`, `FS-006`  
**Основной scope:** `src/bioetl/composition/providers/`, `src/bioetl/composition/factories/datasource/`, `src/bioetl/composition/factories/pipeline/`, `src/bioetl/composition/factories/services/`, а также малые циклы в `application` и `infrastructure`

## Актуализация на 2026-03-19 16:58

По существу baseline для `RF-FS-001` не изменился. Последние test-ownership waves (`Wave 3B` и `Wave 3C`) улучшили диагностируемость `application/services`, но не уменьшили сам composition/runtime cycle debt. Этот RF по-прежнему остаётся архитектурным блокером перед полномасштабным `RF-FS-004` и перед широкими package-split waves из `RF-FS-002`.

## Цель

Цель `RF-FS-001` не в том, чтобы механически переписать импорты до исчезновения циклов на графе зависимостей. Настоящая цель другая: восстановить односторонний поток зависимостей в bootstrap и runtime-сборке проекта так, чтобы composition снова выглядел как слой wiring, а не как самозамкнутый набор взаимно импортирующих factory-модулей. По текущему baseline это самый опасный архитектурный долг в файловой структуре: в composition обнаружен крупный цикл из девяти модулей вокруг `providers` и `datasource factory`, отдельный цикл из семи модулей вокруг `pipeline/services factory`, плюс несколько малых циклов в runtime hot spots. Это уже не косметика. Такие циклы затрудняют перенос кода, скрывают ownership, делают import-time behavior менее предсказуемым и мешают адресно тестировать factory/registry слой.

## Текущее состояние

На старте нужно считать подтверждёнными три проблемы. Первая: вокруг `src/bioetl/composition/providers/provider_registry.py`, `registration.py`, `registration_bio.py`, `registration_biblio.py`, `factory_loader.py`, `loader.py`, `_config_helpers.py`, а также `src/bioetl/composition/factories/datasource/data_source_factory.py` и `http_client.py` уже есть большой SCC. Вторая: вокруг `src/bioetl/composition/factories/pipeline/creation_api.py`, `_creation_wiring.py`, `assembler.py`, `factory_method_helpers.py`, `contract_validator.py` и `src/bioetl/composition/factories/services/creation_api.py`, `bundle.py` есть отдельный SCC. Третья: вне composition есть малые циклы между `batch_transformer_streaming` и `batch_transformer`, между `pipeline_run_context_service` и `pipeline_runner_service`, а также между `health_tracker` и `health_monitor`.

Важно не путать symptom и cause. Причина не только в том, что импорты “плохо расставлены”. По текущей структуре часть модулей одновременно содержит:
- публичный construction API;
- internal assembly helpers;
- registration state;
- config normalization;
- runtime bundle creation.

Пока эти роли живут вперемешку, циклы будут возвращаться даже после локальных fixes.

## Стратегия

`RF-FS-001` лучше выполнять тремя батчами, а не одной волной.

### Батч 1. Provider/DataSource cycle

Первый подэтап должен быть сфокусирован только на `composition/providers` и `composition/factories/datasource`. Здесь нужно провести жёсткую границу между тремя типами модулей:
- registry API и registration state;
- provider descriptors / config DTO / metadata;
- datasource construction helpers.

Правильная конечная форма такая: registry знает только о registration contract и provider descriptors; datasource factory знает только о публичном registry API и leaf-конструкторах; helper-модули не импортируют обратно registry internals. Это значит, что часть helper-кода, вероятно, придётся вынести в leaf modules, которые никто не импортирует “сверху назад”. Особенно подозрительны `_config_helpers.py` и `factory_loader.py`: такие модули часто становятся мостом между тем, что должно быть раздельным.

### Батч 2. Pipeline/Services cycle

Второй подэтап должен быть ограничен `composition/factories/pipeline` и `composition/factories/services`. Здесь задача в том, чтобы сделать один направленный construction flow. Практически это означает:
- один внешний creation API;
- leaf assembler modules ниже этого API;
- validation/helpers как подчинённые зависимости, а не как равноправные центры импорта;
- bundle-модули не должны тянуть creation API обратно.

Если этого не сделать, package будет продолжать расти как “factory mesh”, а не как иерархия.

### Батч 3. Малые циклы

Третий подэтап должен быть коротким и адресным. Малые SCC в application и infrastructure почти всегда чинятся выделением моделей/протоколов/utility seam в отдельный leaf module. Эти пары нельзя тянуть в один большой refactor с composition: там другой риск-профиль и другой verify-set.

## Конкретные изменения по модулям

Ожидаемые точки вмешательства:
- `src/bioetl/composition/providers/provider_registry.py`
- `src/bioetl/composition/providers/registration.py`
- `src/bioetl/composition/providers/registration_bio.py`
- `src/bioetl/composition/providers/registration_biblio.py`
- `src/bioetl/composition/providers/factory_loader.py`
- `src/bioetl/composition/providers/loader.py`
- `src/bioetl/composition/providers/_config_helpers.py`
- `src/bioetl/composition/factories/datasource/data_source_factory.py`
- `src/bioetl/composition/factories/datasource/http_client.py`
- `src/bioetl/composition/factories/pipeline/creation_api.py`
- `src/bioetl/composition/factories/pipeline/_creation_wiring.py`
- `src/bioetl/composition/factories/pipeline/assembler.py`
- `src/bioetl/composition/factories/pipeline/factory_method_helpers.py`
- `src/bioetl/composition/factories/pipeline/contract_validator.py`
- `src/bioetl/composition/factories/services/creation_api.py`
- `src/bioetl/composition/factories/services/bundle.py`

Здесь нельзя сразу “раскидать всё по новым папкам”. На первом проходе важнее восстановить направление зависимостей, чем менять каталог.

## Риски

Главный риск высокий, потому что composition — это центральный wiring layer. Ошибка здесь редко проявляется как простой unit failure; чаще ломается bootstrap конкретного pipeline, lazy registration или construction path, который покрыт несимметрично. Второй риск — совместить в одном батче и cycle fix, и API cleanup, и package move. Это создаст лишний churn. Третий риск — перепутать решение цикла с service locator: если слишком многое спрятать в registry/bundle, граф импорта станет чище, но архитектура деградирует.

## Минимизация рисков

- Делить `RF-FS-001` на три батча с отдельной верификацией.
- Не менять публичные factory entrypoints в том же батче, где рвётся цикл, без необходимости.
- Сначала выделять leaf types/helpers, потом переподключать imports.
- Не переносить код между слоями; задача только про направленность зависимостей и структуру composition/runtime.

## Верификация

После каждого батча:

```bash
./.venv/Scripts/python.exe -m pytest tests/unit/composition/providers tests/unit/composition/factories/datasource tests/unit/composition/factories/pipeline tests/unit/composition/factories/services -q
```

Параллельно:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

После импортных изменений дополнительно:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_forbidden_imports.py tests/architecture/test_layer_dependencies.py -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## Definition of Done

`RF-FS-001` можно считать закрытым только если выполнены все условия:
- крупный SCC в `composition/providers` и `composition/factories/datasource` исчез;
- SCC в `composition/factories/pipeline` и `composition/factories/services` исчез;
- три малых цикла вне composition тоже устранены;
- composition по-прежнему остаётся wiring-слоем без дрейфа в application/domain;
- unit, architecture и `mypy` проверки зелёные;
- не появилось новых compatibility shims, которые только маскируют цикл вместо устранения причины.

Итоговая цель этого RF: не “красивый import graph”, а предсказуемая, односторонняя и тестируемая композиция runtime-сборки.
