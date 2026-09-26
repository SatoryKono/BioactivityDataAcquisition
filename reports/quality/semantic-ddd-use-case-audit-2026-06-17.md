# Semantic DDD and Use-Case Audit - 2026-06-17

Issue scope: #5316.

## Scope

This audit covers the architecture-debt closeout wave for #5306, #5312, #5313,
#5244, #5314, #5315, and #5316. It is intentionally scoped to the touched
runtime and evidence surfaces, not a full repository semantic audit.

Reviewed runtime surfaces:

- `src/bioetl/application/services/control_plane/manifest/diagnostics/base.py`
- `src/bioetl/application/services/control_plane/manifest/diagnostics/replay_readiness.py`
- `src/bioetl/application/services/control_plane/manifest/diagnostics/summary.py`
- `src/bioetl/application/services/control_plane/manifest/inspection_service.py`
- `src/bioetl/application/services/control_plane/manifest/inspection_result_model.py`
- `src/bioetl/application/services/control_plane/manifest/diagnostics/diagnostic_context.py`
- `src/bioetl/application/services/control_plane/manifest/diagnostics/replay_invariants/nested_mapping.py`
- `src/bioetl/application/services/control_plane/replay/_historical_snapshot_certification_modes.py`
- `src/bioetl/application/services/control_plane/replay/_historical_snapshot_materialization_modes.py`
- `src/bioetl/application/services/control_plane/workflow/execution_incremental_metadata.py`
- `src/bioetl/application/services/control_plane/workflow/execution_recording_context.py`
- `src/bioetl/composition/runtime_builders/_run_manifest_create_spec_support.py`
- `src/bioetl/composition/runtime_builders/_effective_config_artifact_builder_support.py`
- `src/bioetl/composition/runtime_builders/effective_config_artifact_builder.py`
- `tests/unit/application/services/test_checkpoint_execution_identity_alignment.py`
- `tests/unit/application/services/control_plane/test_helper_module_coverage.py`

## Architectural Facts

- `docs/02-architecture/01-domain-layer.md` defines the Domain layer as pure
  business logic, entities, value objects, aggregates, domain events, ports,
  and validation rules. It must not depend on Application, Infrastructure, or
  Interfaces.
- `docs/02-architecture/05-composition-layer.md` defines Composition as the
  root that assembles components across Domain, Application, and Infrastructure
  and performs dependency injection.
- `.importlinter` enforces the same directionality: Domain must not import
  other layers, Application must not import Composition, Infrastructure, or
  Interfaces, Composition must not import Interfaces, and Interfaces must not
  directly import Infrastructure.

## Findings

1. Domain purity is preserved for the touched surfaces.

   The edited application modules consume domain value/policy types where
   needed, but no touched Domain module imports Application, Composition,
   Infrastructure, or Interfaces. No domain behavior was moved into
   Composition.

2. Use-case ownership remains in Application.

   Control-plane manifest diagnostics, replay readiness projection,
   checkpoint execution identity projection, and historical replay helper
   classification remain under `bioetl.application.services`. These modules
   orchestrate control-plane use-case state and evidence projection; they do
   not instantiate infrastructure adapters or composition roots.

3. Composition changes remain composition-root work.

   The runtime-builder edits reduce compatibility-facade indirection by
   importing narrower support helpers directly inside
   `bioetl.composition.runtime_builders`. Composition importing Application
   and Domain contracts is allowed by the documented layer model because
   Composition owns wiring and bootstrap assembly.

4. Retained public entrypoints are API-governance debt, not DDD aggregate
   violations.

   The #5315 review keeps all 13 retained public seams because they are
   sanctioned public API paths or canonical model/use-case seams. This does
   not move domain invariants out of Domain or create cross-layer semantic
   ownership drift.

5. The new coverage anchors do not introduce production semantics.

   `tests/unit/application/services/control_plane/test_helper_module_coverage.py`
   exercises helper contracts and edge cases to remove unmeasured module
   warnings. It does not define runtime behavior or broaden production API
   ownership.

## Inferences

- Splitting diagnostics helpers lowers fan-in pressure without changing the
  semantic owner: diagnostics remain an Application control-plane use case.
- Direct imports from smaller runtime-builder support modules are safer than
  routing through broad facades because they make the composition dependency
  graph more explicit.
- The remaining retained entrypoint count should be managed by public API
  lifecycle review, not by DDD refactoring.

## Uncertainties

- This artifact is a scoped semantic audit for the touched architecture-debt
  wave. It does not claim to audit every BioETL pipeline or provider semantic
  path.
- Full historical replay semantics are validated by the reproducibility and
  golden-fixture suites; this audit only checks DDD/use-case placement for the
  modules touched by this closeout wave.

## Validation Evidence

- `python -m scripts.engineering.qa report-debt-governance-gates --check`:
  all 26 debt gates passed, including `hotspot_family_baseline_budget_warnings`
  and `module_coverage_unmeasured_modules`.
- `python -m scripts.engineering.qa report-module-coverage --check`: module
  coverage inventory is current and reports zero unmeasured modules.
- `python scripts/engineering/qa/generate_architecture_dependency_map.py --check`:
  generated dependency map is current.
- `python -m scripts.engineering.qa report-compatibility-importer-census --check`:
  retained public entrypoint census is current.

## Closeout Verdict

No DDD or use-case ownership regression was found in the touched surfaces. The
architecture-debt wave can close #5316 with this scoped artifact as the
required semantic DDD/use-case audit evidence.
