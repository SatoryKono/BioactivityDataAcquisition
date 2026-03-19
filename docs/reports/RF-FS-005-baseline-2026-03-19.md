# RF-FS-005 Baseline Plan

**Дата:** 2026-03-19  
**Тема:** Довести split semantic hotspots и устранить перегруженные/нечестно названные модули  
**Связанные находки:** `FS-008`, `FS-009`  
**Основной scope:** `src/bioetl/application/pipelines/chembl/_pipelines.py`, `src/bioetl/application/services/cli_run_orchestration_service.py`, а также связанные imports/re-exports в CLI

## Цель

`RF-FS-005` — это намеренно локальная structural wave. В отличие от cycle cleanup или config topology, здесь не нужно перепроектировать слой целиком. Задача состоит в том, чтобы убрать два самых очевидных semantic hotspot-а, где имя модуля, число сущностей и фактическая ответственность больше не совпадают. Первый — `src/bioetl/application/pipelines/chembl/_pipelines.py`, где в одном underscored файле живёт четырнадцать public pipeline classes. Второй — `src/bioetl/application/services/cli_run_orchestration_service.py`, который исторически смешивал contracts, DTO/models и orchestration service. По baseline эта задача уже частично начата: models/contracts вынесены в отдельные модули, а CLI helpers переключены на новые canonical imports. Значит план для `RF-FS-005` должен исходить из текущего состояния, а не из старой картины “ничего ещё не сделано”.

## Текущее состояние

На момент baseline:
- `cli_run_orchestration_service.py` уже стал заметно тоньше и опирается на новые `cli_run_orchestration_models.py` и `cli_run_orchestration_contracts.py`;
- связанные run-related helpers уже переведены на canonical imports;
- целевые CLI tests после этого split зелёные;
- `_pipelines.py` в ChEMBL-подпакете всё ещё остаётся концентрацией pipeline class declarations.

Это значит, что `RF-FS-005` делится на два неравных подэтапа: `cli` cleanup closeout и `chembl pipeline hotspot` decomposition.

## Подзадача 1. CLI orchestration closeout

Здесь задача не в новом рефакторинге, а в доведении уже начатого split до консистентной формы. Нужно проверить три вещи:
- все внутренние импорты используют canonical `models`/`contracts` модули, а не старый service-модуль, если только re-export не нужен для совместимости;
- сам service-модуль содержит orchestration, а не данные, протоколы и вспомогательные типы;
- tests и import seams не завязаны на случайные legacy paths, которые можно удалить в ближайшей волне.

Важно не переусердствовать. Если re-export path ещё нужен тестам или внешнему import surface, его лучше оставить до отдельной cleanup-wave, чем ломать совместимость в этой задаче.

## Подзадача 2. ChEMBL pipeline hotspot

`src/bioetl/application/pipelines/chembl/_pipelines.py` — это более чистый structural smell. Тут возможны два корректных решения. Первое: разнести pipeline classes по отдельным модулям или логическим группам. Второе: оставить один registry-oriented модуль, но сделать его честно named и декларативным, а не контейнером для четырнадцати public classes. Выбор зависит от того, сколько реальной логики находится внутри этих классов и насколько они похожи. Если они в основном тонкие декларации поверх уже существующих transformer modules, registry-oriented подход может быть дешевле и читабельнее. Если же классы различаются существенно, лучше раскладывать их по owner-модулям.

Здесь нельзя делать cosmetic rename without payoff. Конечная форма должна уменьшить semantic surprise: пользователь пакета должен по имени файла понимать, что внутри находится registry/assembly, а не случайный набор pipelines.

## Конкретные изменения

Ожидаемые файлы внимания:
- `src/bioetl/application/services/cli_run_orchestration_service.py`
- `src/bioetl/application/services/cli_run_orchestration_models.py`
- `src/bioetl/application/services/cli_run_orchestration_contracts.py`
- `src/bioetl/interfaces/cli/commands/run_command_policy.py`
- `src/bioetl/interfaces/cli/commands/run_runtime_helpers.py`
- `src/bioetl/interfaces/cli/commands/run_result_flow_helpers.py`
- `src/bioetl/application/pipelines/chembl/_pipelines.py`
- `src/bioetl/application/pipelines/chembl/__init__.py`
- любые registration/import paths, которые экспортируют ChEMBL pipeline classes

## Риски

По CLI-ряби риск уже низкий или ближе к среднему: основная опасность в том, что тесты и внешние import paths ещё завязаны на service-модуль как на historical umbrella. По ChEMBL-пакету риск средний. Ломать pipeline registration проще, чем кажется: даже если тесты зелёные, можно случайно изменить import-time side effects или порядок регистрации. Второй риск — превратить `_pipelines.py` в десяток микромодулей и только ухудшить навигацию. Третий риск — совместить structural split с functional changes в pipeline class behavior.

## Минимизация рисков

- CLI closeout делать отдельно от ChEMBL decomposition.
- В `cli` сначала стабилизировать canonical import surface, а cleanup re-exports вынести в отдельное решение, если они ещё нужны.
- Для ChEMBL сначала выбрать target shape: per-pipeline files или registry module. Не начинать разнос без этой развилки.
- Сохранить registration/import contract в неизменном виде на уровне внешнего API.

## Верификация

Для CLI-подзадачи:

```bash
cmd.exe /c "cd /d E:\\g-drive\\05_AI\\github\\BioactivityDataAcquisition2 && .venv\\Scripts\\python.exe -m pytest tests/unit/interfaces/cli/commands/test_run_command_policy.py tests/unit/interfaces/cli/test_cli_commands.py -q"
```

Для ChEMBL:

```bash
./.venv/Scripts/python.exe -m pytest tests/unit/application/pipelines/chembl -q
```

Параллельно после каждого батча:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

После import rewiring:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_forbidden_imports.py tests/architecture/test_layer_dependencies.py -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## Definition of Done

`RF-FS-005` закрыт, если:
- `cli_run_orchestration_service.py` окончательно выполняет роль service-модуля, а не mixed container;
- canonical models/contracts живут в собственных owner-модулях;
- `_pipelines.py` больше не выглядит как misnamed dumping ground для четырнадцати public classes;
- внешние registration/import contracts не сломаны;
- целевые CLI и ChEMBL suites зелёные.

Итоговая цель этого RF — убрать два самых очевидных semantic hotspot-а дешёвой, локальной и верифицируемой волной, не затрагивая остальные слои без необходимости.
