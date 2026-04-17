______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Debt Ownership Playbook

## Purpose

Reduce single-owner risk in architecture debt exemptions and keep ownership aligned with Q2 scorecard decomposition targets.

## Subsystem Ownership Model

- Architecture subsystem owner: `@bioetl-architecture`
- Platform subsystem owner: `@bioetl-platform`
- Data-model subsystem owner: `@bioetl-data-model`

Subsystem mapping source of truth: `configs/quality/debt_scorecard.yaml` (`governance.owner_registry_q2_subsystems`).

## Review Policy For New Exemptions

Every new exemption is accepted only if metadata includes:

- `owner`
- `removal_step`

Mandatory enforcement points:

- Registry policy fields in `configs/quality/architecture_metric_exemptions.yaml`.
- Validator check in `src/bioetl/infrastructure/quality/exemptions_registry.py`.
- Architecture tests in `tests/architecture/test_quality_exemptions_registry.py`.

## PR Checklist

1. New exemption declares explicit `owner` and concrete `removal_step`.
1. `owner` is mapped to the correct subsystem in scorecard governance.
1. `removal_step` references concrete follow-up action (refactor/task/RF).
1. `scripts/engineering/qa/check_quality_exemptions.py --mode warn` passes.
1. Active owner count in registry remains >= 3.

## Dashboard

Current ownership metadata is governed by:

- `configs/quality/debt_scorecard.yaml`
- `configs/quality/architecture_metric_exemptions.yaml`

Use the two config registries above as the canonical current state.
If dashboard snapshots are regenerated, publish them under `docs/reports/` and treat them as evidence-only artifacts rather than source of truth.

## Metric Semantics

Use the following terms consistently in governance reviews:

- **Exemption debt**: counts of entries in `configs/quality/architecture_metric_exemptions.yaml`.
  This is the debt state enforced by the scorecard and quarter targets.
- **Hotspot inventory**: raw structural measurements such as large-file counts
  (for example `>10 KB` or `>350 LOC`) collected from the current working tree.
  This is analysis and prioritization input unless explicitly promoted into a named hotspot budget or another blocking policy.

These two signals are related but not interchangeable:

- A green `file_size_limits` ratchet means the exemption registry is within budget.
- It does **not** automatically mean the repo has no large-file tail.

## Review Workflow For Size Signals

When a review discusses file-size debt:

1. Check exemption debt first in:
   - `configs/quality/debt_scorecard.yaml`
   - `configs/quality/architecture_metric_exemptions.yaml`
1. If structural context is needed, generate or refresh a raw hotspot inventory snapshot using the canonical command in `scripts/README.md`.
1. Treat that raw snapshot as evidence for prioritization, not as a blocking gate by itself.
1. Only convert hotspot inventory into enforceable debt through an explicit scorecard or named-hotspot decision.
