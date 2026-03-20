# RF-FS-005 Wave 1 Hotspot Execution Plan

**Date:** 2026-03-20
**Status:** Implemented locally, verification passed
**Primary baseline:** `docs/99-archive/plans/rf-fs-2026-03/RF-FS-005-baseline-2026-03-19.md`
**Wave goal:** close the remaining `cli_run_orchestration_service` cleanup and replace the misnamed ChEMBL `_pipelines.py` hotspot with an honest canonical module shape, without widening the blast radius beyond import/export seams.

## 0. Implementation Closeout

Wave 1 was implemented with the target shape defined below.

Delivered changes:

- `cli_run_orchestration_service.py` remains the behavioral owner and now documents its compatibility re-export role explicitly.
- CLI run-domain internals now use canonical model ownership for `RunExecutionRequest`.
- `tests/unit/application/services/test_cli_run_orchestration_service.py` locks in the intended re-export identity contract.
- `src/bioetl/application/pipelines/chembl/pipeline_types.py` is now the canonical owner for ChEMBL marker pipeline classes.
- `src/bioetl/application/pipelines/chembl/_pipelines.py` is now a thin compatibility shim.
- `tests/unit/application/pipelines/test_pipeline_registrations.py` treats `pipeline_types.py` as the primary owner path and verifies the `_pipelines.py` shim.
- Follow-up cleanup migrated remaining non-compat test imports from the service module to `cli_run_orchestration_models.py`.

Verification completed successfully:

- focused unit suite for CLI orchestration, ChEMBL pipeline registrations, and registry consistency;
- architecture suite: `test_transformer_signatures.py`, `test_forbidden_imports.py`, `test_layer_dependencies.py`;
- docs config guard: `scripts/docs/check_doc_links.py --configs`;
- type gate: `mypy --strict --no-incremental src/bioetl/`.

Additional note:

- A pre-existing `mypy` blocker in `src/bioetl/infrastructure/storage/delta/table_ops.py` (`no-redef`) was fixed so the wave-level type gate could close cleanly.

## 1. Scope Snapshot

### Hotspot files inspected

| File | LOC | Current role | Risk notes |
| --- | ---: | --- | --- |
| `src/bioetl/application/services/cli_run_orchestration_service.py` | 205 | CLI run orchestration service plus compatibility re-exports | Behavior is already narrow, but source and tests still import request/result symbols from this module. |
| `src/bioetl/application/services/cli_run_orchestration_models.py` | 48 | Request/result DTOs | Canonical owner for `RunExecutionRequest`, `RunPreparationResult`, `StartOffsetValidationResult`. |
| `src/bioetl/application/services/cli_run_orchestration_contracts.py` | 47 | Callable protocols for prepared run execution | Low LOC, but imported by the service and referenced in `TYPE_CHECKING` seams. |
| `src/bioetl/application/pipelines/chembl/_pipelines.py` | 98 | 14 thin `BasePipeline` subclasses | Low behavioral complexity, high import-contract sensitivity because tests hardcode this module path. |
| `src/bioetl/application/pipelines/chembl/__init__.py` | 111 | Public ChEMBL package export surface | Registry and architecture tests derive expected pipeline class inventory from this package. |

### Existing test coverage and seam inventory

The following test files were inspected directly and the combined verify set was collected successfully with `.venv`:

| Source seam | Existing owner tests / guards |
| --- | --- |
| `cli_run_orchestration_service.py` | `tests/unit/application/services/test_cli_run_orchestration_service.py` |
| CLI policy + run boundary | `tests/unit/interfaces/cli/commands/test_run_command_policy.py`, `tests/unit/interfaces/cli/test_cli_commands.py` |
| ChEMBL pipeline importability | `tests/unit/application/pipelines/test_pipeline_registrations.py` |
| ChEMBL pipeline behavior | `tests/unit/application/pipelines/test_chembl_pipelines.py`, `tests/unit/application/pipelines/chembl/` |
| Registry/package export consistency | `tests/unit/composition/factories/pipeline/test_registry_consistency.py` |
| Package-level architecture guard | `tests/architecture/test_transformer_signatures.py` |
| Layer boundaries | `tests/architecture/test_forbidden_imports.py`, `tests/architecture/test_layer_dependencies.py` |

Collected wave gate suite size:

- `674` tests collected across the selected unit and architecture files.

### Important current-state findings

1. CLI closeout is a compatibility problem, not a decomposition problem.
   `src/bioetl/interfaces/cli/commands/domains/run/command.py`, `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py`, and `src/bioetl/interfaces/cli/commands/domains/run/service_access.py` still depend on the service-layer public surface.
2. `cli_run_orchestration_service.py` still intentionally re-exports request/result/protocol symbols.
   Tests also import `RunExecutionRequest` and `RunPreparationResult` from this module, so removing re-exports in Wave 1 would expand scope unnecessarily.
3. ChEMBL `_pipelines.py` is not a logic hotspot anymore.
   It is now a naming and import-contract hotspot: fourteen empty marker classes in a private-looking module path.
4. The stable public contract for ChEMBL pipeline classes is the package surface, not `_pipelines.py`.
   `tests/unit/composition/factories/pipeline/test_registry_consistency.py` derives expected class inventory from `bioetl.application.pipelines.chembl.__all__`.

## 2. Concrete Wave 1 Decisions

### Decision A. CLI Wave 1 stays compatibility-preserving

Wave 1 will **not** remove compatibility re-exports from `cli_run_orchestration_service.py`.
It will only:

- keep models in `cli_run_orchestration_models.py`;
- keep callable protocols in `cli_run_orchestration_contracts.py`;
- keep orchestration behavior in `CliRunOrchestrationService`;
- harden tests and import paths so new code uses canonical owners, while existing compatibility seams remain intact.

Deferred out of Wave 1:

- deleting service-level re-exports;
- changing public imports in `tests/unit/interfaces/cli/test_cli_commands.py` and other compatibility-oriented tests unless needed for a failing seam;
- broad run-command package cleanup outside the inspected run domain.

### Decision B. ChEMBL Wave 1 uses a canonical named module plus compat shim

Wave 1 will **not** split fourteen pipeline classes into fourteen files.

Chosen target shape:

- introduce a canonical module `src/bioetl/application/pipelines/chembl/pipeline_types.py`;
- move the 14 marker pipeline classes there unchanged;
- update `src/bioetl/application/pipelines/chembl/__init__.py` to import from `pipeline_types.py`;
- keep `src/bioetl/application/pipelines/chembl/_pipelines.py` as a thin compatibility shim that re-exports from `pipeline_types.py`.

Why this shape is the safest:

1. The classes contain no per-entity behavior, so per-file decomposition would create file-count noise without reducing real complexity.
2. The problem called out in the baseline is dishonest naming, and `pipeline_types.py` fixes that directly.
3. A shim preserves existing imports from `_pipelines.py` while letting tests and new code migrate toward the canonical path gradually.

## 3. Safe Sequential Refactor Slices

Execution must stay sequential. Do not overlap CLI and ChEMBL edits in one batch.

### Slice 0. Preflight and baseline freeze

**Purpose:** confirm the working tree is clean and the planned verify set still collects before code changes.

**Files touched:** none

**Actions:**

- keep the current clean worktree as the pre-refactor baseline;
- collect the wave verification suite before editing;
- record the selected target shape in this plan as the execution contract.

**Exit criterion:** no unresolved ambiguity remains about Wave 1 target shape.

### Slice 1. CLI closeout hardening without contract shrinkage

**Purpose:** finish the service/models/contracts split as an internal ownership cleanup while preserving public compatibility.

**Primary file scope:**

- `src/bioetl/application/services/cli_run_orchestration_service.py`
- `src/bioetl/application/services/cli_run_orchestration_models.py`
- `src/bioetl/application/services/cli_run_orchestration_contracts.py`
- `src/bioetl/interfaces/cli/commands/domains/run/command.py`
- `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py`
- `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py`
- `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py`
- `src/bioetl/interfaces/cli/commands/domains/run/service_access.py`
- targeted CLI tests if assertions need to reflect canonical owner modules

**Allowed changes:**

- reorder or narrow imports so canonical modules use `models.py` and `contracts.py` directly where already intended;
- keep `CliRunOrchestrationService` focused on validation, request preparation, and execution orchestration;
- add or adjust tests that lock in the service/models/contracts split;
- retain compatibility re-exports from the service module.

**Not allowed in this slice:**

- deleting service-module exports used by compatibility seams;
- changing CLI command behavior;
- touching unrelated `run_all`, `health`, or bootstrap modules outside the inspected seam set.

**Exit criterion:** the run command still behaves the same, and canonical run-domain modules no longer rely on accidental mixed ownership.

### Slice 2. ChEMBL canonical module introduction

**Purpose:** create the honest canonical owner for ChEMBL pipeline marker classes.

**Primary file scope:**

- `src/bioetl/application/pipelines/chembl/pipeline_types.py` (new)
- `src/bioetl/application/pipelines/chembl/__init__.py`

**Allowed changes:**

- move the 14 pipeline class declarations verbatim into `pipeline_types.py`;
- keep docstrings and class names unchanged;
- update package exports to import the classes from `pipeline_types.py`.

**Not allowed in this slice:**

- changing transformer imports;
- renaming any pipeline class;
- editing registry factory logic.

**Exit criterion:** `bioetl.application.pipelines.chembl` becomes the canonical public path, backed by a clearly named owner module.

### Slice 3. Compatibility shim and import rewiring

**Purpose:** preserve legacy `_pipelines.py` imports while aligning tests and docs around the new canonical module.

**Primary file scope:**

- `src/bioetl/application/pipelines/chembl/_pipelines.py`
- `tests/unit/application/pipelines/test_pipeline_registrations.py`
- optional docstrings/comments in `src/bioetl/application/pipelines/chembl/__init__.py`

**Allowed changes:**

- convert `_pipelines.py` into a thin re-export shim from `pipeline_types.py`;
- update tests so the canonical path is the main assertion surface;
- keep at least one compatibility assertion proving `_pipelines.py` still exposes the expected classes.

**Not allowed in this slice:**

- removing `_pipelines.py` entirely;
- spreading direct imports to new external call sites before the shim exists.

**Exit criterion:** both canonical and compatibility imports work, with canonical coverage as the primary owner path.

### Slice 4. Final wave gate and cleanup check

**Purpose:** verify that the refactor stayed structural and did not introduce cross-layer or docs drift.

**Files touched:** only small cleanup if verification reveals path/doc/test fallout.

**Allowed changes:**

- import rewires needed to satisfy tests or type checking;
- docstring/comment updates that reflect the new canonical module name.

**Not allowed in this slice:**

- new behavioral refactors;
- opportunistic package reorganization outside the Wave 1 file list.

**Exit criterion:** all wave gates pass, and the resulting shape matches the two decisions above.

## 4. Verification Commands Per Slice

Use the project `.venv` commands below. These paths were verified for collection in the current environment.

### Slice 0

```bash
./.venv/Scripts/python.exe -m pytest --collect-only -q \
  tests/unit/application/services/test_cli_run_orchestration_service.py \
  tests/unit/interfaces/cli/commands/test_run_command_policy.py \
  tests/unit/interfaces/cli/test_cli_commands.py \
  tests/unit/application/pipelines/test_pipeline_registrations.py \
  tests/unit/application/pipelines/test_chembl_pipelines.py \
  tests/unit/composition/factories/pipeline/test_registry_consistency.py \
  tests/architecture/test_transformer_signatures.py \
  tests/architecture/test_forbidden_imports.py \
  tests/architecture/test_layer_dependencies.py
```

### Slice 1

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/unit/application/services/test_cli_run_orchestration_service.py \
  tests/unit/interfaces/cli/commands/test_run_command_policy.py \
  tests/unit/interfaces/cli/test_cli_commands.py
```

### Slice 2

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/unit/application/pipelines/test_chembl_pipelines.py \
  tests/unit/composition/factories/pipeline/test_registry_consistency.py \
  tests/architecture/test_transformer_signatures.py
```

### Slice 3

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/unit/application/pipelines/test_pipeline_registrations.py \
  tests/unit/application/pipelines/test_chembl_pipelines.py \
  tests/unit/composition/factories/pipeline/test_registry_consistency.py
```

### Slice 4

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
./.venv/Scripts/python.exe -m pytest -q \
  tests/architecture/test_forbidden_imports.py \
  tests/architecture/test_layer_dependencies.py
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## 5. Wave-Level Gates

Wave 1 is complete only if all gates below are green in the same working tree state.

### Gate A. Focused behavior and seam suite

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/unit/application/services/test_cli_run_orchestration_service.py \
  tests/unit/interfaces/cli/commands/test_run_command_policy.py \
  tests/unit/interfaces/cli/test_cli_commands.py \
  tests/unit/application/pipelines/test_pipeline_registrations.py \
  tests/unit/application/pipelines/test_chembl_pipelines.py \
  tests/unit/composition/factories/pipeline/test_registry_consistency.py
```

### Gate B. Architecture and package export safety

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/architecture/test_transformer_signatures.py \
  tests/architecture/test_forbidden_imports.py \
  tests/architecture/test_layer_dependencies.py
```

### Gate C. Documentation and typing

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## 6. Definition Of Done For This Wave

Wave 1 is done when all statements below are true:

1. `cli_run_orchestration_service.py` remains the behavioral owner of request validation/preparation/execution, but canonical data/protocol ownership stays in `models.py` and `contracts.py`.
2. No required compatibility import from the CLI run domain or existing tests is broken.
3. `src/bioetl/application/pipelines/chembl/pipeline_types.py` becomes the canonical owner for ChEMBL marker pipeline classes.
4. `src/bioetl/application/pipelines/chembl/_pipelines.py` stops being the real owner and becomes a compatibility shim only.
5. `bioetl.application.pipelines.chembl.__all__` remains stable from the perspective of registry and architecture tests.
6. All slice-level checks and all wave gates pass.

## 7. Explicit Non-Goals

These items stay out of Wave 1 even if they look adjacent:

- removing all service-module re-exports from the CLI orchestration service;
- splitting ChEMBL marker pipelines into 14 individual files;
- changing pipeline factory registration logic outside import rewiring;
- broad cleanup of other CLI command domains;
- opportunistic refactors in other provider packages.
