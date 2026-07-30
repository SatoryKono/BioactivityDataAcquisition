______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-19'

______________________________________________________________________

# Testing Guide

Этот документ описывает стратегию и инструменты тестирования в проекте BioETL.

## 1. Стек Тестирования

- **Фреймворк**: `pytest`
- **Покрытие**: `pytest-cov`
- **Запись HTTP**: `VCR.py`
- **Property-based**: `Hypothesis`
- **Mocking**: In-memory fakes предпочтительны, `unittest.mock.MagicMock` допустим

Source of truth для тестовой governance:

- [ADR-042](../02-architecture/decisions/ADR-042-testing-strategy-matrix.md)
- `configs/quality/test_matrix.yaml`
- `configs/quality/test_governance_audit.yaml`
- `configs/quality/integration_vcr_policy.yaml`

Canonical named pytest lanes are defined in
`configs/quality/test_matrix.yaml` under `test_lanes.lanes`. Test-health tooling
must use these `suite_name` values for comparable local and CI runs:

- `smoke`: minimal dependency/import smoke lane;
- `unit-fast`: `tests/unit/`, excluding `repo_backed`, `slow`, `benchmark`,
  and `memory`;
- `repo-backed-unit`: `tests/unit/` repo-file-backed contract checks that are
  explicitly isolated from `unit-fast`;
- `unit-parallel-safe`: deterministic unit/domain/application slice routed
  through the maintained shard inventory and excluding `slow`, `serial`,
  `benchmark`, `repo_backed`, and `memory`;
- `integration-replay`: `tests/integration/` in VCR replay-only mode;
- `security`: dedicated security and secret-hygiene lane;
- `contracts`: schema, contract, and snapshot tests;
- `architecture`: layer boundary, contract, and governance checks;
- `architecture-fast-boundary`: fast local architecture boundary lane;
- `architecture-slow-governance`: slow repo-wide architecture governance lane;
- `architecture-read-only-audit`: diagnostic check-only architecture evidence
  lane that bypasses dev-wrapper pretest sync and fails if tracked governance
  surfaces mutate;
- `e2e`: dedicated slow end-to-end lane;
- `e2e-smoke`: minimal end-to-end smoke lane;
- `e2e-nightly-full`: comprehensive nightly end-to-end lane;
- `memory`: dedicated Neo4j project-memory and MCP lane, outside coverage (not a test directory, but a lane selector);
- `performance`: benchmark-backed hotspot/performance-budget lane;
- `coverage-verify`: the only lane that enforces the repo-wide coverage gate.

## Testing Topology Crosswalk

This matrix links the live `tests/**` topology to the canonical lane model and
governance artifacts.

| Test family | Primary purpose | Canonical lane(s) | Main artifact / governance anchor |
| --- | --- | --- | --- |
| `tests/architecture/**` | Architecture boundaries, governance budgets, generated artifact drift, docs/code sync | `architecture`, `architecture-fast-boundary`, `architecture-slow-governance`, `architecture-read-only-audit` | `configs/quality/test_matrix.yaml`, `configs/quality/test_governance_audit.yaml` |
| `tests/contract/**` | Live/provider contracts, schema snapshots, provider-facing compatibility | `contracts` | provider contract fixtures, schema snapshots, live-network policy |
| `tests/integration/**` | Replay-backed integration between adapters, pipelines, configs, runtime, and CI artifacts | `integration-replay` | VCR policy, metadata inventory, replay determinism |
| `tests/e2e/**` | Slow end-to-end pipeline and scenario flows | `e2e` | end-to-end scenario coverage and operator-facing behavior |
| `tests/unit/**` | Isolated deterministic behavior in domain/application/infrastructure/interfaces | `unit-fast`, `repo-backed-unit`, `unit-parallel-safe` | fast feedback, repo-backed fixtures, shard-safe unit coverage |
| `tests/smoke/**` | Minimal startup/import confidence | `smoke` | bootstrap/import survivability |
| `tests/performance/**`, `tests/benchmarks/**` | Performance budgets and hotspot regressions | `performance` | benchmark-backed budget checks |
| `tests/security/**` | Secret hygiene, security regressions, policy enforcement | `security` | security-focused policy checks |
| `tests/fixtures/golden/**` plus golden-backed tests | Frozen compatibility bundles and deterministic output baselines | usually exercised via `contracts`, `integration-replay`, or targeted unit/integration selectors | golden registries, snapshots, bounded output bundles |

Supporting top-level test directories that are part of the live tree but do not
map 1:1 to a canonical lane:

| Directory | Role in the live tree | Typical consumer |
| --- | --- | --- |
| `tests/fakes/**` | reusable in-memory doubles and helper test assets | unit/integration tests |
| `tests/fixtures/**` | shared fixture payloads, including VCR/golden support inputs | contract, integration, repo-backed unit |
| `tests/golden/**` | standalone golden payload bundles referenced by tests outside `tests/fixtures/golden/**` | contracts, integration, targeted regression tests |
| `tests/helpers/**` | test helper APIs and process wrappers | all lanes via imports |
| `tests/infrastructure/**` | infra-adjacent behavior that stays separate from `tests/unit/**` and `tests/integration/**` | targeted infra validation |
| `tests/snapshots/**` | snapshot artifacts and snapshot-backed assertions | contracts, repo-backed unit |
| `tests/testing_support/**` | repo-backed testing utilities and meta-test support code | governance, memory, repo-backed unit |

Ignore `tests/__pycache__/` when reasoning about topology; it is a local Python
cache, not a governed test family.

Interpretation rules:

- A directory family and a lane are related but not identical concepts.
- Wrapper shortcuts such as `unit`, `arch`, or `integration` are local UX
  aliases, not the canonical governance identifiers.
- Comparable test-health evidence must preserve the named lane from
  `configs/quality/test_matrix.yaml`.

Hotspot refactor readiness is additionally governed by the committed module
coverage inventory. `configs/quality/debt_scorecard.yaml` section
`hotspot_family_coverage_thresholds` is the authoritative module-level gate for
hotspot families, and `tests/architecture/test_module_coverage_inventory.py`
fails if those thresholds drift from
`reports/quality/module-coverage-inventory.json`.

Architecture runs are additionally decomposed in the sharded runner into:

- `S7-architecture-fast-boundary`
- `S7-architecture-slow-governance`

Large local runs should use the maintained sharded runner rather than invoking
pytest directly:

```powershell
$env:PYTHONPATH="src"
BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded -- -vv --cov-report=term-missing
```

When coverage stays enabled, the sharded runner now saves combined artifacts to
`reports/coverage/coverage.xml` and `reports/coverage/htmlcov/index.html`.
Mounted WSL checkouts keep raw per-shard coverage files under `/tmp/...` when
`BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1` (or `--force-mounted-coverage`) is
used, so coverage reports stay stable while final artifacts remain under
`reports/coverage/`.

The same execution contract is represented in `test_lanes.execution_defaults`;
future test-health tooling should preserve the logical `suite_name` while
recording sharded runner details separately. The canonical shard membership and
ignore/deselect inventory for `run_pytest_sharded.sh` lives in
`configs/quality/pytest_shards.yaml`.
Local architecture runs should prefer the explicit
`architecture-fast-boundary` lane for fast feedback and the
`architecture-slow-governance` lane for full audit/governance checks. The shard
aliases behind those lanes are `S7-architecture-fast-boundary` and
`S7-architecture-slow-governance`; prefer them over older implicit shard names
when calling the sharded runner directly. On mixed Windows + WSL mounted
checkouts, do not treat root-wide filesystem scans as the first diagnostic path:
use the named lanes or targeted files, prefer git-index-backed governance helpers
for architecture inventories, and report WSL startup/filesystem timeouts as
environment-limited validation rather than weakening assertions.

For read-only architecture evidence collection, prefer:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m scripts.engineering.qa run-architecture-audit-read-only
```

This diagnostic lane runs import-linter, the runtime SCC guard, module coverage
inventory drift, hotspot-family baseline, remote-main debt baseline, and
debt-governance gates in check-only mode. It does not replace the normal
developer wrappers or CI lanes; its purpose is audit evidence collection on a
dirty or mounted checkout where `scripts/engineering/dev/run_pytest.sh` pretest
sync could update generated artifacts. The command compares tracked status for
`.github`, `configs/quality`, `docs`, `reports/quality`, `scripts`,
`src/bioetl`, and `tests` before and after execution and fails if those surfaces
change.

Marker-only commands such as `pytest -m unit` are not canonical lanes and must
not be compared as if they were `unit-fast`, `unit-parallel-safe`, or
`coverage-verify`. Comparable test-health evidence must preserve the
`suite_name` from `configs/quality/test_matrix.yaml`; raw marker/path commands
are acceptable only as local diagnostics.

Developer wrappers such as `scripts/engineering/dev/run_tests.py`,
`python -m scripts.engineering.dev run-tests`, and
`scripts/engineering/dev/run_tests.sh` are convenience entry points for local
feedback. Treat their command aliases (`unit`, `arch`, `integration`, `changed`,
and similar) as local UX shortcuts unless a command explicitly records one of
the `test_lanes.lanes[*].suite_name` values from `configs/quality/test_matrix.yaml`.
Do not use wrapper command names as comparable CI/local telemetry identifiers.

The QA entrypoint can record named lane runs as JUnit XML plus JSON summaries:

```bash
python -m scripts.engineering.qa run-tests --suite unit-fast --skip-preflight -- --no-cov
python -m scripts.engineering.qa run-tests --suite unit-parallel-safe --skip-preflight -- --no-cov
python -m scripts.engineering.qa summarize-junit --suite unit-fast --junit-glob 'reports/test-telemetry/*.xml'
python -m scripts.engineering.qa test-health --last 30 --markdown-out reports/quality/test-runs/rollup.md
python -m scripts.engineering.qa test-health --suite coverage-verify --run-id coverage-verify-local --junit-glob 'reports/quality/test-runs/junit/*.xml' --last 30 --markdown-out reports/quality/test-runs/rollup.md
```

`reports/quality/test-runs/rollup.md` is historical evidence only. Current
merge-blocking status comes from live CI plus the `coverage-verify` hard gate,
while the committed baseline snapshot lives in
`configs/quality/test_telemetry_baseline.yaml` and
`docs/05-engineering/test-telemetry-baseline.md`.

Before using a local checkout as source evidence for broad test audits, run the
reproducibility preflight and static governance budget report:

```bash
python -m scripts.engineering.qa.check_test_audit_preflight --strict
python -m scripts.engineering.qa check-vcr-replay-preflight --strict
python -m scripts.engineering.qa.report_test_governance_audit --check
```

`check_test_audit_preflight --strict` treats missing or unhealthy `git-lfs`,
failed or timed-out `git status`, dirty tracked/untracked VCR cassette paths,
unresolved git-lfs pointer files under `tests/fixtures/vcr/`, missing telemetry
baseline, or a telemetry baseline without `Actual coverage:` as blockers for
main-branch audit claims.
When `git-lfs` is missing, the preflight skips repository-status porcelain so
the primary blocker remains the actionable `missing_git_lfs` diagnosis instead
of an opaque `git-lfs filter-process` failure or a timeout in a partially
hydrated checkout. Normal project Git commands still require `git-lfs` to be
installed in the active shell.
`check-vcr-replay-preflight --strict` is the faster replay-lane gate for long
VCR-backed integration/e2e runs. It reports exact unresolved cassette paths,
flags replay-critical Git LFS pointers before pytest setup, performs cheap VCR
metadata-catalog and sanitizer checks, and uses `git lfs pull` as the local
remediation path.
Refresh the committed test-governance artifacts after changing test sources:

```bash
python -m scripts.engineering.qa.refresh_test_governance_baseline
```

The entry point is
`scripts/engineering/qa/refresh_test_governance_baseline.py`.

`report_test_governance_audit --check` enforces the current ratcheting
budgets for assert-less candidates, duplicate test names, compatibility/legacy
surface, marker/path drift, and deterministic-time/UUID call sites tracked in
`configs/quality/test_governance_audit.yaml`.

Test function names are globally governed, not only file-local. New and renamed
tests must use descriptive, globally unique node IDs in the form
`test_<subject>__<condition>__<expected_behavior>`. Include provider, entity,
value-object, command, or service context in `<subject>` so the pytest node ID is
searchable without opening the file. Avoid generic names such as
`test_default_values`, `test_immutability`, `test_hash_consistency`,
`test_valid_creation`, and `test_none_input` unless the name is already globally
unique and retained only as historical compatibility during a rename batch.
`reports/quality/test-governance-current.json` is the canonical test-audit
baseline. Its `total_test_files` value means `tests/**/test_*.py` files matching
`pyproject.toml -> tool.pytest.ini_options.python_files`; the broader
`test_file_inventory.test_python_file_count` field tracks all Python files under
`tests/`. The repo-backed unit lane is intentionally non-zero and is reported in
`repo_backed_unit_inventory`; those tests live under `tests/unit/repo_backed/`
and run through `repo-backed-unit`, not `unit-fast`.

Duplicate test-name inventory is embedded in
`reports/quality/test-governance-current.json`. The optional
`--duplicate-name-inventory-out <path>` diagnostic may write a throwaway local
inventory, but the repository does not commit a separate
`test-duplicate-name-inventory.json` baseline. The same collector publishes the
canonical exact-byte fixture duplication inventory at
`reports/quality/test-fixture-asset-duplication.json`; similarly named historical
fixture-duplication reports are not current merge-blocking gates. This keeps VCR
cassettes, golden JSON, and other tracked fixture payloads visible even though
`jscpd` does not scan those artifact classes directly.

The tracked flaky-test review is generated from
`configs/quality/flaky_test_inventory.yaml` and the current
`reports/quality/test-governance-current.json` fingerprint. Regenerate it with
`python -m scripts.engineering.qa report-flaky-test-burndown-review` and verify
it with `--check`. The curated inventory records reviewed intermittent failures;
static test-governance evidence supplies source identity and suite size, but does
not replace repeated-run CI telemetry for discovering flakiness.

The blocking `flaky-telemetry` CI job is the empirical discovery surface. It
runs the same replay-only selection three times with seeds `17`, `73`, and
`113`; `BIOETL_RANDOM_ORDER_SEED` changes collection order only when explicitly
set. The reporter joins each run metadata file with its JUnit results, requires
one source commit, persists seed/order/shard identity plus the replay-tree
fingerprint, and fails when a node changes outcome without a matching curated
inventory entry. Curated inventory remains the review/ownership record; the
empirical artifact is the repeated-run observation and cannot replace it.

Failure classifications are informational and come from
`configs/quality/test_health_classifiers.yaml`; pytest exit codes and quality
gates remain the blocking signals.

Git LFS recovery notes:

- LFS-tracked test fixtures are declared in `.gitattributes` under
  `tests/fixtures/vcr/**/*.yaml`.
- If GitHub rejects a push with `GH008` for an unknown LFS object, first verify
  local LFS health with `git lfs fsck`, then upload the missing object with
  `git lfs push origin --object-id <sha>` or, for a full repair,
  `git lfs push --all origin`.
- If a generated local pre-push hook fails with
  `fatal: could not open '/dev/stdin' for reading`, do not replay that hook via
  a scripted `/dev/stdin` path. Run the explicit `git lfs push ...` repair
  command from a shell where `git-lfs` is on `PATH`, then rerun the normal
  project pre-push checks.

Canonical local execution paths:

- **CI / single-OS checkout**: `uv run python -m ...`, прежде всего
  `uv run python -m scripts.engineering.dev run-tests quick|cov|arch|smoke`.
- **Mixed Windows + WSL checkout (PowerShell)**:
  `.\scripts\engineering\dev\setup_env_windows.ps1`,
  `.\scripts\engineering\dev\run_pytest.ps1`, `.\scripts\engineering\dev\run_mypy.ps1`.
- **Mixed Windows + WSL checkout (WSL/Linux)**:
  `bash scripts/engineering/dev/setup_env_wsl.sh`,
  `bash scripts/engineering/dev/run_pytest.sh`, `bash scripts/engineering/dev/run_mypy.sh`.

Wrappers `run_pytest.ps1|.sh` по умолчанию добавляют только `-q --maxfail=1`,
если запуск не был вызван с `--help` / `--version`. Локальное coverage
instrumentation теперь opt-in: используйте `--with-coverage` или
`BIOETL_PYTEST_WITH_COVERAGE=1`, когда нужен coverage-instrumented wrapper run.
CI coverage semantics не меняются и остаются привязаны к lane
`coverage-verify`. WSL-обёртка дополнительно вызывает
`scripts/ops/launchers/codex/setup_plugins.sh --pytest-only` перед запуском pytest.
Для `tests/architecture`, `tests/benchmarks`, observability / serialization /
polars-heavy unit surfaces wrapper автоматически требует расширенный capability
set из `.[tests_full]`.

Supported policy slice for issue `#2598`:

- **Integration**: canonical roots `tests/integration/adapters/`,
  `tests/integration/chembl/`, `tests/integration/composite/`,
  `tests/integration/config/`, `tests/integration/infrastructure/`,
  `tests/integration/interfaces/`, `tests/integration/pipelines/`,
  `tests/integration/validation/`, `tests/integration/ci/`.
- **Integration provider families**: replay-first adapter coverage for `chembl`,
  `pubchem`, `pubmed`, `semanticscholar`, `uniprot`; mixed replay/mock adapter
  coverage for `crossref` and `openalex`; pipeline replay smoke for
  `chembl_activity`, `chembl_cell_line`, `chembl_compound_record`,
  `chembl_target_component`, `pubchem_compound`, `uniprot_protein`.
- **E2E provider families**: `chembl_activity`, `chembl_assay`,
  `chembl_molecule`, `chembl_publication`, `chembl_publication_term`,
  `chembl_target`, `crossref_publication`, `openalex_publication`,
  `pubchem_compound`, `pubmed_publication`, `semanticscholar_publication`,
  `uniprot_protein`.
- **E2E scenario families**: `advanced_scenarios`, `checkpoint`,
  `full_pipeline`, `full_pipeline_chain`, `run_types`.
- **Default replay mode**: local development should prefer replay with
  `--vcr-record=none` for stable feedback loops, and `tests/conftest.py` now
  defaults local runs to strict replay (`VCR_RECORD_MODE=none`) when no explicit
  override is supplied. Targeted refresh is supported via
  `--vcr-record=new_episodes`; broad cassette rewrites are not the supported
  default path.

Текущее состояние rollout по ADR-042:

- mutation testing в CI блокирует `domain/` с порогом `70%` и curated
  `application_control_plane` target
  (`src/bioetl/application/services/control_plane/`,
  `tests/unit/application/services/control_plane/`) с порогом `60%`
- broad `application/` mutation target (`60%`) задокументирован, но пока staged
  и не является blocking gate
- empty/broken `mutmut` run (`0` сгенерированных мутантов) больше не считается
  допустимым green-path и должен падать как неисправный gate; `mutmut results`
  nonzero exit или unparseable output тоже считаются broken gate
- VCR cassette metadata (`*_meta.yaml`) перешли в `enforced` rollout: `configs/quality/test_matrix.yaml` теперь объявляет managed inventory contract для всего canonical VCR estate, а repo-wide metadata coverage больше не держится на seeded subset
- `vcr_cassette_max_age_days: 90` является blocking stale-age threshold: CI теперь валидирует managed metadata inventory через `scripts/engineering/qa/vcr/check_vcr_metadata_age.py --max-age-days 90`
- canonical VCR metadata catalog теперь существует как tracked artifact в `reports/quality/vcr-metadata-catalog.json`
- canonical tooling paths активированы для enforced rollout: `scripts/engineering/qa/report_vcr_metadata_catalog.py` генерирует/проверяет catalog, а `scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py` служит canonical repo-wide backfill entry point и check-path для managed inventory drift
- descriptive test-health taxonomy теперь canonical-фиксируется в `configs/quality/test_health_reporting.yaml`; статусы `fully_exercised_green`, `staged_green`, `environment_limited_green` остаются informational и не заменяют merge-blocking CI status
- monthly `contract-tests.yml` остаётся активным live-network workflow и должен запускать `tests/contract/` с `BIOETL_LIVE_API_TESTS=true`, `BIOETL_NETWORK_TESTS=true` и `--network`
- monthly `contract-tests.yml` выполняется только в canonical repository `SatoryKono/BioactivityDataAcquisition`, а failure issue внутри workflow ссылается на этот guide как на поддерживаемый policy/runbook entry point
- минимальный live-contract baseline теперь полностью enforceable: `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar` обязаны иметь live contract suites
- для `semanticscholar` live governance теперь разделена:
  - `tests/contract/test_semanticscholar_contract.py` содержит promotion-grade путь;
  - `tests/contract/test_semanticscholar_contract_pilot.py` содержит richer pilot-soak проверки и требует `BIOETL_PILOT_SOAK_TESTS=true` или `--pilot-soak`
- текущие silver schema snapshots уже живут в `tests/contract/silver_schemas/snapshots/`; внешний provider-facing registry `tests/fixtures/contracts/{provider}/v{version}.json` тоже уже активирован как bounded live-provider baseline для `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar` и не заменяет schema snapshots
- Gold contract governance теперь тоже имеет явный machine-readable baseline:
  `tests/fixtures/golden/gold/schema_registry.v1.json` хранит canonical Gold
  schema snapshot registry, а bounded DQ-sensitive output bundles живут в
  `tests/fixtures/golden/gold/*_dq_bundle_v1.json`; drift/update path идёт через
  `tests/contract/test_gold_schema_snapshot_registry.py` и
  `UPDATE_SNAPSHOTS=1`
- Publication/Silver compatibility placeholders не должны оставаться как
  unconditional skips: machine-readable publication baseline хранится в
  `tests/fixtures/contracts/publication_schema_compatibility.v1.yaml`, а
  Silver compatibility checks обязаны быть executable against schema/config
  contracts.
- Module-level coverage inventory теперь является committed artifact:
  `reports/quality/module-coverage-inventory.json` генерируется из
  `reports/coverage/coverage.xml` через
  `python -m scripts.engineering.qa report-module-coverage --refresh-from-coverage-xml`
  в lane `coverage-verify`. Локальные drift-проверки без fresh coverage XML
  должны использовать hash-only режим
  `python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml`.
  `unmeasured_module_count=0` и `uncovered_module_count=0` означают, что все
  source modules измерены и имеют хотя бы одну covered executable line; это не
  утверждение о полном line/branch coverage.
  Artifact должен перечислять каждый `src/bioetl/**/*.py`
  module и явно фиксировать coverage status. Поле `source_tree_sha256` MUST
  обновляться после любых изменений под `src/bioetl/**/*.py` через
  `python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml`
  (см.
  `tests/architecture/test_module_coverage_inventory.py`).
- Architecture quality scorecard теперь является committed trend artifact:
  `reports/quality/architecture-quality-scorecard.json` агрегирует dependency
  map, module coverage inventory, compatibility census, dead-code inventory,
  duplication baseline, hotspot-family baseline, test-governance inventory и
  contract diagnostics в 10-категорийную модель с суммой весов `1.00`.
  Integral score is a governance scorecard snapshot, not a manual architecture
  review or broad architecture-health guarantee.
  Category scores вычисляются из live metrics, а не остаются fixed constants,
  поэтому substantial duplication/hotspot/test-governance reductions должны
  менять integral score после регенерации committed artifact.
  Artifact строится через
  `bioetl.infrastructure.quality.architecture_quality_scorecard` и проверяется
  `tests/architecture/test_architecture_quality_scorecard.py`; `quality_integral_gate`
  включает этот payload в CI JSON output для trend visibility.
- canonical VCR placement уже enforced в CI: кассеты вне `tests/fixtures/vcr/{provider}/` блокируются
- extensionless VCR files пока допустимы только через `.github/vcr-noext-allowlist.txt`; новые такие файлы добавлять нельзя

## 2. Уровни Тестирования

### 2.1. Unit Tests (`tests/unit/`)

Изолированные тесты бизнес-логики и трансформаций.

- **Domain**: Тестирование сущностей и чистых функций в `src/bioetl/domain/`.
- **Application**: Тестирование трансформеров и логики пайплайнов. In-memory fakes предпочтительны, MagicMock допустим.
- **Правило**: Никакого сетевого взаимодействия. Repo-layout, dashboard,
  workflow-tree, and checked-in config-file scenarios не должны жить в
  `tests/unit/`, если они не перечислены явно в
  `configs/quality/test_governance_audit.yaml` как repo-backed contract
  exceptions and marked with `pytest.mark.repo_backed`.
- Локальный `tmp_path`/tempdir I/O допустим только для изолированных
  filesystem/serialization seams и не должен зависеть от checked-in repo tree.
- Memory-marked MCP/Neo4j smoke tests and file-backed workflow smokes не
  относятся к `tests/unit/`; их canonical path теперь `tests/smoke/` или
  integration lanes.

#### 2.1.1. Repo-backed Path Naming and Reclassification

Путь `tests/unit/` в BioETL обозначает прежде всего layer ownership, а не
абсолютный запрет на чтение checked-in repository artifacts. Но canonical pure-unit
surface теперь отделён от repo-backed contract tests через dedicated subtree
`tests/unit/repo_backed/`.

Repo-backed contract tests могут оставаться в unit ownership surface только если:

- checked-in artifact сам является contract surface под тестом;
- выполнение остаётся local-only и deterministic;
- тест живёт под `tests/unit/repo_backed/` и изолирован в lane `repo-backed-unit`,
  а не в `unit-fast`;
- файл явно перечислен в `configs/quality/test_governance_audit.yaml` и помечен
  `pytest.mark.repo_backed`.

CI ownership is explicit: `.github/workflows/tests.yml` runs the complete
`repo-backed-unit` lane serially from `tests/unit/repo_backed/`; the parallel
`unit-fast` and `unit-other` surfaces exclude `repo_backed`. The owning team is
`test-governance`, and failures are blocking because these tests validate
checked-in repository contracts.

For a local promotion-confidence pass, run `make test-confidence-local`. It
keeps incompatible execution modes separate: pure unit first, the canonical
fast architecture shard, serial offline contract replay, and finally the
canonical 85% coverage gate. The existing focused commands remain available
for shorter feedback loops.

Surface должен быть перенесён из `tests/unit/`, если тест в первую очередь
проверяет не модульный контракт, а более широкую integration behavior:

- subprocess / CLI process orchestration;
- dashboard, workflow-tree, repo-layout, memory-backend, или service startup
  integration semantics;
- network, VCR, detached backend, или multi-component runtime behavior.

Canonical keep-vs-move inventory живёт в
`configs/quality/test_governance_audit.yaml`:

- `repo_backed_unit_test_exceptions` — retained repo-backed tests, которые
  intentionally остаются в unit ownership surface, но только под
  `tests/unit/repo_backed/`;
- `file_backed_domain_contract_tests` — domain/file-backed contract surfaces,
  которые routed в `contracts` lane;
- `mixed_scope_unit_path_policy` — explicit naming/reclassification policy и
  moved examples.

#### 2.1.2. Source-to-Test Ownership

Для тонких пакетов (`package/__init__.py` + один содержательный `.py`-модуль) проект
держит явную source-to-test ownership symmetry:

- по умолчанию такой модуль должен иметь same-path sibling
  `tests/unit/.../test_<module>.py`;
- исключения фиксируются machine-readable в
  `configs/quality/source_test_mapping_exceptions.yaml`;
- архитектурный guard находится в
  `tests/architecture/test_source_test_mapping_policy.py`.

Это правило staged и не требует на текущем этапе зеркального `test_<module>.py` для
каждого файла в `src/bioetl/`. Для aggregate/contract/facade coverage исключения
должны быть перечислены явно, чтобы contributor мог быстро понять canonical owner
test для модуля.

Для behavior-heavy модулей второго этапа используется отдельный curated inventory:

- `configs/quality/source_test_owner_inventory.yaml`
- `tests/architecture/test_curated_source_test_ownership.py`

Текущий curated scope уже покрывает high-signal seams в `application/core`,
`application/composite`, `infrastructure/storage` и `infrastructure/adapters`.
Для таких модулей ownership фиксируется либо через direct same-path test, либо
через явно перечисленный focused cluster-owner suite.

Там допускаются два режима:

- `direct_test`: same-path owner test обязателен;
- `cluster_owner`: модуль intentionally owned через focused aggregate suite, и это
  должно быть явно перечислено в inventory.

Для stable façade и arch-owned seams есть отдельный inventory:

- `configs/quality/source_test_facade_inventory.yaml`
- `tests/architecture/test_source_test_facade_ownership.py`

Этот слой зарезервирован для package facades, retained canonical entrypoints и
compatibility facades, где mirror-path `test_<module>.py` был бы ложным сигналом,
а реальный owner живёт в contract или architecture suite.

#### 2.1.3. Pure Transformation Logic Baseline

Pure transformation logic считается отдельным high-signal unit-test surface для:

- функций в `src/bioetl/domain/transformations/`;
- pure helpers и dict-level transformers в `src/bioetl/application/core/`,
  если они работают только in-memory и не оркестрируют adapters, storage или
  runtime lifecycle.

Для такого класса тестов canonical expectations следующие:

- тесты должны быть детерминированными и работать только в памяти;
- входы и ожидаемые выходы должны быть зафиксированы явно, без скрытой
  зависимости от времени, сети, filesystem, random state или глобального
  runtime context;
- failure/edge behavior должен проверяться так же явно, как happy path;
- in-memory fakes допустимы только там, где helper нельзя протестировать как
  чистую функцию, но для pure transformation logic прямой input/output assertion
  остаётся предпочитаемым стилем.

Минимальный edge-case baseline для новых и изменяемых pure transformation tests:

- empty inputs;
- malformed inputs;
- Unicode значения и строковая нормализация без потери смысла;
- `null` / missing values и их deterministic fallback semantics.

Подходящие canonical examples в репозитории:

- `tests/unit/domain/transformations/test_coercion.py`
- `tests/unit/domain/test_transformations.py`
- `tests/unit/application/core/test_dict_transformers.py`

Рекомендуемый execution path для этого baseline:

```bash
# CI / single-OS
uv run python -m pytest -q tests/unit/domain/transformations/test_coercion.py
uv run python -m pytest -q tests/unit/application/core/test_dict_transformers.py
uv run python -m pytest -q tests/architecture/test_domain_unit_test_purity.py

# Mixed Windows + WSL checkout (WSL)
bash scripts/engineering/dev/run_pytest.sh tests/unit/domain/transformations/test_coercion.py
bash scripts/engineering/dev/run_pytest.sh tests/unit/application/core/test_dict_transformers.py
bash scripts/engineering/dev/run_pytest.sh tests/architecture/test_domain_unit_test_purity.py
```

Если изменение затрагивает только pure transformation logic, такой targeted run
считается поддерживаемым local feedback path до более широкого
`uv run python -m scripts.engineering.dev run-tests quick` или полного
`uv run python -m scripts.engineering.dev run-tests cov`.

### 2.2. Integration Tests (`tests/integration/`)

Проверка взаимодействия компонентов с внешними API и хранилищем.

- **Адаптеры**: Тестирование HTTP-клиентов (ChEMBL, PubChem, UniProt) с использованием VCR-кассет.
- **Storage**: Проверка записи в Delta Lake и Bronze хранилище (используются локальные временные пути).
  Unit-like storage checks should use explicit test seams such as
  `tests/fakes/storage_fake.py` or `tmp_path`-backed storage instances before
  claiming a storage optimization. Do not describe this as "in-memory Delta"
  unless the actual Delta backend is part of that measured seam; real Delta I/O
  remains in integration/e2e/contract lanes.
- **VCR Policy**: canonical machine-readable policy живёт в `configs/quality/integration_vcr_policy.yaml`. Кассеты хранятся в `tests/fixtures/vcr/`, а стандартный CI path использует `--vcr-record=none`.
- **Compatibility Policy**: `pytest-vcr` должен импортироваться против locked `wrapt` dependency из активного окружения. Repo-root workaround'ы вроде `wrapt/` или `sitecustomize.py` не считаются поддерживаемым fix path; если импорт ломается, нужно чинить environment/lock, а не shadowing dependency.
- **Fixture Governance**: `_meta.yaml` sidecars и stale-age policy находятся в `enforced` rollout. Managed VCR inventory покрывается repo-wide sidecars, canonical catalog, и CI stale-age checks.
- **Catalog / Backfill Policy**: canonical VCR metadata catalog и canonical backfill script являются обязательным governance path; drift по missing sidecars, age, или catalog sync теперь считается blocking.
- **Live Contract Baseline**: live-network enforcement обязателен для `chembl`, `pubchem`, `uniprot`, `pubmed`, `crossref`, `openalex`, `semanticscholar`; richer pilot-soak coverage for Semantic Scholar remains opt-in and does not redefine the enforced baseline.

#### 2.2.1. Supported integration families

В рамках tracked policy `#2598` проект явно поддерживает следующие integration
surface areas:

- `tests/integration/adapters/` — adapter-level HTTP replay и mixed-mode adapter
  checks.
- `tests/integration/pipelines/` — pipeline-level replay smoke для
  `chembl_activity`, `chembl_cell_line`, `chembl_compound_record`,
  `chembl_target_component`.
- `tests/integration/test_pubchem_pipeline.py` и
  `tests/integration/test_uniprot_pipeline.py` — репрезентативные provider
  pipeline smoke paths.
- `tests/integration/interfaces/`, `tests/integration/config/`,
  `tests/integration/composite/`, `tests/integration/validation/`,
  `tests/integration/ci/` — governance/runtime-facing integration surfaces,
  которые не обязаны использовать VCR, но входят в canonical integration scope.

CrossRef и OpenAlex допускают mixed replay/mock режим на adapter-level coverage.
Это считается supported policy, а не отклонением, пока machine-readable policy и
guide остаются синхронизированными.

Concrete file-level inventory для canonical integration surface живёт в
`configs/quality/integration_vcr_policy.yaml -> tracked_suite_inventory.integration`.
Новые `tests/integration/test_*.py` и `tests/integration/**/test_*.py` должны либо
попасть в этот inventory, либо считаться policy drift.

#### 2.2.2. Canonical replay and refresh commands

```bash
# CI / single-OS replay
uv run python -m pytest tests/integration/ --vcr-record=none -m "integration and not e2e"

# Windows replay
.\scripts\engineering\dev\run_pytest.ps1 tests\integration\ --vcr-record=none -m "integration and not e2e"

# WSL replay
bash scripts/engineering/dev/run_pytest.sh tests/integration/ --vcr-record=none -m "integration and not e2e"

# Targeted refresh only
uv run python -m pytest tests/integration/adapters/test_pubmed.py --vcr-record=new_episodes -v
```

`tests/conftest.py` теперь задаёт `VCR_RECORD_MODE=none` как локальный default
для ad-hoc runs без явного режима, а policy-first execution path для supported
integration replay по-прежнему должен задавать `--vcr-record=none`. Это
уменьшает риск случайной перезаписи кассет во время обычного dev feedback loop.

### 2.3. End-to-End (E2E) Tests (`tests/e2e/`)

Тестирование полного цикла работы пайплайна.

- **Сценарий**: `Run ID` -> `Fetch` -> `Bronze` -> `Silver` -> `Gold`.
- **Архитектура**: Local-Only (MemoryLock, LocalCheckpoint, FileSystem Storage).
- **Запуск**: `uv run python -m pytest tests/e2e/ -m e2e -v`.
- **Maintenance carve-out**: E2E intentionally patches out Bronze retention
  cleanup and postrun Silver compaction so replay assertions stay deterministic;
  maintenance fidelity belongs to dedicated maintenance-focused unit/integration
  suites, not the canonical E2E lane.

#### 2.3.1. Supported E2E families

Canonical provider-facing E2E families:

- `chembl_activity`
- `chembl_assay`
- `chembl_molecule`
- `chembl_publication`
- `chembl_publication_term`
- `chembl_target`
- `crossref_publication`
- `openalex_publication`
- `pubchem_compound`
- `pubmed_publication`
- `semanticscholar_publication`
- `uniprot_protein`

Concrete file-level inventory для canonical E2E surface живёт в
`configs/quality/integration_vcr_policy.yaml -> tracked_suite_inventory.e2e`.
Это включает provider runs, scenario runs и tracked governance/resilience
surfaces. Новый `tests/e2e/test_*.py` без inventory update считается policy drift.

Canonical scenario E2E families:

- `advanced_scenarios`
- `checkpoint`
- `full_pipeline`
- `full_pipeline_chain`
- `run_types`

Supported replay/refresh commands:

```bash
# Replay-first E2E run
uv run python -m pytest tests/e2e/ -m e2e --vcr-record=none -v

# Windows replay
.\scripts\engineering\dev\run_pytest.ps1 tests\e2e\ -m e2e --vcr-record=none

# WSL replay
bash scripts/engineering/dev/run_pytest.sh tests/e2e/ -m e2e --vcr-record=none

# Targeted refresh only
uv run python -m pytest tests/e2e/test_pubchem_compound_e2e.py -m e2e --vcr-record=new_episodes -v
```

Standard CI replay path for E2E — это не полный `tests/e2e/` run, а
control-plane smoke target
`tests/e2e/test_pubchem_compound_e2e.py::test_pubchem_compound_full_cycle` с
`VCR_RECORD_MODE=none` и `--vcr-record=none`.

Exact replay runtime validation is covered by a focused matrix rather than the
whole E2E lane:

```bash
uv run pytest tests/integration/ci/test_track_d_fixture_control_plane_linkage.py -q --tb=short
uv run pytest tests/integration/ci/test_reproducibility_contract_suite.py::test_reproducibility_contract_composite_full_snapshot_envelope_rebuild_resume_matrix -q --tb=short
```

The matrix writes compact evidence under `reports/reproducibility/` during the
test run. The ordinary supported-family case proves stable semantic identity
across two cached-Bronze exact replay occurrences. The composite case proves the
same contract only when seed, dependency, and enricher inputs all have a full
cached-Bronze snapshot envelope.

### 2.4. Architecture Tests (`tests/architecture/`)

Автоматизированный контроль за соблюдением архитектурных правил проекта.

- **Layer Separation**: Проверка отсутствия импортов `infrastructure` в `domain/application` через `import-linter`.
- **Rules Enforcement**:
  - `test-no-random-in-writers` (REQ-ARCH-030): Запрет на использование `random` в слое хранилища для детерминизма.
    - Проверяет: `import random`, `from random import`, `random.uniform()`, `random.choice()`
    - Область: `src/bioetl/infrastructure/storage/*.py`
  - `test-no-datetime-now-in-infrastructure`: Запрет на создание временных меток в инфраструктурном слое.
    - Проверяет: `datetime.now()`, `datetime.datetime.now()`
    - Область: `src/bioetl/infrastructure/**/*.py` (с исключениями)
  - `test-all-ports-have-implementations`: Проверка наличия реализаций для всех протоколов (портов).
  - `test_test_matrix_coverage`: Проверка, что ADR-042 matrix, fixture rollout и mutation governance не расходятся с текущим состоянием репозитория и workflow.

**Документация:** См. [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md) для обоснования детерминизма.

### 2.5. Security Tests (`tests/security/`)

- Проверка санитизации секретов в VCR-кассетах.
- Проверка отсутствия паролей и ключей в логах.
- Тестирование обработки PII (Personal Identifiable Information).

### 2.6. Golden/Snapshot Tests (`tests/fixtures/golden/`)

Golden/Snapshot тесты используются для валидации критических outputs и обеспечения обратной совместимости.

**Назначение:**
- Валидация Data Quality contracts
- Проверка корректности transformation логики
- Обнаружение regressions в output schemas

**Расположение:**
- Golden fixtures: `tests/fixtures/golden/`
- Contract tests: `tests/contract/test_gold_dq_golden_snapshots.py`

**Использование:**
```bash
# Запуск golden tests
pytest tests/contract/test_gold_dq_golden_snapshots.py

# Обновление golden snapshots (только при намеренном изменении)
pytest tests/contract/test_gold_dq_golden_snapshots.py --update-golden
```

**Best Practices:**
- Golden snapshots должны быть version-controlled
- Обновление snapshots требует явного флага `--update-golden`
- Изменения в snapshots должны сопровождаться коммитом с объяснением

## 3. Метрики и Покрытие

- **Blocking CI Threshold**: merge-gate в CI использует `coverage report --fail-under=85`, то есть blocking threshold для репозитория составляет **>=85%** общего line coverage.
- **Domain Coverage Goal**: для доменного слоя по-прежнему желателен более высокий локальный стандарт, но он не является отдельным blocking CI gate, пока workflow не вводит отдельный `fail-under` для domain-only coverage.
- **Branch Coverage**: Проверяется автоматически через `pytest-cov`.
- **Module Coverage Inventory**: `coverage-verify` генерирует
  `reports/quality/module-coverage-inventory.json` после
  `reports/coverage/coverage.xml`; локальная проверка drift:
  `uv run python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml`.
  Per-module gates (`configs/quality/module_coverage_gates.yaml`): lane
  `coverage-verify` также запускает
  `--enforce-module-thresholds block-regression --fail-on-regression`, чтобы
  падать при снижении line % относительно committed inventory; tier gaps
  (85/90/95) пока только warn до Phase C.
  После изменений в `src/bioetl/**/*.py` обновляй `source_tree_sha256`:
  `python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml`,
  затем
  `pytest tests/architecture/test_module_coverage_inventory.py::test_module_coverage_inventory_source_tree_hash_is_current`.
- **Architecture Quality Scorecard**:
  `reports/quality/architecture-quality-scorecard.json` фиксирует
  evidence-backed quality trend по слоям, DI, module boundaries, tests,
  contracts, determinism и debt burden. Это governance scorecard snapshot, а не
  полный manual architecture review. Локальная drift-проверка:
  `pytest tests/architecture/test_architecture_quality_scorecard.py`.
- **Regression**: Все исправления багов обязаны сопровождаться регрессионным тестом.
- **Coverage Configuration**: Подробная информация о настройке покрытия, исключаемых паттернах и troubleshooting — см. [Coverage Configuration Guide](./coverage-configuration.md)

## 4. Как запускать тесты

```bash
# Запуск локального стабильного test suite с coverage gate
uv run python -m scripts.engineering.dev run-tests cov

# Быстрый локальный feedback loop
uv run python -m scripts.engineering.dev run-tests quick

# CI-подобный устойчивый прогон coverage/shards
BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 bash scripts/engineering/dev/run_pytest_sharded.sh --stream

# Запуск E2E в Local-Only режиме
uv run python -m pytest tests/e2e/ -m e2e -v

# Mixed Windows + WSL checkout (PowerShell)
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf

# Mixed Windows + WSL checkout (WSL/Linux)
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf

# Запуск только архитектурных тестов
uv run python -m scripts.engineering.dev run-tests arch

# Точечное обновление VCR кассет
uv run python -m pytest tests/integration/adapters/test_pubmed.py --vcr-record=new_episodes -v

# Sharded coverage run with persisted XML/HTML reports
BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 \
bash scripts/engineering/dev/run_pytest_sharded.sh \
  --stream \
  --keep-coverage-files \
  --coverage-dir .coverage-sharded \
  -- -vv --cov-report=term-missing
```

### 4.2. Integration / E2E execution matrix

| Surface                    | CI / single-OS                                                                              | Windows PowerShell                                                                                           | WSL/Linux                                                                                                      | Notes                                                       |
| -------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Integration replay         | `uv run python -m pytest tests/integration/ --vcr-record=none -m "integration and not e2e"` | `.\scripts\engineering\dev\run_pytest.ps1 tests\integration\ --vcr-record=none -m "integration and not e2e"` | `bash scripts/engineering/dev/run_pytest.sh tests/integration/ --vcr-record=none -m "integration and not e2e"` | canonical stable feedback path                              |
| E2E replay                 | `uv run python -m pytest tests/e2e/ -m e2e --vcr-record=none -v`                            | `.\scripts\engineering\dev\run_pytest.ps1 tests\e2e\ -m e2e --vcr-record=none`                               | `bash scripts/engineering/dev/run_pytest.sh tests/e2e/ -m e2e --vcr-record=none`                               | local-only execution, no live network                       |
| Targeted cassette refresh  | `uv run python -m pytest <target> --vcr-record=new_episodes -v`                             | `.\scripts\engineering\dev\run_pytest.ps1 <target> --vcr-record=new_episodes -v`                             | `bash scripts/engineering/dev/run_pytest.sh <target> --vcr-record=new_episodes -v`                             | supported refresh path                                      |
| Live contract verification | `uv run pytest tests/contract/ -v --tb=short --network`                                     | n/a                                                                                                          | n/a                                                                                                            | scheduled/manual workflow path, separate from replay policy |

### 4.3. Cassette lifecycle rules

- **Standard CI** must keep VCR replay locked to `none`.
- **Default local supported path** should also prefer explicit replay via
  `--vcr-record=none`.
- **Targeted refresh** should use `--vcr-record=new_episodes`; repo-wide
  cassette rewrites are not the supported default path.
- **Refresh triggers** include missing cassette for an already-supported path,
  intentional adapter request-shape change, or replay divergence confirmed by a
  contract/schema-drift investigation.
- **Review is required** after refresh when request parameters, headers,
  pagination shape, redaction coverage, or extensionless filename status
  change.
- **Stale signals** include `_meta.yaml` age above `90` days where metadata
  exists, moved provider/pipeline paths without policy updates, or replay shape
  changes without review note.
- **Pre-refresh checks**:
  - `python -m scripts.engineering.qa.vcr check-placement`
  - `python -m scripts.engineering.qa.vcr check-naming`
- **Post-refresh checks**:
  - `python -m scripts.engineering.qa.vcr check-placement`
  - `python -m scripts.engineering.qa.vcr check-naming`
  - `python -m scripts.engineering.qa.vcr check-secrets`
  - `python -m scripts.engineering.qa.vcr check-metadata-age --max-age-days 90`
  - `python -m scripts.engineering.qa report-vcr-metadata --check`

### 4.4. Provider contract drift runbook

`provider-contract-drift.yml` is a replay/snapshot governance gate, not a live
API gate. It must stay network-free on pull requests and pushes; live provider
verification remains isolated in the monthly/manual `contract-tests.yml` path.

Run the same focused gate locally when changing provider adapters, provider
configs, xwalk files, generated normalization artifacts, or export snapshot
manifests:

```bash
uv run python -m pytest \
  tests/contract/test_provider_contract_drift_helper.py \
  tests/contract/test_provider_contract_snapshot_registry.py \
  tests/contract/test_provider_contract_replay_registry.py \
  tests/contract/test_provider_contract_drift_replay.py \
  tests/unit/application/services/test_export_manifests.py \
  -q --tb=short
uv run python -m scripts.engineering.qa check-xwalk-missing-backlog
uv run python -m scripts.docs generate-pipeline-normalization-matrix --check
uv run python -m scripts.engineering.qa report-provider-contract-drift \
  --output reports/quality/provider-contract-drift-report.json \
  --fail-on breaking
```

The governed interoperability surfaces are declared in
`configs/quality/test_matrix.yaml` under
`fixture_governance.interoperability_drift_gates`. The current scope covers
OpenAlex auth/rate/pagination/fallback config, ChEMBL activity publication
identifiers, PubChem chemical standardization fields, ChEMBL ontology companion
fields, export provenance/licensing/checksum manifests, xwalk backlog markers,
and generated normalization matrix drift.

Do not refresh provider contract snapshots as the first response to a failure.
Investigate the provider documentation/API behavior first, then update the
adapter, schema, config, docs, xwalk, or generated artifact surface as needed.
Use `UPDATE_SNAPSHOTS=1` only after the new provider shape is verified as
intentional. Drift diagnostics must retain provider, entity, probe, path,
expected type, observed type, severity, and remediation text so failures are
actionable in CI artifacts.

### 4.1. Быстрый старт для рекомендуемого локального прогона

| Шаг | Команда                                            | Назначение                                                                               |
| --- | -------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 1   | `uv sync --extra dev --extra tests --extra tracing` | CI/single-OS bootstrap                                                                   |
| 2   | `setup_env_windows.ps1` / `setup_env_wsl.sh`       | Mixed-checkout bootstrap в `.venv-win` или `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` |
| 3   | `uv run python -m scripts.engineering.dev run-tests quick` | Получить быстрый feedback для unit + smoke                                      |
| 4   | `uv run python -m scripts.engineering.dev run-tests cov` | Выполнить стабильный локальный прогон с coverage gate 85%                         |
| 5   | `BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 bash scripts/engineering/dev/run_pytest_sharded.sh --stream` | Выполнить ускоренный coverage/sharded прогон |
| 6   | `BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded -- -vv --cov-report=term-missing` | Выполнить sharded coverage-run c сохранением `reports/coverage/coverage.xml` и `reports/coverage/htmlcov/` |
| 7   | `uv run python -m pytest tests/e2e/ -m e2e -v`     | Отдельно запустить E2E в Local-Only режиме                                               |

**Примечания:**

- Если нужен быстрый coverage-run без полного serial suite, используйте sharded runner с `BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1`.
- Для корректного прохождения трассировки и мониторинга установите опциональные зависимости (`psutil`, `opentelemetry-*`).
- Локальный `run-tests cov` по-прежнему не генерирует `reports/coverage/htmlcov/` автоматически; для persisted local coverage artifacts используйте sharded runner с `BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1` или `--force-mounted-coverage`.
- В CI используется `.github/workflows/tests.yml`; для локального rehearsal используйте sharded runner и явные architecture/config slices вместо удалённых legacy CI wrappers.
- В mixed Windows + WSL checkout `.venv` не должен быть общим между PowerShell и WSL: используйте `.venv-win` и внешний WSL venv через `setup_env_windows.ps1` / `setup_env_wsl.sh`.

## 5. План по устранению избыточности (ChEMBL Target Component)

В ходе аудита пайплайна `chembl_target_component` был выявлен риск многократного извлечения одних и тех же данных. План исправления:

1. **Дедупликация на стороне клиента**: Внедрение `seen-ids` в `ChemblAdapter.fetch-filtered` для обработки дублей, возвращаемых API при использовании сложных фильтров.
1. **Исправление пагинации**: Переход от фиксированного `offset += batch-size` к `offset += len(records)` для предотвращения пропусков данных в Degraded режиме.
1. **Оптимизация параметров**: Передача `limit` напрямую в API запросы для исключения выкачивания лишних записей из ChEMBL.

## 6. Оптимизация Тестов

### 6.1. Параллельное Выполнение (pytest-xdist)

Тесты поддерживают параллельное выполнение через `pytest-xdist`, но локальный
дефолт остаётся serial для стабильности. Каноническая стратегия такая:

```bash
# Локальный стабильный дефолт
uv run python -m scripts.engineering.dev run-tests cov

# Быстрый локальный feedback loop
uv run python -m scripts.engineering.dev run-tests quick

# Архитектурный slice
uv run python -m scripts.engineering.dev run-tests arch

# Persisted sharded coverage artifacts
BIOETL_PYTEST_SHARDED_FORCE_COVERAGE=1 bash scripts/engineering/dev/run_pytest_sharded.sh --stream --keep-coverage-files --coverage-dir .coverage-sharded

# Явный параллельный запуск вручную
uv run python -m scripts.engineering.dev run-tests parallel -m "not serial" --dist loadscope --max-worker-restart=0
```

Текущие правила:

- `xdist` используется только для explicit local runs и CI lanes;
- тесты с `@pytest.mark.serial` не смешиваются с parallel-safe subset;
- для worker grouping используется `--dist loadscope`;
- для прозрачной диагностики worker crashes используется `--max-worker-restart=0`;
- Windows mixed-checkout wrappers по умолчанию держат `-n 1`; поднимать лимит
  нужно только через `BIOETL_PYTEST_WINDOWS_XDIST_WORKERS=<n>` после
  подтверждения, что хост не ловит `WinError 10055`;
- benchmark runs выполняются отдельно и без `xdist`.

Репозиторий не использует hard-coded performance SLA в документации, потому что
timings зависят от hardware, Python version, coverage mode и состава shard-ов.
Для актуального baseline фиксируйте точную команду
(`run-tests cov`, `run-tests quick`, sharded runner или explicit `pytest`),
дату и окружение.

### 6.2. Hypothesis Профили

Hypothesis настроен с профилями для разных сценариев (см. `tests/conftest.py`):

| Профиль    | max-examples | Использование                   |
| ---------- | ------------ | ------------------------------- |
| `ci`       | 10           | Автоматически в CI (CI=true)    |
| `fast`     | 5            | Быстрый smoke test              |
| `dev`      | 50           | Более глубокий локальный прогон |
| `thorough` | 200          | Pre-release тестирование        |

```bash
# Использование профилей
HYPOTHESIS_PROFILE=fast uv run python -m pytest tests/unit/
HYPOTHESIS_PROFILE=dev uv run python -m pytest tests/unit/  # Более широкий локальный прогон
HYPOTHESIS_PROFILE=thorough uv run python -m pytest tests/  # Перед релизом
```

**Default profile**: `fast`, если `HYPOTHESIS_PROFILE` не задан.

**Важно**: Тесты НЕ должны переопределять `max-examples` в декораторе `@settings()`, чтобы профили работали корректно.

### 6.3. Test Markers

Используйте маркеры для выборочного запуска:

```bash
# Исключить медленные тесты
uv run python -m pytest tests/ -m "not slow"

# Только unit тесты
uv run python -m pytest tests/ -m "unit"

# Только Hypothesis тесты
uv run python -m pytest tests/ -m "hypothesis"

# Быстрый smoke
uv run python -m scripts.engineering.dev run-tests smoke
```

**Доступные маркеры**:

- `unit` — Unit тесты (быстрые, без I/O)
- `integration` — Integration тесты с VCR
- `e2e` — End-to-end тесты
- `slow` — Медленные тесты (subprocess, vulture, security scans)
- `hypothesis` — Property-based тесты
- `architecture` — Архитектурные тесты
- `security` — Security тесты
- `smoke` — Быстрые smoke тесты
- `serial` — Тесты, которые должны идти без `xdist`
- `benchmark` — Benchmark-тесты, исключённые из стандартных запусков
- `contracts` — Contract tests
- `no_api` — Contract tests, не требующие live API access

### 6.4. CI Test Layering

CI использует job-based layering, а не один линейный `pytest` прогон:

```
tests.yml
├── smoke-check
├── governance-preflight
├── config-schema-preflight
├── test-fast
├── repo-backed-unit
├── test-matrix
├── performance-budgets
├── coverage-verify
├── flaky-telemetry
├── duration-telemetry
├── control-plane-e2e
├── track-d-gates
└── dq-consistency-gate

contract-tests.yml
└── scheduled/manual live contract workflow for tests/contract/

provider-contract-drift.yml
└── replay-based provider API drift gate for provider-facing snapshots
```

Ключевые свойства текущего CI:

- `test-fast` даёт быстрый feedback для unit + architecture;
- `test-matrix` шардирует unit/integration/security по test groups и Python versions;
- `coverage-verify` не rerun-ит весь suite, а объединяет только matrix-generated coverage shards и отдельно догоняет `serial` subset;
- live contract tests вынесены в отдельный workflow и не являются частью обычного PR path;
- replay drift gate работает отдельно от live path и использует существующие
  `tests/fixtures/contracts/{provider}/v{version}.json` + curated VCR cassettes
  как default PR/CI baseline;
- live contract workflow guarded to repository `SatoryKono/BioactivityDataAcquisition`; в нём `tests/contract/` запускаются только при `BIOETL_LIVE_API_TESTS=true`, `BIOETL_NETWORK_TESTS=true` и флаге `--network`;
- `provider-contract-drift.yml` генерирует machine-readable artifact
  `reports/quality/provider-contract-drift-report.json` и hard-fail'ит только на `breaking`
  drift; `warning` остаётся видимым в artifact для PR review;
- `repo-backed-unit` serially owns the complete checked-in artifact contract
  subtree and is excluded from parallel pure-unit jobs;
- `flaky-telemetry` performs replay-only repeated and order-randomized runs and
  blocks untriaged outcome drift;
- `duration-telemetry` собирает JUnit telemetry и публикует slow-test artifact.
  Its committed snapshot records source-tree identity, contributing JUnit
  files, executed/collected counts, worker mode, lane wall times, and explicit
  exclusions for live-provider, performance, and manual e2e tests.

## 7. Воспроизводимость и Проверка Зависимостей

Для обеспечения стабильной работы Quality Gates (особенно расчёта покрытия и линтинга) в CI-окружении и на машинах разработчиков, проект использует строгую проверку зависимостей.

### 7.1. Полная настройка окружения

Для первичной настройки или восстановления окружения используйте:

```bash
# Канонический локальный bootstrap
uv sync --extra dev --extra tests --extra tracing
uv run python -m scripts.ops setup-plugins

# Mixed Windows + WSL checkout
.\scripts\engineering\dev\setup_env_windows.ps1
bash scripts/engineering/dev/setup_env_wsl.sh
```

Поддерживаемый aggregate flow для локального окружения:
`uv sync --extra dev --extra tests --extra tracing`,
`uv run python -m scripts.ops setup-plugins`. `scripts/engineering/dev/dev_setup.sh`
— legacy placeholder и не является поддерживаемым onboarding/testing path.

### 7.2. Smoke-check зависимостей и инструментов

Перед запуском основного набора тестов или линтеров необходимо убедиться, что все критические зависимости и инструменты установлены.

**Runtime зависимости:**

```bash
uv run python -m scripts.engineering.dev run-tests smoke
```

Проверяет доступность критических runtime dependencies через живой smoke lane.
В CI аналогичная проверка выполняется отдельным `smoke-check` job в
`.github/workflows/tests.yml`.

**Инструменты разработки:**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
```

Проверяет доступность repo-supported lint/type toolchain (`ruff`, `mypy`) и
остаётся каноническим smoke path для инструментов аудита, которые реально
участвуют в локальных quality lanes.

### 7.3. Решение проблем с воспроизводимостью

Если аудит или CI падают с ошибками `ModuleNotFoundError`:

1. Выполните `uv sync --extra dev --extra tests --extra tracing`, затем `uv run python -m scripts.ops setup-plugins`.
1. В mixed Windows + WSL checkout пересоберите правильное OS-specific окружение через `setup_env_windows.ps1` или `setup_env_wsl.sh`, а затем запускайте `run_pytest.ps1|.sh` / `run_mypy.ps1|.sh`.
1. Проверьте статус инструментов через `uv run ruff check . && uv run ruff format --check . && uv run mypy src tests`.

В CI для этого используется не legacy `make` wrapper, а отдельный набор шагов в
`.github/workflows/tests.yml`: короткий `smoke-check`, затем независимые
`governance-preflight` и `config-schema-preflight`, после чего стартуют
`test-fast` / `test-matrix`, а в финале `coverage-verify` объединяет coverage
shard-ы и отдельно догоняет только `serial`-тесты. Pytest/Hypothesis cache
остаётся стабильным благодаря pinned зависимостям в `pyproject.toml` и
детерминированному `PYTHONHASHSEED` в CI.

## 8. Forbidden-Artifact Rules для Active Testing Docs

Active testing documentation в `docs/03-guides/testing.md` и связанных ADR
должна соблюдать следующие forbidden-artifact rules:

### Запрещённые артефакты в active docs

- **VCR cassettes**: Запрещено включать VCR cassette файлы (`.yaml`, `.json`) в
  active testing docs. VCR файлы MUST храниться только в
  `tests/fixtures/vcr/{provider}/`
  и ссылаться из active docs как repository-path evidence.
- **Test output artifacts**: Запрещено включать stdout/stderr output, coverage reports,
  или тестовые логи в active testing docs. Такие артефакты MUST храниться в
  `reports/` или временных директориях.
- **Deprecated test commands**: Запрещено документировать устаревшие команды
  запуска тестов (например, `scripts/dev/dev_setup.sh`). Канонические команды
  MUST быть только из `Makefile` или поддерживаемых скриптов в
  `scripts/engineering/`.
- **Hardcoded test paths**: Запрещено хардкодить абсолютные пути к тестовым файлам
  или директориям в active docs. Используйте относительные пути от корня репозитория.
- **Environment-specific configs**: Запрещено включать environment-specific
  конфигурации (например, `.env` файлы, local paths) в active testing docs.
  Используйте placeholder comments или ссылки на governance docs.
- **Test execution logs**: Запрещено включать полные логи выполнения тестов в active docs.
  Краткие примеры команд допустимы, но full execution logs MUST быть в `reports/`.

### Source of Truth Discipline

- **Test governance configs**: Источником истины для testing governance являются
  `configs/quality/test_matrix.yaml`, `configs/quality/test_governance_audit.yaml`,
  и `configs/quality/integration_vcr_policy.yaml`.
- **Testing ADR**: Источником истины для testing strategy является
  [ADR-042](../02-architecture/decisions/ADR-042-testing-strategy-matrix.md).
- **Active docs**: `docs/03-guides/testing.md` является canonical entrypoint для
  contributors, но MUST NOT переопределять governance configs или ADR.

### Archive Policy

- **Deprecated test docs**: Устаревшие testing docs MUST быть перемещены в
  `docs/99-archive/` с суффиксом `.archive.md`.
- **Historical test artifacts**: Исторические тестовые артефакты могут храниться в
  `reports/quality/` как evidence, но MUST NOT ссылаться из active docs как
  current guidance.
