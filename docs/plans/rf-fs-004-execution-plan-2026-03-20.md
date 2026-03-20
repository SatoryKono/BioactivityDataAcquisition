# RF-FS-004 Execution Plan

**Date:** 2026-03-20  
**Status:** Active, implementation in progress  
**Primary baseline:** `docs/reports/RF-FS-004-baseline-2026-03-19.md`  
**Goal:** normalize config topology so the ownership flow reads clearly as `configs -> infrastructure -> domain -> composition`, while preserving the current YAML corpus and avoiding behavior drift.

## 0. Current Status

`RF-FS-004` is no longer a pure planning item. Two safe slices are already implemented locally and verified:

1. The deleted internal bridge `src/bioetl/infrastructure/config_load_api.py` is gone and guarded against reintroduction.
2. First-party `src` imports for `load_pipeline_config` and `load_source_config` now use canonical owner modules instead of the `bioetl.infrastructure.config` package barrel.
3. Canonical ownership for `DomainConfigResolver` moved from `composition/factories/pipeline/config_resolution.py` to `src/bioetl/infrastructure/config/domain_config_resolver.py`.
4. Compatibility-freeze guards now protect both the removed bridge and the moved resolver seam.

That means the remaining work is no longer about obvious compat cleanup. The remaining work is about structural ownership inside the live config path.

## 1. Problem Statement

The codebase still spreads config concerns across four active layers:

- `configs/` holds the YAML artifacts.
- `src/bioetl/infrastructure/config/` owns reading, normalization, staged loading, DQ resolution, contract policy loading, and schema-to-domain mapping.
- `src/bioetl/infrastructure/schemas/` owns validated file-shape models and Silver schema definitions.
- `src/bioetl/domain/config/` owns semantic runtime/domain configuration objects.
- `src/bioetl/composition/factories/pipeline/` still owns a mixed registry inventory that includes transformer references, Arrow schema references, Pandera schema references, and factory-facing config tuples.

The topology is therefore better than it was at baseline, but still not clean. The main unresolved smell is that `composition/factories/pipeline/configs.py` behaves like both a wiring artifact and a config/schema catalog.

## 2. Scope Snapshot

### Key files and current roles

| File | LOC | Current role | Ownership concern |
| --- | ---: | --- | --- |
| `src/bioetl/composition/factories/pipeline/configs.py` | 326 | pipeline registry inventory | co-locates wiring with schema ownership references |
| `src/bioetl/composition/factories/pipeline/config_types.py` | 26 | registry tuple shape | likely still acceptable in composition if it stays wiring-only |
| `src/bioetl/infrastructure/config/pipeline_config_api.py` | 189 | read -> normalize -> validate -> map pipeline YAML | canonical staged loader already exists |
| `src/bioetl/infrastructure/config/pipeline_config_loader.py` | 327 | DQ-aware config enrichment | infrastructure owner, but still broad |
| `src/bioetl/infrastructure/config/converters.py` | 145 | schema-to-domain mapping | canonical mapping seam |
| `src/bioetl/infrastructure/config/domain_config_resolver.py` | 33 | YAML + DQ -> domain config bridge | newly established canonical owner |
| `src/bioetl/domain/config/pipeline.py` | 126 | immutable semantic pipeline config | correct domain owner |

### Packages to normalize

- `src/bioetl/composition/factories/pipeline`
- `src/bioetl/infrastructure/config`
- `src/bioetl/infrastructure/schemas`
- `src/bioetl/domain/config`

### Out of scope for this RF

- changing YAML key shapes unless a move is impossible without it
- broad provider refactors
- `interfaces/cli` package narrowing
- `application/core` and `application/composite` package decomposition
- storage cleanup and orphan-wrapper review from other RFs

## 3. Target Ownership Model

### `configs/`

Owns only source artifacts and config corpus layout.

### `infrastructure/config`

Owns:

- reading files
- normalization/migration logic
- staged loading flows
- DQ/filter/contract policy resolution
- schema-to-domain mapping bridges

Must not become a second domain layer.

### `infrastructure/schemas`

Owns validated file-shape models and storage-facing schema assets.

Must not become a dumping ground for runtime semantics that belong in `domain/config`.

### `domain/config`

Owns immutable semantic config/value models used by runtime behavior.

Must not know about YAML sections, path layout, or compatibility normalization.

### `composition`

Owns only registry assembly and runtime wiring.

Must not be the canonical owner for:

- YAML shape
- normalization rules
- DQ resolution behavior
- schema catalogs that are not specific to assembly

## 4. What Is Already Settled

These decisions are already implemented and should be treated as fixed for the rest of `RF-FS-004`:

- `pipeline_config_api.py` is the canonical function-based pipeline YAML loading flow.
- `source_config_loader.py` is the canonical source config loading flow.
- `domain_config_resolver.py` is the canonical owner for YAML+DQ to domain-config resolution.
- `bioetl.infrastructure.config` remains a public package surface, but internal `src` code should prefer canonical owner modules for loader symbols.
- `composition/factories/pipeline/config_resolution.py` is now a compatibility seam, not the behavioral owner.

## 5. Remaining Hotspots

### Hotspot A. Pipeline registry inventory in composition

`src/bioetl/composition/factories/pipeline/configs.py` still mixes:

- pipeline registration inventory
- transformer class ownership references
- domain gold-schema references
- infrastructure Silver schema references
- Pandera schema references

This may be acceptable only if the module is treated as a pure assembly manifest. If it continues to look like a config catalog, it will keep pulling config semantics into composition.

### Hotspot B. Split inside `infrastructure/config`

The package already has the right building blocks, but it still reads as a broad cluster:

- staged pipeline loading
- DQ hierarchy resolution
- converters
- contract-policy loading
- field-group loading
- settings handling

The next step is to make role boundaries explicit, not to rewrite behavior.

### Hotspot C. Boundary between `infrastructure/schemas` and `domain/config`

The remaining question is not whether both packages should exist, but whether their responsibilities are easy to read:

- `infrastructure/schemas` should express validated file shape or storage shape
- `domain/config` should express semantic runtime config

Any duplicated meaning or transport noise in `domain/config` should be removed only after the role ledger confirms it.

## 6. Execution Strategy

Work this RF in four sequential waves. Do not overlap them in one batch.

### Wave 4A. Role Ledger and Boundary Freeze

**Purpose:** produce an exact ownership map before any deeper code moves.

**Files inspected:**

- all top-level modules in `src/bioetl/infrastructure/config`
- all top-level modules in `src/bioetl/infrastructure/schemas`
- all top-level modules in `src/bioetl/domain/config`
- all top-level modules in `src/bioetl/composition/factories/pipeline`

**Actions:**

- classify each module as one primary role:
  - `artifact-layout`
  - `reader`
  - `normalizer`
  - `validator`
  - `schema-shape`
  - `domain-model`
  - `mapping`
  - `registry-manifest`
  - `wiring`
  - `compat`
- flag modules whose current role is mixed or ambiguous
- record sanctioned canonical owners and sanctioned compat seams

**Expected output:**

- a role ledger section inside this plan or a follow-up inventory note

**Exit criterion:**

- every config-related module has one dominant owner role

### Wave 4B. Composition Pipeline Cleanup

**Purpose:** reduce `composition/factories/pipeline` to wiring and registry concerns only.

**Primary file scope:**

- `src/bioetl/composition/factories/pipeline/configs.py`
- `src/bioetl/composition/factories/pipeline/config_types.py`
- `src/bioetl/composition/factories/pipeline/registry.py`
- any directly dependent tests

**Planned sub-slices:**

1. Decide whether `configs.py` remains an assembly manifest or is split into:
   - a canonical manifest module in `composition`
   - thinner imported schema references owned elsewhere
2. Keep `PipelineFactoryConfig` in composition only if it remains purely assembly-facing.
3. Avoid moving behavior and inventory in the same edit batch.
4. If needed, introduce a better-named manifest module and leave a thin compat re-export from `configs.py`.

**Rules:**

- do not move live behavior into composition
- do not expand public package surface unless a compat shim is intentional
- do not change pipeline runtime behavior during manifest cleanup

**Exit criterion:**

- composition retains only registry manifest and wiring concerns

### Wave 4C. Infrastructure Config Normalization

**Purpose:** make `infrastructure/config` read like a staged pipeline instead of a broad toolbox.

**Primary file scope:**

- `pipeline_config_api.py`
- `pipeline_payload_normalization.py`
- `pipeline_config_loader.py`
- `converters.py`
- `domain_config_resolver.py`
- supporting DQ/filter loaders as needed

**Planned sub-slices:**

1. Confirm the canonical staged pipeline:
   `read -> normalize -> validate -> map -> resolve-domain`
2. Separate pure staged-loading entrypoints from enrichment helpers.
3. Keep `converters.py` as the canonical mapping seam unless a narrower name is clearly better.
4. Make `domain_config_resolver.py` the obvious bridge from validated YAML to semantic config.
5. Fence any lingering package-barrel or historical helper usage with architecture guards.

**Rules:**

- preserve YAML corpus behavior
- preserve cache behavior unless explicitly revalidated
- avoid touching settings code unless it blocks ownership clarity

**Exit criterion:**

- infrastructure config flow is readable as a staged pipeline with clear owners

### Wave 4D. Domain Config Tightening

**Purpose:** ensure `domain/config` contains semantic runtime config only.

**Primary file scope:**

- `src/bioetl/domain/config/*.py`
- optionally `src/bioetl/domain/composite/config*` only when clearly connected

**Planned sub-slices:**

1. Review each domain config module for YAML/file-shape leakage.
2. Remove transport or compatibility concerns that belong in infrastructure.
3. Keep value objects immutable and runtime-facing.
4. Update mapping tests only after ownership is explicit.

**Rules:**

- do not fold runtime semantics back into infrastructure models
- do not turn domain config into a mirror of `PipelineYamlConfig`

**Exit criterion:**

- domain config expresses meaning, not file shape

## 7. Suggested Safe Sequence

Implement in this order:

1. finalize the role ledger
2. clean `composition/factories/pipeline`
3. normalize `infrastructure/config`
4. tighten `domain/config`
5. run the full wave-level gate

Do not start with `domain/config`. The remaining ambiguity still comes from `composition` and `infrastructure`, so domain cleanup should be last.

## 8. Verification Plan

### After every local slice

Use the smallest relevant batch first:

```bash
./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_compatibility_freeze_guards.py
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

### Composition cleanup slices

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/unit/composition/factories/pipeline/test_creation_wiring.py \
  tests/unit/composition/factories/pipeline/test_factory_method_helpers.py \
  tests/unit/composition/factories/pipeline/test_pipeline_factory_construction.py \
  tests/unit/composition/bootstrap/runtime/test_pipeline_bootstrap.py \
  tests/unit/composition/runtime_builders/test_runner_builder.py
```

### Infrastructure config slices

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/unit/infrastructure/test_config_dynamic.py \
  tests/unit/infrastructure/config/test_pipeline_config_loader.py \
  tests/unit/infrastructure/config/test_pipeline_config_loader_extended.py \
  tests/architecture/test_source_config_usage.py \
  tests/architecture/test_config_golden_master.py \
  tests/architecture/test_config_strict_keys.py
```

### Full wave gate

```bash
./.venv/Scripts/python.exe -m pytest -q tests/unit/infrastructure/config
./.venv/Scripts/python.exe -m pytest -q \
  tests/architecture/test_config_ci_invariants.py \
  tests/architecture/test_config_strict_keys.py \
  tests/architecture/test_config_golden_master.py
./.venv/Scripts/python.exe -m pytest -q \
  tests/architecture/test_forbidden_imports.py \
  tests/architecture/test_layer_dependencies.py
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## 9. Guardrails

- Do not change YAML corpus shape as part of ownership-only slices.
- Do not delete public surfaces without either a compat shim or an explicit plan note.
- Do not combine package moves with behavioral refactors.
- Prefer canonical owner modules in `src`, but preserve public package barrels when they are part of the supported surface.
- Treat `composition/factories/pipeline/config_resolution.py` as a compat seam unless a later wave explicitly deletes it.

## 10. Definition Of Done

`RF-FS-004` is done only when all of the following are true:

- config ownership is readable by layer without tracing through historical shims
- `composition` no longer acts as a hidden config/schema owner
- `infrastructure/config` has explicit staged responsibilities
- `domain/config` contains semantic runtime config rather than file-shape noise
- architecture guards protect the new canonical owner paths
- full config-focused verification and wave-level architecture gates are green

## 11. Immediate Next Step

The next implementation step should be **Wave 4A -> Wave 4B preflight**:

- build the role ledger for `composition/factories/pipeline`, `infrastructure/config`, `infrastructure/schemas`, and `domain/config`
- then decide whether `src/bioetl/composition/factories/pipeline/configs.py` stays as an explicit assembly manifest or becomes a compat shim over a narrower canonical manifest

That is the highest-signal move now that the obvious compat bridges are already cleaned up.
