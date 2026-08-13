______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-04'

______________________________________________________________________

# Debt Ownership Playbook

## Purpose

Reduce single-owner risk in architecture debt exemptions and keep ownership aligned with Q3 scorecard decomposition targets.

## Subsystem Ownership Model

- Architecture subsystem owner: `@bioetl-architecture`
- Platform subsystem owner: `@bioetl-platform`
- Data-model subsystem owner: `@bioetl-data-model`

Subsystem mapping source of truth: `configs/quality/debt_scorecard.yaml` (`governance.owner_registry_q3_subsystems`).

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
1. If active `technical_debt` remains in the registry after the change, active owner count stays >= 2 once Q3 diversification policy is in force.

## Tech-debt PR path scope (#7462)

Tech-debt / quality-baseline remediations **SHOULD** stay quality-artifact
scoped so concurrent MCP/docs agent work cannot smuggle unrelated noise into
debt PRs.

**Allowed paths (default allowlist):**

- `configs/quality/**` scorecard, inventories, registries, waivers
- `reports/quality/**` gates, baselines, closeouts, censuses, residual snapshots
- `tests/architecture/**` debt/closeout/residual guards tied to the change
- `scripts/engineering/qa/**` generators for the artifacts above
- Minimal `.gitignore` allowlists for newly tracked quality evidence

**Disallowed by default (own PR / separate issue):**

- `docs/00-project/ai/**` MCP policy/agent mirrors
- `scripts/ai/mcp/**`, `scripts/ops/runtime/mcp/**`, root `.mcp.json` helpers
- Broad docs matrix regenerations under `docs/reports/generated/**` unless the
  issue is explicitly documentation-governance debt
- Unrelated mass lint rewrites outside the debt finding path list

**Exceptions:** allowed when the PR body cites a concrete dependency (for
example a generator lives under another tree) and reviewers accept the scope.

After scorecard/baseline input changes, refresh debt gates last:

```bash
python -m scripts.engineering.qa.refresh_governance_artifacts
python -m scripts.engineering.qa report-debt-governance-gates --check
```

Canonical gate input set is embedded in
`reports/quality/debt-governance-gates.json` field `input_artifacts` (#7465).

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
1. If structural context is needed, generate or refresh a raw hotspot inventory snapshot using the canonical command in `scripts/engineering/README.md`.
1. Treat that raw snapshot as evidence for prioritization, not as a blocking gate by itself.
1. Only convert hotspot inventory into enforceable debt through an explicit scorecard or named-hotspot decision.

## Shrink-before-grow freezes (#8714)

Scorecard ratchets that sit at `current_count == max_count` are **hard freezes**.
Examples (see live residual + scorecard):

- `config_surface_ratchet.metrics.config_count` (27/27)
- `config_surface_ratchet.metrics.unique_parameter_count` (419/419)
- `application_services_control_plane.max_internal_fan_in` (2/2)
- retirement `repo_wide_zero_import_candidate_count` (5/5)
- sanctioned public entrypoint / facade ceilings

**PR rule:** any change that would increase a ceiling metric **MUST** either:

1. Shrink another residual in the same PR (net flat or down), or
2. Split/refactor so the metric does not grow,

and **MUST NOT** raise `max_count` / `bounded_growth_budgets` / exemptions.

Validation:

```bash
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
```

Bare `--check` without `--changed-from-ref` records
`budget_increase_count=not_evaluated_without_changed_from_ref` and does **not**
evaluate saturated-metric compensation. CI and freeze PRs MUST pass the
reference-aware invocation so scorecard `max_count` / `bounded_growth_budgets`
cannot grow unnoticed.


