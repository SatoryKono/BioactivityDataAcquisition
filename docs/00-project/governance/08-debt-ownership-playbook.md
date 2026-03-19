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
2. `owner` is mapped to the correct subsystem in scorecard governance.
3. `removal_step` references concrete follow-up action (refactor/task/RF).
4. `scripts/qa/check_quality_exemptions.py --mode warn` passes.
5. Active owner count in registry remains >= 3.

## Dashboard

Current ownership metadata is governed by:

- `configs/quality/debt_scorecard.yaml`
- `configs/quality/architecture_metric_exemptions.yaml`

Use the two config registries above as the canonical current state.
Historical report snapshots remain evidence only:

- `docs/reports/debt-ownership-dashboard-2026-03-06.md`
