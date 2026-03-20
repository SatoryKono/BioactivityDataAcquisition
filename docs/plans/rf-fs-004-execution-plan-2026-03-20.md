# RF-FS-004 Execution Plan

**Date:** 2026-03-20  
**Status:** Active, implementation in progress  
**Primary baseline:** `docs/99-archive/plans/rf-fs-2026-03/RF-FS-004-baseline-2026-03-19.md`
**Goal:** normalize config topology so the ownership flow reads clearly as `configs -> infrastructure -> domain -> composition`, while preserving the current YAML corpus and avoiding behavior drift.

## 0. Current Status

`RF-FS-004` is no longer a pure planning item. Several safe slices are already implemented locally and verified:

1. The deleted internal bridge `src/bioetl/infrastructure/config_load_api.py` is gone and guarded against reintroduction.
2. First-party `src` imports for `load_pipeline_config` and `load_source_config` now use canonical owner modules instead of the `bioetl.infrastructure.config` package barrel.
3. Canonical ownership for `DomainConfigResolver` moved from `composition/factories/pipeline/config_resolution.py` to `src/bioetl/infrastructure/config/domain_config_resolver.py`.
4. Canonical ownership for the pipeline registry inventory moved from `composition/factories/pipeline/configs.py` to `src/bioetl/composition/factories/pipeline/registry_manifest.py`.
5. Compatibility-freeze guards now protect the removed bridge, the moved resolver seam, and the `pipeline.configs` compatibility shim.

That means the remaining work is no longer about obvious compat cleanup. The remaining work is about structural ownership inside the live config path.

## 1. Problem Statement

The codebase still spreads config concerns across four active layers:

- `configs/` holds the YAML artifacts.
- `src/bioetl/infrastructure/config/` owns reading, normalization, staged loading, DQ resolution, contract policy loading, and schema-to-domain mapping.
- `src/bioetl/infrastructure/schemas/` owns validated file-shape models and Silver schema definitions.
- `src/bioetl/domain/config/` owns semantic runtime/domain configuration objects.
- `src/bioetl/composition/factories/pipeline/` still owns a mixed registry inventory that includes transformer references, Arrow schema references, Pandera schema references, and factory-facing config tuples.

The topology is therefore better than it was at baseline, but still not clean. The main unresolved smells now are:

- `registry_manifest.py` is a legitimate composition assembly manifest, but it still concentrates transformer and schema references that must remain assembly-only.
- `pipeline_config_loader.py` is still broader than the staged flow around it.
- the `infrastructure/schemas` vs `domain/config` boundary is mostly correct, but it still needed an explicit role ledger before deeper cleanup.

## 2. Scope Snapshot

### Key files and current roles

| File | LOC | Current role | Ownership concern |
| --- | ---: | --- | --- |
| `src/bioetl/composition/factories/pipeline/configs.py` | 8 | compatibility shim | must remain compat-only |
| `src/bioetl/composition/factories/pipeline/registry_manifest.py` | 326 | canonical pipeline registry manifest | must stay assembly-only, not become a second config catalog |
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
- `registry_manifest.py` is the canonical owner for the composition pipeline registry inventory.
- `bioetl.infrastructure.config` remains a public package surface, but internal `src` code should prefer canonical owner modules for loader symbols.
- `composition/factories/pipeline/config_resolution.py` is now a compatibility seam, not the behavioral owner.
- `composition/factories/pipeline/configs.py` is now a compatibility seam, not the behavioral owner.

## 5. Wave 4A Role Ledger

The following ledger records the dominant owner role for every top-level module in the active config-topology scope. Roles used here:

- `package-surface`: sanctioned package barrel or public surface
- `settings-surface`: settings-facing public surface
- `reader`: direct file or asset loading
- `normalizer`: compatibility or shape normalization
- `validator`: validation-focused loader behavior
- `schema-shape`: validated infrastructure file shape
- `storage-schema`: storage-facing schema definition
- `mapping`: schema-to-domain conversion
- `domain-model`: semantic runtime or domain config
- `registry-manifest`: composition-owned assembly inventory
- `wiring`: assembly or runtime construction helper
- `compat`: explicit compatibility shim or facade

### `src/bioetl/infrastructure/config`

| Module | Dominant role | Status | Notes |
| --- | --- | --- | --- |
| `__init__.py` | `package-surface` | retain | public config package barrel with lazy exports |
| `_base.py` | `settings-surface` | mixed | owns Settings surface plus `get_pipeline_config` convenience |
| `_dq_config_layers.py` | `reader` | retain | internal hierarchical DQ layer reading helpers |
| `_dq_config_normalization.py` | `normalizer` | retain | DQ file-shape normalization |
| `_dq_config_validation_merge.py` | `normalizer` | retain | DQ validation-list merge strategy |
| `_yaml_settings_source.py` | `reader` | retain | YAML-backed settings source |
| `base_config_loader.py` | `reader` | retain | shared YAML read and merge foundation |
| `config_ci_contract.py` | `package-surface` | retain | CI/docs/scripts contract constants |
| `contract_policy_loader.py` | `reader` | retain | typed contract policy file loading |
| `converters.py` | `mapping` | retain | canonical schema-to-domain mapping seam |
| `domain_config_resolver.py` | `mapping` | retain | canonical YAML + DQ -> domain bridge |
| `dq_config_loader.py` | `validator` | mixed | broad DQ hierarchy loader and merge orchestrator |
| `field_group_loader.py` | `reader` | retain | field-group asset loading |
| `filter_config_loader.py` | `validator` | retain | filter hierarchy loading and merge |
| `pipeline_config_api.py` | `reader` | retain | canonical staged pipeline loader entrypoint |
| `pipeline_config_loader.py` | `validator` | mixed | broad enrichment loader; main Wave 4C hotspot |
| `pipeline_normalizers.py` | `normalizer` | retain | pipeline config normalization helpers |
| `pipeline_payload_normalization.py` | `normalizer` | retain | payload normalization boundary for staged flow |
| `publication_type_classification_loader.py` | `reader` | retain | JSON classification asset loading |
| `source_config_loader.py` | `reader` | retain | canonical source config loading pipeline |

### `src/bioetl/infrastructure/schemas`

| Module | Dominant role | Status | Notes |
| --- | --- | --- | --- |
| `__init__.py` | `package-surface` | retain | package barrel for infrastructure schemas |
| `_composite_config_merge_schema.py` | `schema-shape` | retain | composite merge-related file shape |
| `base_schemas.py` | `compat` | retain | stable facade over split base schema modules |
| `base_schemas_chembl.py` | `schema-shape` | retain | shared config schema primitives |
| `base_schemas_pubchem.py` | `schema-shape` | retain | shared filter and gold schema primitives |
| `composite_config.py` | `schema-shape` | retain | composite pipeline config file schema |
| `composite_config_base.py` | `schema-shape` | retain | shared composite config schema pieces |
| `composite_validation.py` | `schema-shape` | retain | composite validation-focused schema pieces |
| `dq_config.py` | `schema-shape` | retain | standalone DQ config file schema |
| `dq_report_config.py` | `schema-shape` | retain | DQ report config schema |
| `filter_config.py` | `schema-shape` | retain | standalone filter config schema |
| `pipeline_config.py` | `compat` | retain | pipeline config schema facade |
| `pipeline_config_common.py` | `compat` | retain | common schema facade |
| `pipeline_config_common_schemas.py` | `schema-shape` | retain | non-provider pipeline config schema parts |
| `pipeline_config_dq.py` | `compat` | retain | DQ schema facade extracted from pipeline config |
| `pipeline_config_provider.py` | `schema-shape` | retain | provider or source pipeline config schema parts |
| `pipeline_contract_policy.py` | `schema-shape` | retain | typed contract-policy schema |
| `silver.py` | `compat` | retain | stable Silver schema facade |
| `silver_chembl.py` | `compat` | retain | ChEMBL Silver schema facade |
| `silver_chembl_core.py` | `storage-schema` | retain | core ChEMBL Silver schemas |
| `silver_chembl_extended.py` | `storage-schema` | retain | extended ChEMBL Silver schemas |
| `silver_compounds.py` | `storage-schema` | retain | PubChem and UniProt Silver schemas |
| `silver_publications.py` | `storage-schema` | retain | publication Silver schemas |
| `source_config.py` | `schema-shape` | retain | source config schema |

### `src/bioetl/domain/config`

| Module | Dominant role | Status | Notes |
| --- | --- | --- | --- |
| `__init__.py` | `package-surface` | retain | public domain-config barrel |
| `_converters.py` | `domain-model` | retain | internal enum and sequence helpers for dataclasses |
| `base_provider.py` | `domain-model` | retain | semantic base provider value objects |
| `dq.py` | `domain-model` | retain | DQ runtime config and rule descriptors |
| `memory.py` | `domain-model` | retain | memory runtime config |
| `pipeline.py` | `domain-model` | retain | canonical semantic pipeline config |
| `runtime.py` | `domain-model` | retain | CLI/runtime execution config |
| `table.py` | `domain-model` | retain | table and key config |
| `validation.py` | `domain-model` | retain | validation rule value objects |

### `src/bioetl/composition/factories/pipeline`

| Module | Dominant role | Status | Notes |
| --- | --- | --- | --- |
| `__init__.py` | `package-surface` | retain | package barrel and import guidance |
| `_creation_wiring.py` | `wiring` | retain | internal pipeline creation assembly |
| `assembler.py` | `wiring` | retain | GenericPipeline factory assembly |
| `config_resolution.py` | `compat` | retain | compat shim over canonical `domain_config_resolver.py` |
| `config_types.py` | `registry-manifest` | retain | tuple shape for assembly manifest |
| `configs.py` | `compat` | retain | compat shim over `registry_manifest.py` |
| `construction.py` | `compat` | retain | sanctioned aggregate seam for construction helpers |
| `construction_types.py` | `wiring` | retain | protocol contracts for construction helpers |
| `contract_validator.py` | `wiring` | mixed | preflight validation tied to manifest and contract policy loading |
| `creation_api.py` | `compat` | retain | public facade over private creation helpers |
| `factory_method_helpers.py` | `wiring` | retain | GenericPipelineFactory helper wiring |
| `postrun_assembly.py` | `wiring` | retain | postrun service assembly |
| `registry.py` | `wiring` | retain | factory instantiation and registration |
| `registry_manifest.py` | `registry-manifest` | mixed | canonical assembly inventory; must stay assembly-only |
| `run_context_factory.py` | `wiring` | retain | run-context assembly |
| `runner.py` | `wiring` | retain | runner factory implementation |
| `runner_assembly.py` | `wiring` | retain | runner assembly helper |
| `transformer_builder.py` | `wiring` | retain | transformer construction helper |
| `transformer_dependencies.py` | `wiring` | retain | canonical composition-side dependency builders |

### Ledger Conclusions

1. `domain/config` is already in the desired shape and is not the main RF hotspot anymore.
2. `infrastructure/schemas` is mostly structurally correct; most modules are either `schema-shape`, `storage-schema`, or explicit facades.
3. The main remaining mixed owners in `infrastructure/config` are `_base.py`, `dq_config_loader.py`, and especially `pipeline_config_loader.py`.
4. The main remaining mixed owners in `composition/factories/pipeline` are `registry_manifest.py` and `contract_validator.py`, but both are acceptable only as assembly-time concerns.
5. `Wave 4B` no longer needs another manifest rename. That slice is already complete and can now focus on keeping the assembly manifest clean.

## 6. Remaining Hotspots

### Hotspot A. Pipeline registry inventory in composition

`src/bioetl/composition/factories/pipeline/registry_manifest.py` is now the canonical assembly manifest. It still mixes:

- pipeline registration inventory
- transformer class ownership references
- domain gold-schema references
- infrastructure Silver schema references
- Pandera schema references

This is acceptable only if the module is treated as a pure assembly manifest. The next cleanup step is not another rename; it is to make sure no new behavior or config semantics accrete there.

### Hotspot B. Split inside `infrastructure/config`

The package already has the right building blocks, but it still reads as a broad cluster:

- staged pipeline loading
- DQ hierarchy resolution
- converters
- contract-policy loading
- field-group loading
- settings handling

The next step is to make role boundaries explicit, not to rewrite behavior.

Current evidence boundary:

- `PipelineConfigLoader` should be retained as a sanctioned infrastructure
  convenience seam
- canonical ownership should stay centered on
  `pipeline_config_api.py` and `domain_config_resolver.py`
- deeper `Wave 4C` work should keep thinning the class rather than re-centering
  ownership around it

### Hotspot C. Boundary between `infrastructure/schemas` and `domain/config`

The remaining question is not whether both packages should exist, but whether their responsibilities are easy to read:

- `infrastructure/schemas` should express validated file shape or storage shape
- `domain/config` should express semantic runtime config

Any duplicated meaning or transport noise in `domain/config` should be removed only after the role ledger confirms it.

## 7. Execution Strategy

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
  - `package-surface`
  - `settings-surface`
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
- mixed-owner modules are explicitly identified before deeper cleanup

### Wave 4B. Composition Pipeline Cleanup

**Purpose:** reduce `composition/factories/pipeline` to wiring and registry concerns only.

**Primary file scope:**

- `src/bioetl/composition/factories/pipeline/registry_manifest.py`
- `src/bioetl/composition/factories/pipeline/config_types.py`
- `src/bioetl/composition/factories/pipeline/registry.py`
- `src/bioetl/composition/factories/pipeline/contract_validator.py`
- `src/bioetl/composition/factories/pipeline/configs.py` only if a compat seam adjustment is required
- any directly dependent tests

**Planned sub-slices:**

1. Keep `registry_manifest.py` as the canonical assembly manifest and treat `configs.py` as compat-only.
2. Keep `PipelineFactoryConfig` in composition only if it remains purely assembly-facing.
3. Avoid moving behavior and inventory in the same edit batch.
4. Decide whether any schema references in the manifest need clearer assembly-only documentation or extraction.

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
6. Retain `PipelineConfigLoader` only as a convenience surface unless later
   evidence proves it no longer adds integration value.

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

## 8. Suggested Safe Sequence

Implement in this order:

1. use the role ledger to finish `composition/factories/pipeline`
2. normalize `infrastructure/config`
3. tighten `domain/config` only if the ledger still reveals leakage
4. run the full wave-level gate

Do not start with `domain/config`. The remaining ambiguity still comes from `composition` and `infrastructure`, so domain cleanup should be last.

## 9. Verification Plan

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

## 10. Guardrails

- Do not change YAML corpus shape as part of ownership-only slices.
- Do not delete public surfaces without either a compat shim or an explicit plan note.
- Do not combine package moves with behavioral refactors.
- Prefer canonical owner modules in `src`, but preserve public package barrels when they are part of the supported surface.
- Treat `composition/factories/pipeline/config_resolution.py` as a compat seam unless a later wave explicitly deletes it.
- Treat `composition/factories/pipeline/configs.py` as a compat seam unless a later wave explicitly deletes it.

## 11. Definition Of Done

`RF-FS-004` is done only when all of the following are true:

- config ownership is readable by layer without tracing through historical shims
- `composition` no longer acts as a hidden config/schema owner
- `infrastructure/config` has explicit staged responsibilities
- `domain/config` contains semantic runtime config rather than file-shape noise
- architecture guards protect the new canonical owner paths
- full config-focused verification and wave-level architecture gates are green

## 12. Immediate Next Step

The next implementation step should be **Wave 4B focused cleanup**:

- keep `registry_manifest.py` and `contract_validator.py` strictly assembly-scoped
- then move to `Wave 4C`, where `pipeline_config_loader.py` and `_base.py` are the main ownership hotspots on the infrastructure side

The highest-signal remaining move is now inside `infrastructure/config`, not in another round of manifest renaming.
