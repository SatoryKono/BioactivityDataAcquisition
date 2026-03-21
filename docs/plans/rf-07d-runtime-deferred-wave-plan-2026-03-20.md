# RF-07D Deferred Runtime Paths Wave Plan

**Date:** 2026-03-20  
**Status:** Completed execution plan
**Primary rationale:** prepare a safe next wave for runtime/bootstrap `ProviderRegistry` migration without crossing the current safe boundary too early  
**Normative constraint:** preserve current bootstrap semantics and keep class-level compatibility available during this wave

## 0. Planning Contract

This plan covers only the runtime/bootstrap paths that were intentionally deferred from the first RF-07 wave.

It exists to do two things:

- keep the next migration step explicit and bounded;
- avoid accidentally expanding the already-successful datasource/factory migration into a larger bootstrap rewrite.

This wave must **not**:

- remove the default `ProviderRegistry`;
- rewrite bootstrap semantics in one pass;
- merge runtime migration with unrelated composition cleanups.

## 1. Deferred Scope

These files remain outside the current safe migration boundary and are the only intended scope for RF-07D:

- [`src/bioetl/composition/_pipeline_execution.py`](../../src/bioetl/composition/_pipeline_execution.py)
- [`src/bioetl/composition/bootstrap/runtime/pipeline.py`](../../src/bioetl/composition/bootstrap/runtime/pipeline.py)
- [`src/bioetl/composition/factories/pipeline/runner.py`](../../src/bioetl/composition/factories/pipeline/runner.py)
- [`src/bioetl/composition/runtime_builders/runner_builder.py`](../../src/bioetl/composition/runtime_builders/runner_builder.py)

## 2. Evidence Baseline

### 2.1. Why these paths were deferred

At the start of this wave, all four files relied on class-level provider bootstrap:

- `_pipeline_execution.py` calls `ProviderRegistry.ensure_loaded()`
- `bootstrap/runtime/pipeline.py` calls `ProviderRegistry.ensure_loaded()`
- `factories/pipeline/runner.py` calls `ProviderRegistry.ensure_loaded()`
- `runtime_builders/runner_builder.py` defaults `ensure_providers_loaded_fn` to `ProviderRegistry.ensure_loaded`

Unlike the datasource chain, these files sit directly on runtime lifecycle seams:

- bootstrap ordering,
- registry initialization timing,
- runner assembly,
- test doubles that patch `ProviderRegistry.ensure_loaded`.

That makes them higher-risk than the datasource and pipeline-factory slices already migrated.

### 2.2. Current protective test net

The existing regression net around this area is already meaningful:

- [`tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py`](../../tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py)
- [`tests/unit/composition/factories/pipeline/test_runner_factory.py`](../../tests/unit/composition/factories/pipeline/test_runner_factory.py)
- [`tests/unit/composition/runtime_builders/test_runner_builder.py`](../../tests/unit/composition/runtime_builders/test_runner_builder.py)

At the start of this wave, these tests encoded a real compatibility assumption:

- `ProviderRegistry.ensure_loaded()` is observable in bootstrap/runtime behavior;
- callers and tests are built around that shared seam.

This is good news for migration, but also a warning: the first runtime wave must change one seam at a time.

## 3. Main Interpretation

The deferred runtime zone should be migrated in the following order:

1. **Make provider bootstrap explicit as an injectable callable before changing ownership.**
   The current code already hints at this pattern in `runner_builder.py` through `ensure_providers_loaded_fn`.

2. **Prefer dependency threading over semantic rewrites.**
   The right first move is not "remove ensure_loaded", but "move the bootstrap trigger behind a smaller explicit runtime contract".

3. **Keep bootstrap and runner factory aligned.**
   If one path uses explicit registry/bootstrap injection and the other still hardcodes class-level calls, the result will be confusing and brittle.

## 4. Proposed Wave Breakdown

### RF-07D1. Extract A Runtime Provider Bootstrap Contract

- **Type:** refactor
- **Risk:** medium
- **Goal:** replace direct class-level `ProviderRegistry.ensure_loaded()` calls with a shared injected runtime bootstrap callable.

**Preferred shape**

- create one small composition-local helper such as `ensure_runtime_provider_registry_ready(...)` or equivalent;
- thread it through:
  - [`_pipeline_execution.py`](../../src/bioetl/composition/_pipeline_execution.py)
  - [`bootstrap/runtime/pipeline.py`](../../src/bioetl/composition/bootstrap/runtime/pipeline.py)
  - [`factories/pipeline/runner.py`](../../src/bioetl/composition/factories/pipeline/runner.py)
  - [`runtime_builders/runner_builder.py`](../../src/bioetl/composition/runtime_builders/runner_builder.py)

**Non-goal**

- do not make runtime code own a provider registry instance yet unless a specific caller already has one naturally.

### RF-07D2. Align Tests Around The New Runtime Seam

- **Type:** test adaptation
- **Risk:** low-medium
- **Goal:** move tests from patching raw `ProviderRegistry.ensure_loaded` to patching the new runtime bootstrap seam where appropriate.

**Priority tests**

- [`test_pipeline_bootstrap.py`](../../tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py)
- [`test_runner_factory.py`](../../tests/unit/composition/factories/pipeline/test_runner_factory.py)
- [`test_runner_builder.py`](../../tests/unit/composition/runtime_builders/test_runner_builder.py)

**Desired outcome**

- tests continue to prove provider bootstrap ordering;
- tests become less coupled to the class-level compatibility API.

### RF-07D3. Add A Narrow Runtime Ratchet

- **Type:** architecture/test guard
- **Risk:** low
- **Goal:** prevent new raw class-level `ProviderRegistry.ensure_loaded()` calls from appearing in the migrated runtime files.

**Suggested scope**

- only the four runtime files above;
- not a repo-wide ban.

### RF-07D4. Evaluate Instance Ownership Only After D1-D3

- **Type:** analysis/defer
- **Risk:** medium-high
- **Goal:** decide whether runtime callers should eventually receive an explicit `ProviderRegistry` instance, or whether an injected bootstrap callable is sufficient.

This decision should happen only after the runtime seam is explicit and test-stable.

## 5. Execution Order

1. Read and map current runtime provider bootstrap flow across the four deferred files.
2. Implement **RF-07D1** with the smallest shared runtime helper possible.
3. Update unit tests in **RF-07D2**.
4. Add the narrow runtime ratchet in **RF-07D3**.
5. Re-evaluate whether explicit runtime registry ownership is actually worth a second wave.

## 5.1. Current Implementation Status

### Completed

- **RF-07D1** completed:
  - [`_pipeline_execution.py`](../../src/bioetl/composition/_pipeline_execution.py) now uses `ensure_providers_loaded()`
  - [`bootstrap/runtime/pipeline.py`](../../src/bioetl/composition/bootstrap/runtime/pipeline.py) now uses `ensure_providers_loaded()`
  - [`factories/pipeline/runner.py`](../../src/bioetl/composition/factories/pipeline/runner.py) now injects the runtime bootstrap seam via `ensure_providers_loaded_fn`
  - [`runtime_builders/runner_builder.py`](../../src/bioetl/composition/runtime_builders/runner_builder.py) now defaults to the named loader helper instead of raw class-level registry access

- **RF-07D2** completed:
  - [`test_pipeline_bootstrap.py`](../../tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py)
  - [`test_runner_factory.py`](../../tests/unit/composition/factories/pipeline/test_runner_factory.py)
  - [`test_runner_builder.py`](../../tests/unit/composition/runtime_builders/test_runner_builder.py)
  - [`test_bootstrap_entrypoints.py`](../../tests/unit/composition/bootstrap/test_bootstrap_entrypoints.py)

These tests now assert the named runtime bootstrap seam rather than raw `ProviderRegistry.ensure_loaded()` patch points.

### Remaining

- **RF-07D3** completed: `tests/architecture/test_registry_contracts.py` now blocks raw `ProviderRegistry.ensure_loaded()` from reappearing in the four deferred runtime files.
- **RF-07D4** accepted/closed: explicit runtime `ProviderRegistry` instance ownership is not required for the current architecture. The wave stops at the named runtime bootstrap seam unless a new caller-driven case appears.

## 6. Verification Gates

Run at minimum:

- [`tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py`](../../tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py)
- [`tests/unit/composition/factories/pipeline/test_runner_factory.py`](../../tests/unit/composition/factories/pipeline/test_runner_factory.py)
- [`tests/unit/composition/runtime_builders/test_runner_builder.py`](../../tests/unit/composition/runtime_builders/test_runner_builder.py)
- [`tests/architecture/test_layer_dependencies.py`](../../tests/architecture/test_layer_dependencies.py)

If helper placement or imports move:

- re-run the narrow runtime ratchet test slice
- re-run any composition architecture tests already covering bootstrap boundaries

## 7. Main Risks And Controls

### Risk 1. Breaking bootstrap ordering semantics

**Control**

- keep `initialize_publication_type_classification(...)` ordering unchanged;
- preserve "providers loaded before pipeline registration" semantics through tests.

### Risk 2. Replacing one hidden seam with another

**Control**

- prefer one named runtime helper/callable over multiple ad hoc lambdas;
- keep the seam visible in signatures and tests.

### Risk 3. Over-migrating into explicit registry ownership too early

**Control**

- separate "explicit bootstrap seam" from "explicit instance ownership";
- decide on instance threading only after the first runtime wave lands cleanly.

## 8. Definition Of Done

RF-07D is complete only if:

1. Raw class-level runtime bootstrap usage is reduced behind one explicit runtime seam.
2. Target runtime tests are green and express the new seam directly.
3. A narrow ratchet protects the migrated runtime files from regressing to direct `ProviderRegistry.ensure_loaded()` calls.
4. Bootstrap/runtime behavior remains unchanged from a caller perspective.
5. The explicit runtime ownership question is either justified by new evidence or explicitly closed for the current wave.

The current wave is now closed successfully because:

- raw class-level runtime bootstrap usage has been removed from the deferred runtime files;
- the runtime seam is now named and injectable;
- runtime test coverage is aligned with that seam;
- bootstrap behavior remains green.
- the runtime ratchet is in place;
- explicit runtime registry ownership has been intentionally closed for now by [`DEC-provider-registry-runtime-stop-at-named-bootstrap-seam`](../reports/evidence/provider-registry-runtime-ownership/04-decisions/DECISIONS.yaml).

## 9. Recommended Immediate Start

RF-07D no longer has an immediate implementation start recommendation.

Why:

- the runtime-only wave has already landed;
- the regression net and ratchet are already in place;
- any future reopening should begin from a fresh caller-driven evidence case, not from a standing implementation backlog.
