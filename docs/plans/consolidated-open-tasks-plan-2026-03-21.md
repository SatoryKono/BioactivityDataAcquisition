# Consolidated Open Tasks Plan

Дата: 2026-03-21  
Статус: active consolidated plan  
Язык: русский

> Этот документ — internal-published planning surface. Он описывает текущую
> очередь исполнения и sequencing, но не заменяет canonical project guidance в
> `docs/00-project/`, `docs/01-requirements/`, `docs/02-architecture/` и active
> guides under `docs/03-guides/`.

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
- `P0` full final verify after the last waves (`green` on `2026-03-23`,
  refreshed via `RF-011`)
- `P1` config topology closeout (`green` on `2026-03-23`)

Эти темы могут использоваться как historical context, но не как активная
очередь работ.

## Текущий кодовый срез

По текущему репозиторию главный остаточный pressure теперь сидит в одном месте:

1. `topology watchpoints / conservative follow-up`

Текущий size snapshot для закрытых/guarded shared adapter seams:

- `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py` — `221` LOC
- `src/bioetl/infrastructure/adapters/common/base_title_fallback.py` — `254` LOC

Wave 4 guarded decorator facades после последних closeout slices:

- `src/bioetl/infrastructure/adapters/decorators/retry.py` — `274` LOC
- `src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py` — `245` LOC
- `src/bioetl/infrastructure/adapters/http/circuit_breaker.py` — `211` LOC

Config-topology seams после `P1` closeout удерживаются как guarded surfaces:

- `src/bioetl/composition/factories/pipeline/registry_manifest.py` — `21` LOC
- `src/bioetl/infrastructure/config/dq_config_loader.py` — `246` LOC
- `src/bioetl/infrastructure/config/pipeline_config_loader.py` — `142` LOC

Дополнительно остаётся один сознательно сохранённый topology watchpoint:

- `src/bioetl/composition/providers/provider_registry.py`
- `src/bioetl/composition/providers/_default_registry.py`

Это больше не большой provider/datasource SCC; это узкий compatibility seam.

## Активная очередь

### P1. Config topology closeout

Статус: completed on `2026-03-23`.

Цель:

- дочистить ownership story так, чтобы путь читался как
  `configs -> infrastructure -> domain -> composition`
- не допустить превращения `composition` в второй config-owner
- удержать `registry_manifest.py` assembly-only поверхностью

Закрытые поверхности:

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

Закрытые structural slices:

- [2026-03-23] `dq_config_loader.py`: убран локальный `_merge_hierarchy`;
  canonical staged flow теперь удерживается только через
  `dq_config_resolution.run_dq_config_flow(...)`.
- [2026-03-23] `registry_manifest.py`: giant declarative table вынесен в
  private provider-entry modules; canonical manifest остался thin assembly
  facade.
- [2026-03-23] `pipeline_config_loader.py`: private DQ helper wrappers
  схлопнуты в прямые `staticmethod` aliases поверх
  `pipeline_dq_resolution.py`.

Признак завершения:

- ownership story читается без дополнительных compat-исключений;
- `composition` не владеет config normalization logic;
- targeted config tests и architecture guards остаются зелёными.

Следующий active structural track теперь уже `P2`, а не продолжение `P1`.

### P2. Residual adapter hotspot reduction

Статус: completed on `2026-03-23`.

Последний closeout slice:

- [2026-03-23] `common/base_title_fallback.py`: repetitive `_event_*`
  properties схлопнуты в compact property-factory pattern; helper-backed flow
  по-прежнему удерживается в `common/_title_fallback_flow.py`, а seam
  дополнительно закреплён через `tests/architecture/test_wave4_complexity_closeout.py`.

Все provider-bounded cluster starts были закрыты как bounded slices. Shared
adapter seams тоже доведены до helper-backed / guarded baseline, поэтому
`P2` больше не является активной очередью.

Закрытые/guarded `P2` slices:

- [2026-03-23] `cached_bronze_data_source.py`: private wrapper cruft убран;
  canonical helper-layer удерживается через
  `infrastructure/adapters/_cached_bronze_support.py`; unit tests переведены
  на helper-level contract.
- [2026-03-23] `base_title_fallback.py`: shared async flow и utility helpers
  удерживаются через
  `infrastructure/adapters/common/_title_fallback_flow.py`; private utility
  seams больше не являются adapter-owned contract.
- [2026-03-23] `RF-006` closeout: helper-level branch coverage добавлен для
  `cached_bronze` и `title_fallback` flows, а `cached_bronze_data_source.py`
  теперь дополнительно удерживается Wave 4 ratchet-guard'ом как helper-backed
  facade.
- [2026-03-23] `decorators/circuit_breaker.py`: state gate, failure logging,
  manual reset и open-health helpers вынесены в
  `decorators/_circuit_breaker_support.py`; Wave 4 ratchet добавлен в
  `tests/architecture/test_wave4_complexity_closeout.py`.
- [2026-03-23] `http/circuit_breaker.py`: state transition, metric emission,
  retry-after math и error helpers вынесены в
  `http/_circuit_breaker_support.py`; Wave 4 ratchet добавлен в
  `tests/architecture/test_wave4_complexity_closeout.py`.
- [2026-03-23] `RF-007` circuit breaker contract unify: shared typed
  transition/state contract удерживается в
  `infrastructure/adapters/_circuit_breaker_contract.py` (исторический private
  seam, с тех пор promoted в current public path
  `src/bioetl/infrastructure/adapters/circuit_breaker_contract.py`); обе
  breaker реализации опираются на него через support modules, а
  contract-backed ownership закреплён в
  `tests/architecture/test_wave4_complexity_closeout.py`.

Признак завершения:

- shared adapter seams больше не требуют broad rewrite;
- helper-backed surfaces удерживаются targeted tests и architecture ratchets;
- следующий шаг после `P2` — не новая adapter wave, а conservative backlog
  refresh / watchlist review.

### P3. Watchlist, а не активная миграция

Следующие темы пока не являются очередью исполнения:

- class-level compatibility seam между
  `src/bioetl/composition/providers/provider_registry.py`
  и
  `src/bioetl/composition/providers/_default_registry.py`
- дальнейшее физическое сокращение `png/` дерева диаграмм
- broad dead-code cleanup без нового evidence pack

Для них сейчас правильный статус: `watchlist`.

Первый conservative closeout slice:

- [2026-03-23] `provider_registry.py` перестал владеть lazy default-singleton
  state напрямую; default-registry ownership централизован в
  `composition/providers/_default_registry.py`, а `provider_registry.py`
  удерживается как import-stable facade над registry API.
- [2026-03-23] `_default_registry.py` зафиксирован как final private compat
  owner через targeted architecture guard: size budget, запрет на regrowth в
  loading/creation hub и явное удержание lazy singleton seam.
- [2026-03-23] `RF-009` closeout: baseline-aware no-growth ratchet добавлен
  для raw call sites `get_default_provider_registry()` /
  `get_default_provider_registrar()` и для private imports of
  `composition/providers/_default_registry.py`; seam удерживается как
  локальный watchpoint без новой registry migration wave.

### RF-005. Application/Core duplication pressure

Статус: bounded application/core slices completed on `2026-03-23`.

Execution note:

- report-only snapshot зафиксирован в
  `reports/quality/rf005-application-core-duplication-snapshot-2026-03-23.md`
- первым family выбран `application/core/batch_execution`
- shared execution-state/memory contracts централизованы в
  `application/core/batch_execution/_contracts.py`
- `lifecycle.py`, `run_service.py` и `state_service.py` больше не держат
  раздельные локальные копии этих contracts
- regrowth guard удерживается через
  `tests/architecture/test_rf005_application_core_closeout.py`
- после зелёной проверки первого slice вторым bounded family выбран `postrun`
- strict/warning failure policy для postrun теперь централизована в
  `application/core/postrun/_failure_policy.py`, а
  `dq_report_orchestrator.py` и `metadata_version_resolver.py`
  больше не держат раздельные копии этого policy path
- следующим bounded slice выбран `application/core/batch_processing`
- скрытая mixin-based state choreography убрана из
  `application/core/batch_processing_service_mixins.py`
  в явный support module
  `application/core/batch_processing_support.py`
- `BatchProcessingService` сохранил прежний публичный API, но orchestration
  теперь читается через один helper/service seam вместо двух внутренних mixin
- shared runtime failure policy для соседнего `application/core` family
  централизована в `application/core/batch_runtime_failure_policy.py`
- `batch_executor.py`, `batch_execution/run_service.py` и
  `batch_processing_support.py` больше не держат локальные копии runtime
  failure tuples

## Что не делать

- не поднимать заново старые `rf-*`, `rf-fs-*`, `wave-3-*`, `wave-4-*`
  документы как параллельные master queues;
- не смешивать config-topology cleanup с provider-registry migration wave;
- не запускать repo-wide import cleanup без нового evidence;
- не делать broad adapter rewrite вместо bounded-cluster подхода.

## Рекомендуемый порядок

1. `P3` — watchlist review только при появлении нового evidence
2. затем новый snapshot backlog, а не автоматический переход к следующему
   старому dated plan

## Definition Of Done Для Папки `docs/plans`

Папка считается приведённой в порядок, когда:

- в ней остаётся один активный consolidated backlog;
- completed и absorbed execution plans больше не создают видимость живой
  очереди;
- historical context удерживается только там, где он ещё нужен для evidence
  traceability;
- `README.md` показывает реальную, а не историческую структуру планов.
