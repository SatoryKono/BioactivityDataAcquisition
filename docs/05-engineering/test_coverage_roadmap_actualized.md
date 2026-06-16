# Test Coverage Roadmap - Current Main Status

Last refreshed from `reports/quality/module-coverage-inventory.json`
(`snapshot_date: 2026-06-16`).

## Executive Status

This roadmap supersedes older composition-focused backlog notes that still
claimed several public APIs were at `0%`. They are no longer accurate on
current `main`.

Current committed inventory shows that the `#5153` epic is **not closable yet**.

| Metric | Current value | Epic target |
|--------|---------------|-------------|
| Production modules | 2134 | all in inventory |
| Global line coverage | **69.71%** (`62512 / 89677`) | `>= 85%` |
| Modules `<85%` | **864** | `0` |
| Uncovered modules (`0%`) | **127** | `0` |
| Aggregates `<95%` | **13 / 18** | `0` |
| Contracts / schemas `<95%` | **13 / 72** | `0` |
| Unmeasured modules | **2** | `0` or explicitly allowlisted |

Known unmeasured modules:

- `src/bioetl/__main__.py`
- `src/bioetl/interfaces/cli/__main__.py`

Child issue status from the epic body:

- `#5136` — closed
- `#5143` — closed

## Composition Surface Status

The biggest drift in earlier roadmap drafts was the composition section.
Current main now looks like this:

| Module | Coverage | Status |
|--------|----------|--------|
| `control_plane_api.py` | `100.00%` (`11 / 11`) | done |
| `execution_api.py` | `100.00%` (`19 / 19`) | done |
| `health_api.py` | `88.89%` (`16 / 18`) | below target |
| `maintenance_api.py` | `100.00%` (`16 / 16`) | done |
| `registry_api.py` | `100.00%` (`6 / 6`) | done |
| `resources_api.py` | `100.00%` (`8 / 8`) | done |
| `_pipeline_execution.py` | `84.52%` (`71 / 84`) | below target |
| `services_api.py` | retired / absent | do not backlog |

Implication:

- old issue drafts for `control_plane_api`, `execution_api`,
  `maintenance_api`, and `resources_api` should be treated as completed and
  not reopened;
- `services_api.py` remains a retired target and must stay out of active
  backlog;
- the only remaining composition items from that cluster are `health_api.py`
  and `_pipeline_execution.py`.

## Domain Aggregate Status

The aggregate cluster is still the clearest epic blocker.

| Module | Coverage | Target |
|--------|----------|--------|
| `_batch_lifecycle.py` | `43.33%` (`13 / 30`) | `>= 95%` |
| `_batch_aggregate.py` | `48.39%` (`15 / 31`) | `>= 95%` |
| `_quarantine_entry_transitions_mixin.py` | `42.55%` (`20 / 47`) | `>= 95%` |
| `_quarantine_aggregate.py` | `37.84%` (`14 / 37`) | `>= 95%` |
| `_batch_mixins.py` | `61.62%` (`61 / 99`) | `>= 95%` |
| `_pipeline_run_read_model_mixin.py` | `72.97%` (`54 / 74`) | `>= 95%` |
| `_pipeline_run_stage_result.py` | `77.50%` (`31 / 40`) | `>= 95%` |
| `_quarantine_entry_properties_mixin.py` | `72.58%` (`45 / 62`) | `>= 95%` |
| `_quarantine_value_objects.py` | `77.78%` (`28 / 36`) | `>= 95%` |
| `_batch_record.py` | `75.00%` (`15 / 20`) | `>= 95%` |
| `_batch_status.py` | `93.75%` (`15 / 16`) | `>= 95%` |
| `pipeline_run_state.py` | `94.12%` (`16 / 17`) | `>= 95%` |
| `_pipeline_run_mixins.py` | `90.16%` (`55 / 61`) | `>= 95%` |

Already at target:

- `batch.py`
- `events.py`
- `pipeline_run.py`
- `quarantine_entry.py`

## Contracts / Schema Status

Earlier roadmap text incorrectly treated the whole Gold/contracts area as done.
Current committed inventory still reports `13 / 72` contract-or-schema modules
below the `95%` tier. That makes the “Gold/schema contracts >=95%” track still
open on current main.

## Priority Order

### Phase 1: Finish residual composition blockers

Scope:

- `src/bioetl/composition/health_api.py`
- `src/bioetl/composition/_pipeline_execution.py`

Goal:

- raise both to `>= 90%`
- keep `services_api.py` retired

### Phase 2: Close aggregate lifecycle and quarantine gaps

Primary targets:

- `_batch_lifecycle.py`
- `_batch_aggregate.py`
- `_quarantine_entry_transitions_mixin.py`
- `_quarantine_aggregate.py`
- `_batch_mixins.py`

Focus:

- batch FSM transitions
- quarantine immutability and transition rules
- deterministic record/hash behavior

### Phase 3: Raise remaining aggregate read-model and value-object coverage

Primary targets:

- `_pipeline_run_read_model_mixin.py`
- `_pipeline_run_stage_result.py`
- `_quarantine_entry_properties_mixin.py`
- `_quarantine_value_objects.py`
- `_batch_record.py`
- `_pipeline_run_mixins.py`
- `_batch_status.py`
- `pipeline_run_state.py`

### Phase 4: Restore contracts/schema tier compliance

Goal:

- reduce contracts/schema `<95%` count from `13` to `0`

### Phase 5: Attack broad repo-wide floor

Global backlog remains the hard blocker to epic closure:

- `864` modules below `85%`
- `127` fully uncovered modules

This phase needs breadth-oriented child issues, not more stale composition-only
tickets.

## Definition Of Done

`#5153` is closable only when all of the following are true:

- global line coverage is `>= 85%`
- modules below tier thresholds are reduced to `0`
- aggregates below `95%` are reduced to `0`
- contracts / schemas below `95%` are reduced to `0`
- unmeasured modules are eliminated or explicitly policy-allowlisted
- `python -m scripts.engineering.qa report-module-coverage --check` passes

## Canonical Sources

- `reports/quality/module-coverage-inventory.json`
- `reports/coverage/coverage.xml`
- `configs/quality/debt_scorecard.yaml`
- `configs/quality/test_matrix.yaml`
