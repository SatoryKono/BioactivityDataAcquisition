# RF-FS Remaining Backlog Execution Plan

Status: reconciled context after Wave 0  
Date: 2026-03-20

## Wave 0 Reconciliation Update

This document remains useful as a structural input, but it is no longer the
primary execution queue for refactor work.

After the Wave 0 reconciliation pass:

- the authoritative cross-plan execution order now lives in
  `docs/plans/consolidated-master-refactor-plan-2026-03-20.md`
- this file should be read as a supporting structural backlog snapshot and
  detail source for `RF-FS-*` interpretation
- `RF-FS-004` should no longer be read as a broad unresolved baseline item;
  it now acts mainly as implemented-local context plus remaining config-seam
  constraints
- `RF-FS-006a` and `RF-FS-006b` should be interpreted through evidence-led
  candidate review and conservative cleanup rules, not as a blind delete queue
- runtime `ProviderRegistry` ownership questions should remain aligned with the
  deferred/watchpoint framing captured outside this document rather than being
  pulled forward as an implicit structural prerequisite

Do not use the historical ordering below as a competing master program. Use it
only to understand what unresolved `RF-FS-*` themes were absorbed into the
consolidated plan.

## Purpose

This plan updates the remaining `RF-FS-*` backlog against the current codebase state after the completed structural waves:

- `RF-FS-005a`
- `RF-FS-005b`
- `RF-FS-001a`
- `RF-FS-001b`
- `RF-FS-001c`

The goal is to prevent the next refactor phases from following stale assumptions. Several original baseline candidates are now either already resolved, already decomposed, or no longer the highest-risk interpretation of the code.

## Current Code Snapshot

As of 2026-03-20, the main remaining structural hotspots are still visible in the code:

- `src/bioetl/application/core`: 50 top-level Python modules
- `src/bioetl/application/composite`: 45 top-level Python modules
- `src/bioetl/interfaces/cli/commands`: 37 top-level Python modules
- `src/bioetl/infrastructure/config`: 19 top-level Python modules
- `src/bioetl/infrastructure/schemas`: 24 top-level Python modules
- `src/bioetl/domain/config`: 9 top-level Python modules
- `src/bioetl/composition/factories/pipeline`: 18 top-level Python modules

Important current-state corrections versus the older baselines:

- `application/services` is no longer the main ownership hotspot.
- `composition` cycle cleanup is materially advanced and should now be treated as a completed prerequisite for config-topology work.
- `infrastructure/storage` is no longer fully flat; it already has `bronze/`, `silver/`, `gold/`, `metadata/`, `delta/`, and `support/` subdomains.
- several `RF-FS-006` candidates are not orphaned in practice and must be audited by status, not deleted by filename intuition.

## Historical Remaining Order At Consolidation Time

1. `RF-FS-004`
2. `RF-FS-006a`
3. `RF-FS-006b`
4. `RF-FS-002a`
5. `RF-FS-002b`
6. `RF-FS-002c`
7. `RF-FS-002d`
8. `RF-FS-003`
9. `RF-FS-007`

## Current Interpretation After Reconciliation

- `RF-FS-004`: substantially implemented locally; remaining relevant pieces are
  now ownership constraints and context for broader composition/config work.
- `RF-FS-006a` / `RF-FS-006b`: remain valid only as evidence-led review and
  conservative cleanup subtracks.
- `RF-FS-007`: no longer a near-term structural prerequisite; deferred runtime
  ownership watchpoint rules take precedence.
- `RF-FS-002a` through `RF-FS-002d` and `RF-FS-003`: still useful as thematic
  decomposition ideas, but they should be scheduled through the consolidated
  master plan rather than revived as a separate queue.

## RF-FS-004

### Updated Scope

The problem is now sharply localized: config ownership is still spread across `configs/`, `infrastructure/config`, `infrastructure/schemas`, `domain/config`, and `composition/factories/pipeline`. The strongest code-level evidence is the coexistence of:

- `src/bioetl/infrastructure/config/pipeline_config_loader.py`
- `src/bioetl/infrastructure/config/pipeline_payload_normalization.py`
- `src/bioetl/infrastructure/config/converters.py`
- `src/bioetl/composition/factories/pipeline/configs.py`
- `src/bioetl/composition/factories/pipeline/config_types.py`

The composition package already went through cycle cleanup, so this RF should no longer wait for more graph stabilization. The key issue is that `composition/factories/pipeline/configs.py` still acts like a mixed ownership module: registry inventory, schema references, transformer references, and factory-facing config data are all co-located there. That keeps `composition` too close to config semantics.

### Planned Waves

Wave 4A: build a role ledger for every config-related module in `domain`, `infrastructure`, and `composition`, marking each as `schema-shape`, `loader`, `normalizer`, `domain-model`, `mapping`, or `wiring`.

Wave 4B: reduce `composition/factories/pipeline` to registry and wiring concerns only. Move any config-shape or schema-owner concerns out of composition if they are not truly assembly-only.

Wave 4C: normalize `infrastructure/config` into explicit read, normalize, validate, and map stages. Keep YAML corpus behavior stable while improving package readability.

Wave 4D: review `domain/config` and `domain/composite` to ensure only semantic config/value models remain there.

### Verification

- `./.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/config -q`
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_config_ci_invariants.py tests/architecture/test_config_strict_keys.py tests/architecture/test_config_golden_master.py -q`
- `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs`
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_forbidden_imports.py tests/architecture/test_layer_dependencies.py -q`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

The config flow reads clearly as `configs -> infrastructure -> domain -> composition`, and `composition` no longer owns config normalization or schema-shape logic.

## RF-FS-006a

### Updated Scope

This is now a confirmation task, not a delete task. The codebase already disproves several baseline assumptions:

- `composition/bootstrap/runtime/composite_support_service_builders.py` is used and has dedicated tests.
- `composition/bootstrap/runtime/dq_bootstrap.py` is used and has dedicated tests.
- `composition/bootstrap/runtime/logger_bootstrap.py` is used and has dedicated tests.
- `composition/factories/storage/storage_factory.py` is a live canonical shim over `factory.py`.
- the metadata helper chain still has active value and cannot be treated as dead by path alone.

The most likely false-positive area in the old baseline is `domain/transformations/`, where file-level scans are misleading because some symbols are consumed through the package root. `coercion` and `hashing` are clearly live. `quality` now needs symbol-level review rather than blanket orphan labeling.

### Planned Waves

Wave 6A-1: create a candidate ledger with columns for `module`, `why flagged`, `direct imports`, `package-root imports`, `tests`, `docs`, `runtime/patch usage`, and `proposed status`.

Wave 6A-2: review `composition/bootstrap/runtime` candidates with unit-test and runtime-entrypoint context, not just static grep.

Wave 6A-3: review `composition/factories/storage` with re-export and smoke-test awareness.

Wave 6A-4: review metadata wrapper chain and `domain/transformations` at symbol granularity.

### Verification

- `rg -n "<module>|<symbol>" src tests docs configs`
- targeted unit suites per candidate cluster
- `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

Every candidate has an explicit status: `dead`, `retain`, `merge`, or `dynamic`, with evidence and cluster-local verification attached.

## RF-FS-006b

### Updated Scope

This task should now be treated as a narrow implementation phase driven entirely by the ledger from `RF-FS-006a`. The code already demonstrates why this matters: one true orphan storage wrapper was removable, while multiple other candidates that once looked suspicious are still active. So the cleanup phase must be selective and evidence-backed.

The likely categories will differ:

- `dead`: delete directly with absence guards
- `merge`: fold wrapper logic into a canonical owner module
- `retain`: keep as sanctioned entrypoint or compatibility seam
- `dynamic`: do not delete; document and fence

The metadata helper chain is the highest-value merge candidate, but only if review confirms that the application layer helper does not add irreplaceable assembly policy. Storage and runtime wrappers should be handled only when call sites, tests, and doc mentions all support the change.

### Planned Waves

Wave 6B-1: execute all `dead` deletions first, one file or seam at a time.

Wave 6B-2: execute low-risk `merge` candidates where canonical ownership is already explicit and test coverage exists.

Wave 6B-3: convert `retain` outcomes into documented policy or architecture freeze guards.

Wave 6B-4: update compatibility inventory or shim-usage tests where cleanup changes the sanctioned surface.

### Verification

- candidate-local unit suites
- `./.venv/Scripts/python.exe -m pytest tests/architecture -q`
- `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

Confirmed dead code is removed, thin wrappers are either merged or explicitly retained, and no runtime/bootstrap/storage regressions appear.

## RF-FS-002a

### Updated Scope

`application/core` remains a top-tier hotspot with 50 top-level modules. The current code already reveals natural decomposition seams:

- execution lifecycle and runner path
- batch loop and executor support
- processing and record orchestration
- writer and tracing support
- specialized data sources and source mixins

The biggest modules reinforce this reading. High-density files include `field_specs.py`, `_filtered_data_source_mixins.py`, `batch_executor_loop_helpers.py`, `dict_transformers.py`, `runner.py`, and `batch_executor.py`. This is no longer a question of whether a split is needed; the question is how to split without introducing micro-packages or behavior churn.

### Planned Waves

Wave 2A-1: produce a target package map, likely around `execution`, `processing`, `writing`, `datasources`, and `transform`.

Wave 2A-2: move low-blast-radius internal helpers first: protocols, loop helpers, tracing helpers, and mixin modules.

Wave 2A-3: relocate major owners like `batch_executor`, `runner`, and `record_processor` only after support modules are stable.

Wave 2A-4: preserve root-package re-exports during the transition so import churn remains controlled.

### Verification

- `./.venv/Scripts/python.exe -m pytest tests/unit/application/core -q`
- architecture gates for imports/layers
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

The root of `application/core` becomes meaningfully narrower and the package geography reflects execution-lifecycle responsibilities instead of historical accumulation.

## RF-FS-002b

### Updated Scope

`application/composite` still has 45 top-level modules and mixes preflight, planning, dependency joins, merger internals, runtime models, and validation helpers. The code is already segmented enough to show bounded themes, but not enough to make navigation easy.

The strongest current clusters are:

- preflight and preflight reporting/rules
- dependency join and planner logic
- merger and merger mixin stack
- composite runner/runtime support

This package is more structurally mature than the old baseline implied, so the correct goal is not to invent themes but to codify the themes the code already expresses.

### Planned Waves

Wave 2B-1: isolate the preflight cluster into a coherent subpackage.

Wave 2B-2: isolate dependency and join planning modules into a dedicated subpackage.

Wave 2B-3: isolate merger implementation detail around the retained public entrypoint `merger.py`.

Wave 2B-4: review runner/runtime support for either a fourth subpackage or a thinner root-level surface.

### Verification

- `./.venv/Scripts/python.exe -m pytest tests/unit/application/composite -q`
- architecture import/layer checks
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

Composite behavior remains in the application layer, but the package stops presenting planning, preflight, merger internals, and runtime coordination as one flat directory.

## RF-FS-002c

### Updated Scope

This task must be reinterpreted. `infrastructure/storage` is no longer truly flat; it already contains `bronze`, `silver`, `gold`, `metadata`, `delta`, and `support` subdomains. The remaining issue is that the root package still carries heavy public owners and shared primitives:

- `bronze_writer.py`
- `silver_writer.py`
- `gold_writer.py`
- `metadata_builder.py`
- `metadata_writer.py`
- `base_delta_writer.py`

So the target is no longer "create subpackages" but "finish the split and clarify the root public surface."

### Planned Waves

Wave 2C-1: define the intended root-level API for `infrastructure.storage`.

Wave 2C-2: move or slim shared Delta primitives so they read as internal infrastructure building blocks rather than root-package neighbors of public writers.

Wave 2C-3: normalize metadata ownership so `metadata_builder` and `metadata_writer` are clearly the public owners over `metadata/*` implementation modules.

Wave 2C-4: keep writer entrypoints stable while gradually reducing root-level implementation density.

### Verification

- `./.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/storage -q`
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_pipeline_storage_compat_shim_usage.py -q`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

The root package reads as a clear storage public surface, while most operational detail lives under the existing subdomains.

## RF-FS-002d

### Updated Scope

`interfaces/cli/commands` has already started to split through `commands/domains/*`, but the root still holds 37 Python modules. The codebase therefore no longer needs domain discovery; it needs canonicalization of the root versus domain-owned logic.

The current hotspot is coexistence:

- root command files such as `run.py`, `run_all.py`, `export.py`, `quarantine.py`
- root support files such as `run_helpers.py`, `run_command_policy.py`, `export_support.py`
- newer domain-owned packages under `commands/domains/*`

This means the wave should optimize for surface discipline, not for directory creation.

### Planned Waves

Wave 2D-1: finish the `run` and `run_all` migration so root-level files act as thin entrypoints or shims only.

Wave 2D-2: group `export`, `quarantine`, `health`, and `maintenance` support logic under their domain packages where appropriate.

Wave 2D-3: classify `_compat.py` and any remaining root support modules as either retained shim or migration target.

### Verification

- `./.venv/Scripts/python.exe -m pytest tests/unit/interfaces/cli tests/unit/interfaces/cli/commands -q`
- architecture checks for import boundaries
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

The commands root becomes a thin routing layer, and command behavior lives under domain packages instead of drifting back into the flat root.

## RF-FS-003

### Updated Scope

This task is no longer about broad test scarcity. The current code has substantial test surfaces for:

- `application/core`
- `application/composite`
- `infrastructure/storage`
- `infrastructure/adapters`

The remaining problem is ownership clarity, not simple presence. Some modules still have only clustered coverage, some have direct tests, and `domain/ports` already correctly leans on architecture and contract tests instead of mirror unit tests.

### Planned Waves

Wave 3-1: build a source-to-test ledger for priority modules with statuses:
`direct_test`, `cluster_owner`, `arch_only`, `covered_but_implicit`.

Wave 3-2: close only the `covered_but_implicit` and `no-clear-owner` gaps in `application/core`, `application/composite`, and `infrastructure/storage`.

Wave 3-3: review provider adapter suites at the package level, not by forcing one test file per helper module.

Wave 3-4: preserve the current policy for `domain/ports`, where architecture and typing checks remain the primary ownership mechanism.

### Verification

- local cluster suites for touched areas
- `./.venv/Scripts/python.exe -m pytest tests/architecture -q`
- `./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/`

### Done When

Behavior-heavy modules have an obvious owning suite, clustered suites are understandable, and `domain/ports` does not accumulate low-value mirror tests.

## RF-FS-007

### Updated Scope

This remains a valid late governance wave. Adapter package asymmetry is still real, and current architecture tests do not fully define the intended provider package contract. Real package shapes now look like this:

- `chembl`: expanded entrypoint plus models and fetch support
- `crossref`: flow-heavy client package with models and query helpers
- `pubchem`: client plus flow, models, mapping, policy helper
- `pubmed`: retained dual-entrypoint situation (`client.py` and `pubmed_client.py`)
- `semanticscholar`: retained dual-entrypoint situation (`client.py` and `adapter.py`)
- `uniprot`: large specialized package with many provider-local collaborators

So the task is not symmetry; it is formalization.

### Planned Waves

Wave 7-1: define the adapter package contract in architectural terms:
required entrypoint, allowed extensions, forbidden smells.

Wave 7-2: align this contract with retained-entrypoint policy already enforced for PubMed and Semantic Scholar.

Wave 7-3: classify each provider package into a small set of allowed structural forms.

Wave 7-4: update `tests/architecture/test_adapter_contracts.py` so it checks real policy rather than incidental file naming.

### Verification

- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_adapter_contracts.py -q`
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_retained_adapter_entrypoint_policy.py -q`
- `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs`
- targeted provider unit suites when package layout changes

### Done When

Provider package structure is predictable, documented, architecture-tested, and no longer governed by folklore.
