# RF-07 ProviderRegistry Migration Plan

**Date:** 2026-03-20  
**Status:** In progress  
**Primary rationale:** reduce hidden dependency on the default `ProviderRegistry` without breaking the bootstrap/test ecosystem  
**Normative constraint:** compatibility class-level API remains available during this wave

## 0. Planning Contract

RF-07 is a **late, cautious migration**, not a singleton-removal campaign.

The current architecture already has two realities:

- an **instance-scoped** path via `create_provider_registry()` and APIs that accept `provider_registry: ProviderRegistry | None`;
- a **wide compatibility layer** via class-level dispatch on `ProviderRegistry.*`.

That means the risk is not "the registry is still global everywhere". The real risk is subtler:
- hidden reliance on the default registry is still present in production bootstrap paths;
- new code can still accidentally expand that reliance because the class-level API is convenient and widely visible;
- tests currently normalize that compatibility behavior, which makes premature removal expensive.

So RF-07 must:
- inventory current registry consumers before changing behavior;
- migrate one narrow production path to an explicit registry instance where the conceptual ownership is already local;
- add a ratchet so new production call sites do not silently increase class-level dependency.

RF-07 must **not**:
- remove the default registry in one wave;
- break class-level compatibility for tests or bootstrap;
- mix provider-registry migration with unrelated composition refactors.

## 1. Evidence Baseline

### 1.1. What the current implementation already supports

1. `ProviderRegistry` is already instance-scoped internally.
   See [`provider_registry.py`](../../src/bioetl/composition/providers/provider_registry.py):
   - `ProviderRegistry.__init__()` owns a local `ProviderStore`;
   - `create_provider_registry()` returns a fresh isolated instance;
   - `ensure_provider_registry_ready(registry)` already exists as a helper for explicit instances.

2. The class-level API is an intentional compatibility seam.
   The registry methods are wrapped by `DefaultRegistryMethod`, and `ensure_loaded()` routes through `get_default_provider_registry()`.

3. An explicit-registry path already exists in production composition code.
   The strongest example is [`data_source_factory.py`](../../src/bioetl/composition/factories/datasource/data_source_factory.py):
   - `get_data_source_creator(..., provider_registry=...)`
   - `DataSourceFactory.create(..., provider_registry=...)`
   - `_resolve_provider_registry(...)`

This is important because RF-07 does not need to invent a new model; it needs to expand an existing one carefully.

### 1.2. Current production call-site map

#### A. Direct class-level production usage

Current production files still calling class-level `ProviderRegistry` methods directly:

- [`src/bioetl/composition/_pipeline_execution.py`](../../src/bioetl/composition/_pipeline_execution.py)
  - `ProviderRegistry.ensure_loaded()`
- [`src/bioetl/composition/bootstrap/runtime/pipeline.py`](../../src/bioetl/composition/bootstrap/runtime/pipeline.py)
  - `ProviderRegistry.ensure_loaded()`
- [`src/bioetl/composition/factories/pipeline/runner.py`](../../src/bioetl/composition/factories/pipeline/runner.py)
  - `ProviderRegistry.ensure_loaded()`
- [`src/bioetl/composition/runtime_builders/runner_builder.py`](../../src/bioetl/composition/runtime_builders/runner_builder.py)
  - default DI arg `ensure_providers_loaded_fn = ProviderRegistry.ensure_loaded`
- [`src/bioetl/composition/factories/datasource/http_client.py`](../../src/bioetl/composition/factories/datasource/http_client.py)
  - `ProviderRegistry.ensure_loaded()`
  - `ProviderRegistry.is_registered()`
  - `ProviderRegistry.list_providers()`
  - `ProviderRegistry.get_http_config()`

#### B. Production code already prepared for explicit registry injection

- [`src/bioetl/composition/factories/datasource/data_source_factory.py`](../../src/bioetl/composition/factories/datasource/data_source_factory.py)
  - `provider_registry: ProviderRegistry | None` is already accepted by public helpers/factories.
- [`src/bioetl/composition/providers/registration.py`](../../src/bioetl/composition/providers/registration.py)
  - `register_all_providers(registry=...)` already supports explicit target registries.

#### C. Compatibility-heavy test surface

Tests exercise the class-level API broadly:

- decorator/registration expectations in
  [`test_decorators.py`](../../tests/unit/composition/providers/test_decorators.py)
  and
  [`test_provider_registry.py`](../../tests/unit/composition/providers/test_provider_registry.py)
- bootstrap/runtime mocks against `ProviderRegistry.ensure_loaded` in
  [`test_runner_factory.py`](../../tests/unit/composition/factories/pipeline/test_runner_factory.py),
  [`test_runner_builder.py`](../../tests/unit/composition/runtime_builders/test_runner_builder.py),
  [`test_bootstrap_entrypoints.py`](../../tests/unit/composition/bootstrap/test_bootstrap_entrypoints.py),
  [`test_pipeline_bootstrap.py`](../../tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py)

This confirms the migration blast radius is currently dominated by test and bootstrap conventions, not by business logic.

## 2. Main Interpretation

The evidence points to three practical conclusions:

1. **The most urgent problem is not "remove ProviderRegistry class methods".**  
   The real problem is that production composition still has several hidden default-registry entry points, especially in runtime/bootstrap and HTTP client configuration lookup.

2. **The best first migration slice is not bootstrap.**  
   Bootstrap and runner assembly still rely on class-level `ensure_loaded()` as a shared convenience seam. Changing that first would create a larger compatibility blast radius than necessary.

3. **The best first migration slice is a datasource/factory chain.**  
   That area already accepts explicit registry instances and has the right conceptual locality: provider lookup and adapter creation belong together there.

## 3. RF Breakdown

### RF-07A. Inventory And Classification

- **Type:** analysis
- **Risk:** low
- **Goal:** produce an explicit call-site ledger before changing behavior.

**Required output**
- classify each `ProviderRegistry.ensure_loaded / is_registered / create_adapter / build_data_source_creator / get_http_config` usage as:
  - production path,
  - compatibility path,
  - test convenience / fixture seam.

**Recommended artifact**
- short evidence note or table in `docs/plans/` or evidence workspace capturing:
  - file,
  - method used,
  - category,
  - proposed disposition (`migrate`, `retain`, `defer`).

**Why it matters**
- without this, later migration work will keep arguing from intuition instead of actual blast radius.

### RF-07B. First Explicit Registry Slice In Datasource Chain

- **Type:** refactor
- **Risk:** medium-low
- **Goal:** make one production path prefer an explicit registry instance without breaking compatibility callers.

**Best first target**
- datasource factory / HTTP client configuration chain

**Preferred scope**
- [`data_source_factory.py`](../../src/bioetl/composition/factories/datasource/data_source_factory.py)
- [`http_client.py`](../../src/bioetl/composition/factories/datasource/http_client.py)
- only the minimum number of upstream callers needed to thread a registry instance through

**Rationale**
- `data_source_factory.py` already models explicit registry ownership well;
- `http_client.py` still hides default-registry access for config lookup;
- moving this seam to explicit injection gives a real testability win with relatively small blast radius.

**Target shape**
- `HttpClientFactory.create_for_provider(..., provider_registry: ProviderRegistry | None = None)` or equivalent explicit resolver injection
- config lookup in HTTP client path goes through an explicit registry when available
- fallback to default registry remains intact for compatibility callers

**Non-goals**
- no bootstrap overhaul in this slice
- no removal of class-level classmethods

### RF-07C. Ratchet Against New Production Class-Level Call Sites

- **Type:** architecture guard
- **Risk:** low
- **Goal:** stop the legacy seam from expanding while migration is in progress.

**Preferred guard shape**
- a targeted search-based architecture test that forbids *new* production usage of class-level `ProviderRegistry` access in selected directories once the first explicit path is in place

**Suggested initial scope**
- guard only the freshly migrated area first, for example:
  - `src/bioetl/composition/factories/datasource/`

This is intentionally narrower than a repo-wide ban.

**Why narrow first**
- bootstrap/runtime still knowingly use compatibility access;
- a narrow ratchet avoids false failures while still preventing regression in the area we just improved.

### RF-07D. Later Bootstrap / Runner Migration (Deferred)

- **Type:** defer
- **Risk:** medium-high
- **Goal:** only after earlier slices land safely, consider reducing default-registry usage in:
  - [`_pipeline_execution.py`](../../src/bioetl/composition/_pipeline_execution.py)
  - [`bootstrap/runtime/pipeline.py`](../../src/bioetl/composition/bootstrap/runtime/pipeline.py)
  - [`factories/pipeline/runner.py`](../../src/bioetl/composition/factories/pipeline/runner.py)
  - [`runtime_builders/runner_builder.py`](../../src/bioetl/composition/runtime_builders/runner_builder.py)

**Defer reason**
- these paths are closer to bootstrap lifecycle semantics and test fixtures;
- the compatibility seam is more entrenched there;
- RF-07 should establish a successful explicit pattern before attempting this zone.

## 4. Execution Order

1. **RF-07A** — produce the call-site ledger and classify consumers.
2. **RF-07B** — migrate one datasource/factory chain to explicit registry preference.
3. **RF-07B verification** — targeted unit tests plus composition architecture checks.
4. **RF-07C** — add a narrow ratchet in the migrated area.
5. **RF-07D** — explicitly defer bootstrap/runtime migration until later evidence supports it.

## 4.1. Current Implementation Status

### Completed

- **RF-07A** completed via
  [`rf-07a-provider-registry-call-site-ledger-2026-03-20.md`](rf-07a-provider-registry-call-site-ledger-2026-03-20.md)
- **RF-07B** first datasource slice completed:
  - [`http_client.py`](../../src/bioetl/composition/factories/datasource/http_client.py) now supports explicit `provider_registry`
  - [`_registration_contracts.py`](../../src/bioetl/composition/providers/_registration_contracts.py) now threads explicit registry into HTTP client creation as well as adapter creation
- **RF-07C** initial narrow ratchet completed:
  - [`test_registry_contracts.py`](../../tests/architecture/test_registry_contracts.py) now prevents new class-level `ProviderRegistry.*` calls from reappearing in `composition/factories/datasource/`
- Adjacent factory seam expanded without entering bootstrap/runtime:
  - [`assembler.py`](../../src/bioetl/composition/factories/pipeline/assembler.py) accepts explicit `provider_registry`
  - [`contract_validator.py`](../../src/bioetl/composition/factories/pipeline/contract_validator.py) threads explicit registry into `get_data_source_creator(...)`

### Explicitly deferred

- [`_pipeline_execution.py`](../../src/bioetl/composition/_pipeline_execution.py)
- [`bootstrap/runtime/pipeline.py`](../../src/bioetl/composition/bootstrap/runtime/pipeline.py)
- [`factories/pipeline/runner.py`](../../src/bioetl/composition/factories/pipeline/runner.py)
- [`runtime_builders/runner_builder.py`](../../src/bioetl/composition/runtime_builders/runner_builder.py)

These paths were intentionally deferred from the first RF-07 wave. They are now tracked by the dedicated runtime plan:

- [`rf-07d-runtime-deferred-wave-plan-2026-03-20.md`](rf-07d-runtime-deferred-wave-plan-2026-03-20.md)

### Runtime deferred wave status

- **RF-07D1** completed: deferred runtime files now use the named loader helper `ensure_providers_loaded()` or an injected `ensure_providers_loaded_fn` seam instead of raw class-level `ProviderRegistry.ensure_loaded()`.
- **RF-07D2** completed: runtime/bootstrap test slices now assert the new seam directly.
- **RF-07D3** completed: narrow runtime ratchet now protects the four deferred runtime files from regressing to raw `ProviderRegistry.ensure_loaded()` access.
- **RF-07D4** accepted/closed: the project will stop at the named runtime bootstrap seam for now and reopen explicit runtime registry instance ownership only if a new caller-driven case appears. See [`DEC-provider-registry-runtime-stop-at-named-bootstrap-seam`](../reports/evidence/provider-registry-runtime-ownership/04-decisions/DECISIONS.yaml).

## 5. Verification Gates

### For RF-07A

- no code changes required beyond artifact cleanliness
- `git diff --check` on the plan/evidence artifact

### For RF-07B

Run targeted tests around datasource/provider creation:

- [`tests/unit/composition/factories/datasource/test_data_source_registry.py`](../../tests/unit/composition/factories/datasource/test_data_source_registry.py)
- [`tests/unit/composition/factories/datasource/test_data_sources.py`](../../tests/unit/composition/factories/datasource/test_data_sources.py)
- provider-registry unit slice in
  [`tests/unit/composition/providers/test_provider_registry.py`](../../tests/unit/composition/providers/test_provider_registry.py)

Add bootstrap safety slices if caller threading reaches them:

- [`tests/unit/composition/factories/pipeline/test_runner_factory.py`](../../tests/unit/composition/factories/pipeline/test_runner_factory.py)
- [`tests/unit/composition/runtime_builders/test_runner_builder.py`](../../tests/unit/composition/runtime_builders/test_runner_builder.py)

### For RF-07C

- targeted architecture test for the migrated subtree
- existing architecture regression slices if imports or boundaries change:
  - [`tests/architecture/test_layer_dependencies.py`](../../tests/architecture/test_layer_dependencies.py)

## 6. Main Risks And Controls

### Risk 1. Accidental compatibility break in tests/bootstrap

**Control**
- keep class-level `ProviderRegistry.*` methods fully working through RF-07;
- migrate only one explicit production path first;
- avoid changing bootstrap semantics in the first wave.

### Risk 2. "Migration" that only moves complexity sideways

**Control**
- require a real explicit registry thread through one factory chain;
- do not accept helper churn without reducing hidden default-registry access.

### Risk 3. Ratchet introduced too broadly, causing noisy failures

**Control**
- scope the first guard to the migrated subtree only;
- leave bootstrap/runtime compatibility paths temporarily allowed.

### Risk 4. Confusing test convenience with production dependency

**Control**
- maintain the production / compatibility / test-convenience classification as part of RF-07A;
- do not use test count alone as a reason to postpone all migration.

## 7. Definition Of Done

RF-07 is complete only if:

1. There is an explicit map of current registry consumers.
2. At least one real production path prefers an explicit `ProviderRegistry` instance.
3. Class-level compatibility remains available during the transition.
4. A ratchet exists so the migrated production area does not accumulate new class-level registry access.
5. Targeted tests confirm no hidden regressions in adapter creation / bootstrap lifecycle.

Full removal of the default registry is **not** required for RF-07.

The current wave should already be considered successful if:

- the explicit registry path is present in datasource and adjacent pipeline-factory code,
- compatibility classmethods still work,
- the narrow ratchet protects the migrated subtree,
- bootstrap/runtime remains unchanged and green.

The broader RF-07 program is now effectively split into:

- completed datasource/pipeline-factory reduction work (`RF-07A/B/C`);
- completed runtime seam clarification and protection (`RF-07D1/D2/D3`);
- accepted closeout decision for runtime ownership (`RF-07D4`).

## 8. Recommended Immediate Start

RF-07 is now at a stable stopping point.

Why:
- the datasource/factory explicit-registry path is in place;
- the runtime/bootstrap seam is explicit, test-covered, and ratcheted;
- the remaining runtime ownership question is now closed by decision unless new evidence appears.
- bootstrap/runtime remains the higher-risk area and should stay deferred;
- this sequencing converts RF-07 from a vague "remove singleton seam" idea into a controlled reduction of hidden default-registry dependency.
