______________________________________________________________________

Version: 1.0.0
Status: proposed
Class: implementation_plan
Owner: BioETL Team
Last updated: 2026-06-01

______________________________________________________________________

# ChemblBaseline Refactor Plan

Дата snapshot: `2026-06-01`

## Executive Summary

`chembl_baseline` уже shipped как canonical workflow, а не как design-only
surface. В репозитории уже есть:

- декларативный workflow в `configs/workflows/chembl_baseline.yaml`;
- runner и transform orchestration в `src/bioetl/application/services/`;
- control-plane с manifest/ledger/state и destructive recovery;
- local-only locking через `MemoryLock`;
- unit/integration test coverage по config, runner, reconciliation и CLI-adjacent
  surfaces.

Поэтому целевой refactor для `main` должен идти как **hardening program**, а не
как повторная реализация workflow с нуля.

## Plan Intent

Этот план закрывает пять практических направлений:

1. workflow-level dry-run safety;
2. dedicated CI smoke lane для `chembl_baseline`;
3. GitHub Actions hardening и policy enforcement;
4. выравнивание declared DAG semantics с реальными data dependencies;
5. подготовку к optional parallel/distributed evolution без нарушения
   `ADR-010` local-only runtime boundary.

## Non-Goals

- Не переводить исполнение реального data-bearing `chembl_baseline` в
  GitHub-hosted runners.
- Не заменять `MemoryLock` на distributed coordination backend в текущей фазе.
- Не включать parallel execution до завершения dry-run/recovery hardening.
- Не менять shipped destructive semantics без явного fail-closed operator
  contract.

## Evidence Anchors

- `configs/workflows/chembl_baseline.yaml`
- `src/bioetl/application/services/workflow_runner_service.py`
- `src/bioetl/application/services/workflow_transform_service.py`
- `src/bioetl/application/workflow/transforms/reconcile_foreign_keys.py`
- `src/bioetl/infrastructure/storage/workflow_foreign_key_reconciliation.py`
- `src/bioetl/interfaces/cli/commands/workflow.py`
- `src/bioetl/application/services/control_plane/workflow/execution_service.py`
- `src/bioetl/infrastructure/locking/memory_lock.py`
- `.github/actions/setup-python-uv/action.yml`
- `.github/workflows/tests.yml`
- `.github/workflows/contract-tests.yml`
- `scripts/engineering/repo/check_github_actions_runtime_policy.py`
- `docs/03-guides/workflows.md`
- `docs/05-operations/runbooks/workflow-control-plane.md`
- `docs/05-operations/verification/ci-failure-triage-2026-05-05.md`
- `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`

## Current-State Findings

1. `chembl_baseline` сейчас объявлен линейно: `assay -> target -> publication ->
   reconcile_target -> reconcile_publication`, хотя первый reconciliation step
   использует только `chembl_assay` и `chembl_target`.
2. `WorkflowRunnerService` обходит `config.topological_step_ids` обычным
   последовательным циклом; независимые DAG vertices не выполняются параллельно.
3. `SilverForeignKeyReconciliationAdapter` делает
   `self.silver_writer.clear(..., dry_run=False)`, то есть destructive transform
   не уважает workflow CLI dry-run expectation.
4. В `.github/workflows/tests.yml` есть общие lanes и `control-plane-e2e`, но нет
   отдельного baseline-specific smoke workflow.
5. Runtime policy checker
   `scripts/engineering/repo/check_github_actions_runtime_policy.py` покрывает
   только ограниченный allowlist, а в текущих surfaces остаются tag-based refs:
   `astral-sh/setup-uv@v7` и `actions/github-script@v7`.
6. Workflow docs прямо фиксируют local-only locking через `MemoryLock`, поэтому
   remote/distributed execution не должен появиться как “побочный эффект”
   baseline CI hardening.

## Workstreams

| Priority | Stream | Outcome |
| --- | --- | --- |
| `P0` | Dry-run safety contract | destructive transforms fail-closed or preview-only under workflow dry-run |
| `P0` | Baseline CI smoke lane | dedicated `chembl_baseline` smoke workflow with JUnit artifacts |
| `P1` | DAG dependency cleanup | declared dependencies reflect real transform inputs |
| `P1` | Recovery and CLI smoke hardening | baseline-specific coverage for `status`, `resume-last`, `repair-steps`, dry-run policy |
| `P1` | Actions security hardening | all external actions pinned by SHA, checker covers all external `uses:` |
| `P2` | Cache and runner-image refinement | deterministic cache invalidation and fixed runner image |
| `P3` | Optional bounded parallel runner | layer-based parallel mode for independent non-destructive steps |
| `P3` | Distributed lock seam preparation | explicit future seam for non-local execution without changing current runtime policy |

## Stream 1: Workflow-Level Dry-Run Safety

**Priority:** `P0`

### Goal

Сделать `chembl_baseline --dry-run` операционно предсказуемым: destructive
workflow transforms не должны silently mutate Silver state.

### Primary Surfaces

- `src/bioetl/interfaces/cli/commands/workflow.py`
- `src/bioetl/application/services/workflow_runner_service.py`
- `src/bioetl/application/services/workflow_transform_service.py`
- `src/bioetl/application/workflow/transforms/reconcile_foreign_keys.py`
- `src/bioetl/infrastructure/storage/workflow_foreign_key_reconciliation.py`

### Refactor Direction

1. Ввести единый workflow runtime signal `effective_dry_run` для pipeline и
   transform steps.
2. Для destructive transforms выбрать **fail-closed default**:
   - либо block with explicit operator-facing error;
   - либо preview-mode without `clear`/write side effects.
3. Зафиксировать policy в CLI help, workflow guide и recovery runbook.

### Acceptance Criteria

- `bioetl workflow run chembl_baseline --dry-run` never calls destructive
  storage mutation paths.
- `reconcile_foreign_keys` under dry-run returns explicit no-op/preview payload
  or explicit blocked status, but not silent success with mutation.
- CLI/operator output states clearly that destructive steps were blocked or
  previewed.

### Required Tests

- `tests/unit/application/workflow/test_reconcile_foreign_keys.py`
- `tests/unit/application/services/test_workflow_transform_service.py`
- `tests/unit/interfaces/cli/test_workflow_cli.py`
- `tests/unit/interfaces/cli/commands/test_workflow_command.py`
- `tests/integration/workflow/test_workflow_foreign_key_reconciliation.py`

## Stream 2: Dedicated ChemblBaseline CI Smoke

**Priority:** `P0`

### Goal

Вынести `chembl_baseline` в отдельный repo-backed CI lane, не смешивая его с
общими workflow/control-plane/test matrices.

### Primary Surfaces

- new `.github/workflows/chembl-baseline-smoke.yml`
- `.github/actions/setup-python-uv/action.yml`
- `tests/unit/infrastructure/config/test_workflow_config_api.py`
- `tests/unit/application/services/test_workflow_runner_service.py`
- `tests/integration/workflow/test_workflow_foreign_key_reconciliation.py`

### Refactor Direction

1. Добавить workflow, который триггерится только на baseline-related paths.
2. Разделить smoke на три группы:
   - config load/schema;
   - runner semantics;
   - reconciliation integration.
3. Публиковать JUnit artifacts и step summary.
4. Использовать `permissions: contents: read` и фиксированный
   `runs-on: ubuntu-24.04`.

### Acceptance Criteria

- PR touching baseline surfaces gets a dedicated `ChemblBaseline Smoke` status.
- Smoke lane uploads JUnit XML even on failure.
- Smoke lane does not attempt live ChEMBL ingestion or cross-host execution.

## Stream 3: Declared DAG Cleanup

**Priority:** `P1`

### Goal

Сделать `configs/workflows/chembl_baseline.yaml` выражением реальных data
dependencies, а не исторического serial order.

### Primary Surfaces

- `configs/workflows/chembl_baseline.yaml`
- `src/bioetl/infrastructure/config/workflow_config_api.py`
- `tests/unit/application/services/test_workflow_runner_service.py`
- `tests/unit/infrastructure/config/test_workflow_config_api.py`

### Refactor Direction

1. Убрать лишнюю зависимость
   `reconcile_assay_target_orphans -> run_chembl_publication`.
2. Явно задать:
   - `reconcile_assay_target_orphans` depends on `run_chembl_assay`,
     `run_chembl_target`;
   - `reconcile_assay_publication_orphans` depends on
     `reconcile_assay_target_orphans`, `run_chembl_publication`.
3. Поднять workflow version до нового patch/minor only when accompanying tests
   and docs are updated.

### Acceptance Criteria

- Config topology remains valid and deterministic.
- Existing sequential runner still executes successfully after dependency
  simplification.
- Tests assert dependency-minimal declared order for baseline workflow.

### Open Question

До merge нужно подтвердить, что между `chembl_target` и
`chembl_publication` нет скрытой semantic dependency вне явных transform
inputs.

## Stream 4: Recovery and CLI Smoke Hardening

**Priority:** `P1`

### Goal

Закрыть операторский path вокруг `status`, `resume-last`, `repair-steps`,
`force-steps` и dry-run/destructive ambiguity в baseline-specific tests.

### Primary Surfaces

- `src/bioetl/application/services/control_plane/workflow/execution_service.py`
- `src/bioetl/interfaces/cli/commands/workflow.py`
- `docs/05-operations/runbooks/workflow-control-plane.md`
- `tests/unit/application/services/control_plane/test_workflow_execution_service.py`
- `tests/unit/interfaces/cli/test_workflow_cli.py`
- `tests/integration/workflow/test_workflow_runner_service.py`

### Acceptance Criteria

- Persisted `repair_required`, `ambiguous_step_ids`, and
  `execution_fingerprint` remain stable through destructive recovery paths.
- CLI smoke covers `status`, `--resume-last`, and dry-run behavior for
  destructive steps.
- Runbook examples match shipped CLI semantics.

## Stream 5: GitHub Actions Security Hardening

**Priority:** `P1`

### Goal

Привести all external GitHub Actions refs и permission scopes к explicit
runtime policy.

### Primary Surfaces

- `.github/actions/setup-python-uv/action.yml`
- `.github/workflows/contract-tests.yml`
- `.github/workflows/tests.yml`
- `scripts/engineering/repo/check_github_actions_runtime_policy.py`
- `docs/05-operations/verification/ci-failure-triage-2026-05-05.md`

### Refactor Direction

1. Replace tag-based external refs with pinned SHAs:
   - `astral-sh/setup-uv@v7`
   - `actions/github-script@v7`
   - any other unpinned external `uses:` found during sweep.
2. Expand runtime policy checker from partial allowlist to full external
   `uses:` inventory across `.github/workflows/*.yml` and composite actions.
3. Add explicit `permissions` blocks:
   - top-level `contents: read` by default;
   - narrow write scopes only on jobs that need them, e.g. issue creation.

### Acceptance Criteria

- Runtime policy checker fails on any non-pinned external action.
- `contract-tests.yml` uses least-privilege token permissions.
- CI hardening docs and checker allowlist stay in sync.

## Stream 6: Cache and Runner Image Refinement

**Priority:** `P2`

### Goal

Уменьшить cache drift и image drift для baseline-related lanes.

### Primary Surfaces

- `.github/actions/setup-python-uv/action.yml`
- new `.github/workflows/chembl-baseline-smoke.yml`
- `.github/workflows/tests.yml`

### Refactor Direction

1. Broaden cache key inputs beyond `uv.lock`:
   - `pyproject.toml`
   - `.github/actions/setup-python-uv/action.yml`
   - `uv-extras` input
2. Pin baseline smoke to `ubuntu-24.04`.
3. Add narrow Python `3.13` smoke only for baseline lane, not full matrix.

### Acceptance Criteria

- Baseline smoke cache invalidates on dependency/extras/action changes.
- Baseline smoke no longer depends on mutable `ubuntu-latest`.
- Python `3.13` baseline smoke catches workflow regressions before release-only
  surfaces.

## Stream 7: Optional Bounded Parallel Runner

**Priority:** `P3`

### Goal

Разрешить parallel execution только для независимых non-destructive steps после
завершения P0/P1 hardening.

### Primary Surfaces

- `src/bioetl/application/services/workflow_runner_service.py`
- `src/bioetl/domain/workflow/config.py`
- `tests/unit/application/services/test_workflow_runner_service.py`
- `tests/integration/workflow/test_workflow_runner_service.py`

### Refactor Direction

1. Keep sequential mode as default.
2. Add opt-in layer-based execution for topological batches.
3. Forbid parallel execution of destructive transforms in first iteration.
4. Bound concurrency via explicit semaphore/config limit.

### Acceptance Criteria

- No behavioral regression in resume/skip/failure semantics.
- Parallel mode is opt-in and guarded by tests.
- Baseline workflow benefits only after dependency cleanup proves independence.

## Stream 8: Distributed Lock Seam Preparation

**Priority:** `P3`

### Goal

Подготовить clean seam для future non-local execution, не нарушая текущий
`ADR-010` local-only runtime.

### Primary Surfaces

- `src/bioetl/infrastructure/locking/memory_lock.py`
- `src/bioetl/composition/_workflow_services.py`
- `src/bioetl/domain/locking.py`
- `docs/03-guides/workflows.md`
- `docs/05-operations/runbooks/workflow-control-plane.md`

### Refactor Direction

1. Treat distributed coordination as separate roadmap item.
2. Introduce only the abstraction seam if needed:
   - explicit lock factory injection;
   - clearer local-only runtime docs;
   - no silent fallback from remote to in-memory.
3. Do not enable remote executor until storage consistency model is reviewed.

### Acceptance Criteria

- Current runtime keeps `MemoryLock` semantics unchanged.
- Any future distributed lock backend is introduced behind an explicit seam and
  separate ADR/change program.

## Delivery Sequence

### Phase A: Safety First

1. Stream 1: dry-run safety contract
2. Stream 2: baseline CI smoke lane

### Phase B: Semantics and Operator Hardening

3. Stream 3: declared DAG cleanup
4. Stream 4: recovery and CLI smoke hardening
5. Stream 5: GitHub Actions security hardening

### Phase C: Determinism and Compatibility

6. Stream 6: cache and runner-image refinement

### Phase D: Optional Evolution

7. Stream 7: bounded parallel runner
8. Stream 8: distributed lock seam preparation

## Suggested Timeline

- `2026-06-02` to `2026-06-04`: Streams `P0`
- `2026-06-04` to `2026-06-08`: Streams `P1`
- `2026-06-08` to `2026-06-10`: Streams `P2`
- after `2026-06-10`: `P3` only if roadmap still needs them

## Definition of Done

The refactor plan can be considered complete when:

1. destructive workflow dry-run semantics are fail-closed and tested;
2. `chembl_baseline` has a dedicated CI smoke lane with artifacts;
3. declared workflow dependencies match visible data inputs;
4. baseline recovery and CLI operator paths are baseline-specific tested;
5. external GitHub Actions refs are pinned and enforced by policy;
6. future parallel/distributed work is explicitly separated from current
   hardening scope.

## Recommended First PR Split

To keep reviewable deltas small, use this PR order:

1. `PR-1`: dry-run safety contract + tests
2. `PR-2`: `chembl-baseline-smoke.yml` + cache-key refinement
3. `PR-3`: baseline DAG cleanup + runner/config tests
4. `PR-4`: actions pinning + permissions + checker expansion
5. `PR-5`: recovery/CLI smoke hardening
6. `PR-6+`: optional parallel/distributed follow-ups
