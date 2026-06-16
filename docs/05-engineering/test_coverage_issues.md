# GitHub Issue Drafts For Coverage Program

Last refreshed from `reports/quality/module-coverage-inventory.json`
(`snapshot_date: 2026-06-16`).

## Program Status

Epic `#5153` remains open by substance and is **not ready for closure** on
current `main`.

Current blockers:

- global line coverage is `69.71%`, below the `85%` gate;
- `864` modules remain below `85%`;
- `127` production modules remain at `0%`;
- `13 / 18` aggregate modules remain below `95%`;
- `13 / 72` contracts/schema modules remain below `95%`;
- two modules remain unmeasured in committed inventory:
  `src/bioetl/__main__.py` and `src/bioetl/interfaces/cli/__main__.py`.

Resolved child issues already referenced by the epic:

- `#5136` — closed
- `#5143` — closed

## Resolved / Retired Composition Drafts

These older composition issue ideas should **not** be created again:

- `execution_api.py` is now at `100%`
- `control_plane_api.py` is now at `100%`
- `maintenance_api.py` is now at `100%`
- `resources_api.py` is now at `100%`
- `registry_api.py` is now at `100%`
- `services_api.py` is retired and absent from current `main`

## Draft 1: Raise residual composition coverage to target

**Title:** Raise residual composition coverage for `health_api.py` and `_pipeline_execution.py`

**Priority:** P1

**Labels:** `testing`, `coverage`, `layer:composition`, `technical-debt`

**Context:**

- `src/bioetl/composition/health_api.py` is at `88.89%` (`16 / 18`)
- `src/bioetl/composition/_pipeline_execution.py` is at `84.52%` (`71 / 84`)
- all other live public composition API surfaces in this cluster already meet
  or exceed target

**Acceptance criteria:**

- [ ] `health_api.py` reaches `>= 90%`
- [ ] `_pipeline_execution.py` reaches `>= 90%`
- [ ] no new structural-debt exemptions are added
- [ ] `report-module-coverage --check` remains green after inventory refresh

## Draft 2: Close aggregate FSM and quarantine transition gaps

**Title:** Cover aggregate lifecycle and quarantine transition invariants

**Priority:** P0

**Labels:** `testing`, `coverage`, `layer:domain`, `architecture`, `technical-debt`

**Primary targets:**

- `src/bioetl/domain/aggregates/_batch_lifecycle.py` — `43.33%`
- `src/bioetl/domain/aggregates/_batch_aggregate.py` — `48.39%`
- `src/bioetl/domain/aggregates/_quarantine_entry_transitions_mixin.py` — `42.55%`
- `src/bioetl/domain/aggregates/_quarantine_aggregate.py` — `37.84%`
- `src/bioetl/domain/aggregates/_batch_mixins.py` — `61.62%`

**Acceptance criteria:**

- [ ] explicit tests cover batch FSM transitions
- [ ] explicit tests cover quarantine immutability and transition invalidation
- [ ] each listed module reaches `>= 95%`
- [ ] no technical-debt budgets are raised

## Draft 3: Close aggregate read-model and value-object gaps

**Title:** Raise remaining aggregate read-model and value-object coverage to `95%`

**Priority:** P1

**Labels:** `testing`, `coverage`, `layer:domain`, `technical-debt`

**Primary targets:**

- `src/bioetl/domain/aggregates/_pipeline_run_read_model_mixin.py` — `72.97%`
- `src/bioetl/domain/aggregates/_pipeline_run_stage_result.py` — `77.50%`
- `src/bioetl/domain/aggregates/_quarantine_entry_properties_mixin.py` — `72.58%`
- `src/bioetl/domain/aggregates/_quarantine_value_objects.py` — `77.78%`
- `src/bioetl/domain/aggregates/_batch_record.py` — `75.00%`
- `src/bioetl/domain/aggregates/_pipeline_run_mixins.py` — `90.16%`
- `src/bioetl/domain/aggregates/_batch_status.py` — `93.75%`
- `src/bioetl/domain/aggregates/pipeline_run_state.py` — `94.12%`

**Acceptance criteria:**

- [ ] all listed modules reach `>= 95%`
- [ ] tests assert payload and event semantics, not facade-only imports
- [ ] module inventory refresh shows `aggregates <95% == 0`

## Draft 4: Restore contracts / schema tier compliance

**Title:** Restore `>=95%` coverage across domain contracts and schema surfaces

**Priority:** P1

**Labels:** `testing`, `coverage`, `layer:domain`, `technical-debt`

**Context:**

- current committed inventory still reports `13 / 72` contracts/schema modules
  below `95%`
- older roadmap text that marked this track “complete” is stale on current main

**Acceptance criteria:**

- [ ] contracts/schema `<95%` count drops from `13` to `0`
- [ ] strict contract tests remain deterministic
- [ ] no contract surface is removed from inventory to fake compliance

## Draft 5: Burn down repo-wide zero-coverage and below-floor modules

**Title:** Burn down repo-wide `<85%` and `0%` module backlog after domain/composition fixes

**Priority:** P1

**Labels:** `testing`, `coverage`, `technical-debt`

**Context:**

- `864` modules remain below `85%`
- `127` modules remain fully uncovered
- closing the epic is impossible without broad repo-wide follow-up beyond the
  composition and aggregate clusters

**Acceptance criteria:**

- [ ] broad backlog is decomposed into tractable child issues by family / layer
- [ ] global line coverage moves materially toward `85%`
- [ ] epic `#5153` is only closed after the repo-wide floor is actually met
