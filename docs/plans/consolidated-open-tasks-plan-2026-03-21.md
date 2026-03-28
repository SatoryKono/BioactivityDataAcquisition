# Consolidated Open Tasks Plan

Дата: 2026-03-21  
Статус: active consolidated plan  
Язык: русский

> Этот документ — repo-only planning surface. Он описывает текущую
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

По текущему репозиторию активная очередь больше не выглядит как broad refactor
program. После closeout `RF-024` и завершения `RF-023` follow-up остаточный
pressure теперь удерживается в двух режимах:

1. `watch-mode governance refresh` для hotspot families и bounded ratchets
2. `topology watchpoints / conservative follow-up`

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

Дополнительно уже landed и удерживаются guardrails, которые раньше выглядели
как "будущие задачи", но по текущему коду уже являются частью baseline:

- `RF-023`: `configs/quality/debt_scorecard.yaml` уже держит report-only
  family baseline для `application/core`,
  `composition/bootstrap/runtime` и
  `composition/factories/pipeline`;
- `RF-023`: `make qa-hotspot-report` уже публикует repeatable hotspot snapshot
  и append-only history artifact `reports/quality/hotspot-duplication-history.jsonl`;
- `RF-024`: curated compatibility inventory уже ведётся через
  `configs/quality/compatibility_facade_inventory.yaml` и
  `docs/02-architecture/07-compatibility-facade-inventory.md`;
- `RF-024`: transition debt ledger сейчас равен `0`, а remaining pipeline
  shims удерживаются как measured-only surfaces под freeze guards.
- `RF-024`: retained CLI entrypoint ledger теперь покрывает
  `run*`, `health`, `quarantine`, `maintenance`, `archive`, `cleanup`,
  `vacuum`, а helper-level CLI aliases и shared `execution_policy.py`
  уже удерживаются как measured-only / no-new-first-party-imports seams.

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

### RF-023. Hotspot family governance closeout

Статус: completed on `2026-03-24`.

Что зафиксировано как closed baseline:

- `configs/quality/debt_scorecard.yaml` держит repo-level `report-only`
  baseline и active family-level duplication-only ratchets для
  `application/core`, `composition/bootstrap/runtime` и
  `composition/factories/pipeline`;
- `Makefile` публикует canonical command `qa-hotspot-report`;
- `reports/quality/hotspot-duplication-baseline.md` и
  `reports/quality/hotspot-duplication-history.jsonl` уже фиксируют два
  confirming clean snapshots с `0` duplication clusters во всех tracked
  families;
- `docs/reports/evidence/governance-signals/SUMMARY.md` синхронизирован с
  этим posture и описывает active bounded ratchets как non-regression control,
  а не как открытый refactor queue.

Что это значит для живой очереди:

- `RF-023` больше не является active backlog line;
- tracked families теперь удерживаются в watch mode:
  repo-level governance остаётся `report-only`,
  duplication — под bounded family ratchets,
  file-growth и fan-in — в watch-only posture;
- новые hotspot slices должны открываться только при новом evidence или
  regressions, а не как автоматическое продолжение уже закрытой wave.

Чего не делать:

- не включать repo-wide duplication gate;
- не трактовать active family ratchets как повод открыть новую broad cleanup
  program;
- не смешивать hotspot governance с package-move инициативой.

Признак сохранения closeout:

- history artifact продолжает пополняться только после intentional slices или
  reviewed governance refresh;
- tracked families удерживают `0` duplication clusters;
- decision notes и top-level summaries остаются синхронизированы с bounded
  ratchet posture.

### RF-024. Compatibility-surface governance closeout

Статус: completed on `2026-03-24`.

Что зафиксировано как closed baseline:

- `transition_debt` в
  `configs/quality/compatibility_facade_inventory.yaml` удерживается на `0`;
- curated retained-entrypoint ledger покрывает CLI seams
  `run.py`, `run_all.py`, `run_composite.py`, `health.py`,
  `quarantine.py`, `maintenance.py`, `archive.py`, `cleanup.py`,
  `vacuum.py`;
- helper-level CLI aliases и shared `execution_policy.py` сведены к
  measured-only / no-new-first-party-imports posture под freeze guards;
- `pipeline.config_resolution`, `pipeline.configs`,
  `pipeline.creation_api` и `services.creation_api` удерживаются как
  controlled measured-only / deprecated seams без broad migration wave;
- compatibility inventory, generated snapshot, boundary tests и
  architecture freeze guards синхронизированы с этим baseline.

Что это значит для живой очереди:

- `RF-024` больше не является active backlog line;
- новые compatibility decisions теперь должны открываться только как
  отдельные bounded follow-up slices при появлении нового evidence;
- measured-only review продолжается как routine governance, а не как
  самостоятельная refactor wave.

Чего не делать:

- не переоткрывать `RF-024` под broad rename/package-consistency волну;
- не превращать measured-only modules в curated rows без явного governance
  повода;
- не удалять retained entrypoints, пока inventory, tests и public import paths
  не подтверждают readiness.

Признак сохранения closeout:

- transition debt остаётся `0`;
- measured-only allowlist не растёт без явного approval/update в inventory;
- новые compatibility changes оформляются как отдельные bounded decisions, а
  не как возврат к repo-wide cleanup wave.

## Что не делать

- не поднимать заново старые `rf-*`, `rf-fs-*`, `wave-3-*`, `wave-4-*`
  документы как параллельные master queues;
- не смешивать config-topology cleanup с provider-registry migration wave;
- не запускать repo-wide import cleanup без нового evidence;
- не делать broad adapter rewrite вместо bounded-cluster подхода;
- не трактовать `RF-023` как повод для нового глобального duplication gate;
- не трактовать закрытый `RF-024` как повод для массовой rename/move волны.

## Рекомендуемый порядок

1. `watch-mode governance refresh` — обновлять hotspot history и summaries
   только после intentional slices или reviewed drift
2. `P3` — watchlist review только при появлении нового evidence
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
