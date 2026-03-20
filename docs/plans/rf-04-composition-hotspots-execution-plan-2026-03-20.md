# RF-04 Composition Hotspots Execution Plan

**Date:** 2026-03-20
**Status:** Partially implemented, core slices verified
**Primary rationale:** decompose composition hotspots by actual seams and change coupling, not by file length alone
**Normative constraint:** [`RULES.md`](../00-project/RULES.md)

## 0. Planning Contract

This plan corrects the earlier framing of RF-04.

The repo explicitly warns against treating large files as monoliths by default. In particular, [`RULES.md`](../00-project/RULES.md) requires delegation analysis before asserting that a hotspot needs decomposition. For RF-04, this means:

- do not start from `wc -l`;
- start from repeated assembly patterns, change coupling, and mixed reasons to change;
- decompose only where new seams make navigation and future edits simpler.

Success for RF-04 is therefore not “fewer lines”.
Success is:
- fewer non-obvious change points,
- cleaner assembly ownership,
- lower duplication in real wiring paths,
- clearer navigation across `composition/`.

## 0.1. Implementation Closeout

RF-04 has now completed the intended core path:

- RF-04A completed as an explicit seam-analysis memo in [`rf-04a-composition-seam-map-2026-03-20.md`](rf-04a-composition-seam-map-2026-03-20.md)
- RF-04B completed for [`registration_biblio.py`](../../src/bioetl/composition/providers/registration_biblio.py)
- RF-04C completed for [`pipeline_builder.py`](../../src/bioetl/composition/factories/services/pipeline_builder.py)
- RF-04D remains intentionally deferred for [`composite_support_service_builders.py`](../../src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py)

Delivered structural changes:

- bibliographic provider request-profile resolution moved into [`_registration_biblio_profiles.py`](../../src/bioetl/composition/providers/_registration_biblio_profiles.py)
- [`registration_biblio.py`](../../src/bioetl/composition/providers/registration_biblio.py) now stays focused on provider registration and data-source facade wiring
- record-processor projection/config assembly moved into [`pipeline_record_processor_builder.py`](../../src/bioetl/composition/factories/services/pipeline_record_processor_builder.py)
- [`pipeline_builder.py`](../../src/bioetl/composition/factories/services/pipeline_builder.py) remains the public facade while delegating the extracted seam

Verification completed successfully for implemented slices:

- provider registration tests:
  - [`test_registration_biblio_profiles.py`](../../tests/unit/composition/providers/test_registration_biblio_profiles.py)
  - [`test_registration_data_sources.py`](../../tests/unit/composition/providers/test_registration_data_sources.py)
  - [`test_registration_biblio_provider_configs.py`](../../tests/unit/composition/providers/test_registration_biblio_provider_configs.py)
  - [`test_registration.py`](../../tests/unit/composition/providers/test_registration.py)
- provider registration architecture guards:
  - [`test_provider_registry_decomposition.py`](../../tests/architecture/test_provider_registry_decomposition.py)
  - [`test_compatibility_freeze_guards.py`](../../tests/architecture/test_compatibility_freeze_guards.py)
- pipeline builder / composition tests:
  - [`test_pipeline_record_processor_builder.py`](../../tests/unit/composition/factories/services/test_pipeline_record_processor_builder.py)
  - [`test_pipeline_builder_unit.py`](../../tests/unit/composition/factories/services/test_pipeline_builder_unit.py)
  - [`test_pipeline_builder_batch_executor.py`](../../tests/unit/composition/factories/services/test_pipeline_builder_batch_executor.py)
  - [`test_services_factory.py`](../../tests/unit/composition/factories/services/test_services_factory.py)
  - [`test_builder_unit.py`](../../tests/unit/composition/factories/services/test_builder_unit.py)
  - [`test_smoke_composition.py`](../../tests/smoke/test_smoke_composition.py)
  - [`test_layer_dependencies.py`](../../tests/architecture/test_layer_dependencies.py)

## 1. Scope Snapshot

### Hotspot files in scope

| File | Current role | Initial read |
| --- | --- | --- |
| [`src/bioetl/composition/providers/registration_biblio.py`](../../src/bioetl/composition/providers/registration_biblio.py) | bibliographic provider data-source creation and provider config assembly | already partially decomposed; best treated as closeout/hardening slice |
| [`src/bioetl/composition/factories/services/pipeline_builder.py`](../../src/bioetl/composition/factories/services/pipeline_builder.py) | pipeline-bound builder surface for processing, checkpointing, record processor, batch executor | strongest candidate for primary decomposition wave |
| [`src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py`](../../src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py) | composite runtime support bundles for execution, runtime management, merge dependencies | may already be sufficiently cohesive; requires evidence before refactor |

### Current-state observations

1. `registration_biblio.py` already has one real seam extracted.
   Adapter binding for bibliographic providers has already been moved to [`_registration_biblio_adapters.py`](../../src/bioetl/composition/providers/_registration_biblio_adapters.py). That lowers the value of using it as the main decomposition wave.

2. `pipeline_builder.py` contains multiple distinct assembly responsibilities.
   Current responsibilities include:
   - batch processing component assembly,
   - checkpoint manager creation,
   - record processor argument projection,
   - record processor config + validator construction,
   - batch executor assembly and dependency bundle construction.

3. `composite_support_service_builders.py` already exposes three coherent bundle-builders.
   Right now this file looks more like a structured bundle module than an obvious hotspot. It should not be decomposed unless we can prove mixed reasons to change or repeated wiring patterns elsewhere.

## 2. Existing Protective Test Net

### `registration_biblio.py`

- [`tests/unit/composition/providers/test_registration_data_sources.py`](../../tests/unit/composition/providers/test_registration_data_sources.py)
- [`tests/unit/composition/providers/test_registration_biblio_provider_configs.py`](../../tests/unit/composition/providers/test_registration_biblio_provider_configs.py)
- [`tests/unit/composition/providers/test_registration.py`](../../tests/unit/composition/providers/test_registration.py)
- [`tests/architecture/test_provider_registry_decomposition.py`](../../tests/architecture/test_provider_registry_decomposition.py)
- [`tests/architecture/test_compatibility_freeze_guards.py`](../../tests/architecture/test_compatibility_freeze_guards.py)

### `pipeline_builder.py`

- [`tests/unit/composition/factories/services/test_pipeline_builder_unit.py`](../../tests/unit/composition/factories/services/test_pipeline_builder_unit.py)
- [`tests/unit/composition/factories/services/test_pipeline_builder_batch_executor.py`](../../tests/unit/composition/factories/services/test_pipeline_builder_batch_executor.py)
- [`tests/unit/composition/factories/services/test_services_factory.py`](../../tests/unit/composition/factories/services/test_services_factory.py)
- [`tests/unit/composition/factories/services/test_builder_unit.py`](../../tests/unit/composition/factories/services/test_builder_unit.py)
- [`tests/smoke/test_smoke_composition.py`](../../tests/smoke/test_smoke_composition.py)

### `composite_support_service_builders.py`

- [`tests/unit/composition/bootstrap/runtime/test_composite_support_service_builders.py`](../../tests/unit/composition/bootstrap/runtime/test_composite_support_service_builders.py)
- [`tests/architecture/test_composite_cli_runtime_config_boundaries.py`](../../tests/architecture/test_composite_cli_runtime_config_boundaries.py)

Current implication:
- `registration_biblio` and `pipeline_builder` already have enough coverage to support small structural waves.
- `composite_support_service_builders` has targeted tests, but it should still remain behind an evidence gate because its current bundle boundaries already look cohesive.

## 3. RF Breakdown

### RF-04A. Seam Analysis And Delegation Map

- **Status:** completed
- **Type:** analysis
- **Layer:** composition
- **Risk:** low
- **Goal:** create a seam map for each target module before code edits.

**Deliverables**
- delegation map for the three hotspot files;
- list of repeated assembly patterns;
- list of distinct reasons to change;
- explicit recommendation: `refactor now`, `closeout only`, or `defer`.

**Expected decisions**
- `registration_biblio.py` = closeout candidate
- `pipeline_builder.py` = primary decomposition candidate
- `composite_support_service_builders.py` = evidence-gated candidate

### RF-04B. Registration Biblio Closeout Slice

- **Status:** completed
- **Type:** refactor
- **Layer:** composition/providers
- **Risk:** low
- **Goal:** finish the already-started seam extraction without widening the API surface.

**Allowed moves**
- extract shared HTTP data-source profile helpers;
- centralize provider-specific `extra_kwargs` assembly where it reduces repeated branch logic;
- keep provider registration contracts and exports stable.

**Not allowed**
- broad provider registration redesign;
- renaming public provider registration entry points;
- moving logic into a pile of underscore helpers without clearer ownership.

**Intended shape**
- `registration_biblio.py` stays as a thin provider-registration facade;
- provider-specific HTTP profile resolution becomes easier to follow;
- remaining duplication between PubMed / CrossRef / OpenAlex / Semantic Scholar setup paths is reduced.

### RF-04C. Main Decomposition Wave For Pipeline Builder

- **Status:** completed
- **Type:** refactor
- **Layer:** composition/factories/services
- **Risk:** medium
- **Goal:** split `pipeline_builder.py` along stable assembly seams.

**Candidate seams**
- batch processing component assembly
- record processor projection / argument mapping
- processor config + gold validator construction
- batch executor dependency assembly

**Preferred target shape**
- `pipeline_builder.py` remains the public facade for callers;
- 2-3 adjacent helper modules carry themed responsibilities;
- helper names are descriptive and navigable, not just `_helpers2.py`-style fragments.

**Not allowed**
- changing runtime semantics;
- moving half the file into generic “utils”;
- mixing this wave with unrelated `builder.py` or `runtime_managers.py` redesign unless the tests force a minimal touch.

### RF-04D. Evidence Gate For Composite Support Builders

- **Status:** deferred by explicit seam analysis
- **Type:** analysis-first
- **Layer:** composition/bootstrap/runtime
- **Risk:** medium if executed blindly, low if deferred
- **Goal:** decide whether this file is truly a hotspot or merely a large cohesive bundle-builder.

**Promote to implementation only if one of these is proven**
- one builder contains multiple independent change axes;
- repeated merge/runtime wiring is duplicated outside the file;
- a planned seam can be protected with targeted tests, not only architecture smoke checks.

**Default outcome**
- if the evidence is weak, explicitly defer this file out of RF-04 implementation scope.

## 4. Execution Order

RF-04 must run sequentially. Do not decompose multiple composition hotspots in parallel.

### Slice 0. Preflight

- confirm current tests still collect and pass for target seams;
- freeze the intended seam map before code changes;
- confirm no scope creep into unrelated composition packages.

### Slice 1. RF-04B

- perform the `registration_biblio` closeout;
- run targeted unit and architecture checks;
- optionally run docs/drift checks in parallel after the code slice is stable.

### Slice 2. RF-04C

- decompose `pipeline_builder.py` using the seam map from RF-04A;
- keep the facade stable;
- verify with focused tests first, then architecture slices.

### Slice 3. RF-04D

- only analytical pass by default;
- implement only if the evidence justifies one more safe slice.

## 5. Verification Gates

### After RF-04B

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/composition/providers/test_registration_data_sources.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/unit/composition/providers/test_registration_biblio_provider_configs.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/unit/composition/providers/test_registration.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_provider_registry_decomposition.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_compatibility_freeze_guards.py`

### After RF-04C

- `./.venv/Scripts/python.exe -m pytest -q tests/unit/composition/factories/services/test_pipeline_builder_unit.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/unit/composition/factories/services/test_pipeline_builder_batch_executor.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/unit/composition/factories/services/test_services_factory.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/unit/composition/factories/services/test_builder_unit.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/smoke/test_smoke_composition.py`

### Architecture / regression gates after each code slice

- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_layer_dependencies.py`
- relevant composition boundary / compatibility slices if touched
- docs/drift verification only when imports, paths, or contributor-facing contracts change

## 6. Main Risks And Controls

### Risk 1. Fragmentation into meaningless helper files

**Control**
- allow only helpers with one clear assembly responsibility;
- keep public navigation through a thin facade module;
- prefer 2-3 meaningful seams over many tiny modules.

### Risk 2. Silent orchestration behavior drift

**Control**
- add characterization assertions before moving logic when needed;
- keep public factories stable during the first wave;
- rely on focused composition tests before broader smoke/architecture passes.

### Risk 3. Refactoring a cohesive file just because it is visible

**Control**
- require evidence of mixed reasons to change for `composite_support_service_builders.py`;
- explicitly defer that file if evidence does not support a clean seam.

## 7. Definition Of Done

RF-04 is complete only if all of the following are true:

1. At least one key composition hotspot is decomposed along stable seams.
2. Assembly duplication or change coupling is reduced in a way that is visible in code ownership, not just line count.
3. `composition/` navigation becomes simpler:
   - thin facade,
   - clear helper names,
   - no helper sprawl.
4. No new architecture boundary regressions appear.
5. Targeted tests exist or are strengthened for the introduced seams.
6. `composite_support_service_builders.py` is either:
   - given an evidence-backed follow-up slice, or
   - explicitly deferred as cohesive enough for now.

## 8. Current Outcome

The executed path matched the intended sequence:

- start with **RF-04A + RF-04B**,
- use that low-risk slice to validate the seam-first approach,
- then complete RF-04C as the main decomposition wave,
- keep RF-04D deferred until stronger evidence appears.

This means RF-04 has already delivered the intended practical result:
- one provider-registration hotspot reduced to a cleaner facade,
- one composition/factory hotspot decomposed by actual assembly seams,
- one visible but cohesive candidate explicitly left out of churn-heavy refactoring.
