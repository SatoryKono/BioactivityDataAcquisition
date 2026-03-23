# Consolidated Open Tasks Plan

Дата: 2026-03-21  
Статус: active consolidated plan  
Язык: русский

## Назначение

Этот документ заменяет россыпь dated execution plans, которые уже:

- полностью выполнены;
- были поглощены более поздними refactor waves;
- перестали быть актуальной очередью исполнения после evidence-refresh и
  последних implementation волн.

Ниже фиксируется только то, что действительно остаётся открытым по текущему
коду.

## Что уже не является открытой задачей

Не нужно заново поднимать как отдельные execution plans:

- `RF-01` ... `RF-09`
- documentation drift remediation
- compatibility registry refactor
- diagram publication rationalization
- import/topology Wave 1 (`pipeline factory assembly`)
- import/topology Wave 2 (`datasource/provider cluster`)
- provider-bounded Wave 3 hotspot starts
- Wave 4 retry-decorator cluster start
- `P0` full final verify after the last waves (`green` on `2026-03-23`)

Эти темы могут использоваться как historical context, но не как активная
очередь работ.

## Текущий кодовый срез

По текущему репозиторию главный остаточный pressure сидит в двух местах:

1. `config topology / ownership`
2. `shared adapter hotspots`

Текущий size snapshot для живых residual targets:

- `src/bioetl/composition/factories/pipeline/registry_manifest.py` — `326` LOC
- `src/bioetl/infrastructure/config/dq_config_loader.py` — `280` LOC
- `src/bioetl/infrastructure/config/pipeline_config_loader.py` — `205` LOC
- `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py` — `297` LOC
- `src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py` — `296` LOC
- `src/bioetl/infrastructure/adapters/common/base_title_fallback.py` — `295` LOC
- `src/bioetl/infrastructure/adapters/http/circuit_breaker.py` — `289` LOC

Дополнительно остаётся один сознательно сохранённый topology watchpoint:

- `src/bioetl/composition/providers/provider_registry.py`
- `src/bioetl/composition/providers/_default_registry.py`

Это больше не большой provider/datasource SCC; это узкий compatibility seam.

## Активная очередь

### P0. Полный финальный verify после последних волн

Это не structural refactor, но это единственная обязательная операционная
задача перед закрытием большой серии.

Что сделать:

1. прогнать `pytest tests -q`
2. при необходимости локализовать и закрыть только live regressions
3. после зелёного suite при желании собрать coverage snapshot

Базовый verify bundle:

- `./.venv/Scripts/python.exe -m pytest tests -q`
- `./.venv/Scripts/ruff.exe check src tests`
- `./.venv/Scripts/ruff.exe format --check src tests`
- `./.venv/Scripts/python.exe -m mypy --strict src/bioetl`
- `./.venv/Scripts/python.exe scripts/qa/generate_architecture_dependency_map.py --check`
- `./.venv/Scripts/python.exe scripts/qa/generate_compatibility_facade_snapshot.py --check`

### P1. Config topology closeout

Это главный оставшийся structural track.

Цель:

- дочистить ownership story так, чтобы путь читался как
  `configs -> infrastructure -> domain -> composition`
- не допустить превращения `composition` в второй config-owner
- удержать `registry_manifest.py` assembly-only поверхностью

Приоритетные поверхности:

- `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `src/bioetl/infrastructure/config/pipeline_config_loader.py`
- `src/bioetl/infrastructure/config/dq_config_loader.py`

Что делать:

1. зафиксировать `registry_manifest.py` как assembly-manifest и не допускать
   роста config semantics внутри него;
2. уточнить разделение `read / normalize / validate / map` внутри
   `infrastructure/config`;
3. не открывать новую broad migration в `domain/config`, если evidence не
   показывает реальный drift.
4. удерживать ownership story через architecture ratchet в
   `tests/architecture/test_p1_config_topology_closeout.py`.

Первый закрытый structural slice в этом track:

- [2026-03-23] `dq_config_loader.py`: убран локальный `_merge_hierarchy`;
  canonical staged flow теперь удерживается только через
  `dq_config_resolution.run_dq_config_flow(...)`.
- [2026-03-23] `registry_manifest.py`: giant declarative table вынесен в
  private provider-entry modules; canonical manifest остался thin assembly
  facade.

Признак завершения:

- ownership story читается без дополнительных compat-исключений;
- `composition` не владеет config normalization logic;
- targeted config tests и architecture guards остаются зелёными.

### P2. Residual adapter hotspot reduction

Все provider-bounded cluster starts уже реализованы как bounded slices. Теперь
имеет смысл работать только по shared seams, и строго по одному кластеру за
раз.

Рекомендуемый порядок:

1. `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py`
2. `src/bioetl/infrastructure/adapters/common/base_title_fallback.py`
3. `src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py`
4. `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`

Правила выполнения:

- брать только один hotspot за волну;
- сначала проверять bounded test net;
- держать package-root import surfaces стабильными;
- после каждого slice обновлять dependency docs только если граф реально
  изменился.

### P3. Watchlist, а не активная миграция

Следующие темы пока не являются очередью исполнения:

- class-level compatibility seam между
  `src/bioetl/composition/providers/provider_registry.py`
  и
  `src/bioetl/composition/providers/_default_registry.py`
- дальнейшее физическое сокращение `png/` дерева диаграмм
- broad dead-code cleanup без нового evidence pack

Для них сейчас правильный статус: `watchlist`.

## Что не делать

- не поднимать заново старые `rf-*`, `rf-fs-*`, `wave-3-*`, `wave-4-*`
  документы как параллельные master queues;
- не смешивать config-topology cleanup с provider-registry migration wave;
- не запускать repo-wide import cleanup без нового evidence;
- не делать broad adapter rewrite вместо bounded-cluster подхода.

## Рекомендуемый порядок

1. `P1` — config topology closeout
2. `P2` — один shared adapter hotspot
3. затем новый snapshot backlog, а не автоматический переход к следующему
   старому dated plan

## Definition Of Done Для Папки `docs/plans`

Папка считается приведённой в порядок, когда:

- в ней остаётся один активный consolidated backlog;
- completed и absorbed execution plans больше не создают видимость живой
  очереди;
- historical context удерживается только там, где он ещё нужен для evidence
  traceability;
- `README.md` показывает реальную, а не историческую структуру планов.
