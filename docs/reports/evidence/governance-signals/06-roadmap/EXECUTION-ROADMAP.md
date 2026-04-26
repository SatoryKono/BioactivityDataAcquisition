# Governance Roadmap: execution waves

## Status Snapshot

- Wave 1 completed on 2026-03-20.
- Wave 2 completed on 2026-03-20.
- Wave 3 calibration artifact now lives in [`WAVE-3-CALIBRATION-MEMO.md`](./WAVE-3-CALIBRATION-MEMO.md).

## Purpose

This roadmap turns the provisional governance decisions into an execution sequence with minimal ambiguity and low regression risk.

It is intentionally staged:

- first stabilize metric semantics and preserve clean complexity baseline,
- then add non-blocking visibility where governance is currently blind,
- only then expand enforceable hotspot programs.

## Inputs

- [`SYN-governance-signals.md`](../03-synthesis/SYN-governance-signals.md)
- [`DECISIONS.yaml`](../04-decisions/DECISIONS.yaml)
- [`RISKS.yaml`](../05-risks/RISKS.yaml)

## Ordering Logic

1. `DEC-governance-c901-zero-new-debt-baseline` stays active across all waves as the clean regression floor.
1. `DEC-governance-file-size-report-dual-track` should come before any new hotspot expansion, otherwise new budgets will be built on ambiguous semantics.
1. `DEC-governance-duplication-expand-report-only-baseline` should happen before any blocking duplication ratchet, because current `R0801` output is too noisy to promote directly.
1. `DEC-governance-expand-named-hotspot-programs-after-calibration` should be last, because it depends on improved visibility from the previous two waves.

## Wave 1: Preserve Baseline And Clarify Metrics

**Primary decisions**

- `DEC-governance-c901-zero-new-debt-baseline`
- `DEC-governance-file-size-report-dual-track`

**Goal**

- Keep complexity governance clean and make file-size reporting semantically honest.

**Scope**

- Preserve `C901` as zero-new-debt blocking baseline.
- Introduce a documented dual-track size view:
  - enforceable exemption debt
  - raw hotspot inventory
- Make dashboard/report wording explicit so green file-size status is not read as “no large-file debt exists”.

**Deliverables**

- One governance doc or report section that explicitly defines:
  - `exemption debt`
  - `hotspot inventory`
- A reproducible raw hotspot snapshot command or script path referenced in developer workflow.
- Updated governance/report text wherever file-size status is surfaced.

**Out of scope**

- New blocking budgets for raw hotspot counts.
- New hotspot program creation.
- Duplication gate changes.

**Verification gates**

- `./.venv/Scripts/python.exe -m scripts.engineering.qa check-c901`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_regression_metrics.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_documentation_sync.py`

**Exit criteria**

- `C901` remains green.
- File-size reporting clearly distinguishes ratcheted debt from raw inventory.
- No new ambiguity remains in governance docs or summaries.

## Wave 2: Add Duplication Visibility Without Enforcement

**Primary decision**

- `DEC-governance-duplication-expand-report-only-baseline`

**Goal**

- Create a stable, non-blocking baseline for duplication in `composition` and `application`.

**Scope**

- Add report-only duplication scans for:
  - `src/bioetl/composition`
  - `src/bioetl/application`
- Keep existing `infrastructure/adapters` duplication check unchanged.
- Capture duplicate clusters in a machine-readable or summary format suitable for trend comparison.
- Define a first-pass normalization policy for tolerated duplicate classes:
  - facades
  - export barrels
  - compatibility shims

**Deliverables**

- A repeatable command or script wrapper for report-only duplication baseline collection.
- A baseline snapshot artifact for `composition` and `application`.
- A short normalization note for known noisy duplication classes.

**Out of scope**

- Blocking duplication budgets.
- Mandatory fail-on-duplication CI gate for `composition` or `application`.
- Large-scale duplicate removal refactors.

**Verification gates**

- Existing default duplication check remains intact.
- New report-only duplication workflow completes within an acceptable time budget.
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_regression_metrics.py`
- Any touched workflow/docs syntax checks remain green.

**Exit criteria**

- `composition` and `application` duplication are visible in a repeatable baseline artifact.
- The team has a reviewed list of noisy-but-expected duplicate classes.
- No merge-blocking duplication ratchet has been introduced yet.

## Wave 3: Calibrate And Expand Named Hotspot Programs

**Primary decision**

- `DEC-governance-expand-named-hotspot-programs-after-calibration`

**Goal**

- Decide whether additional named hotspot programs should be created beyond `application/core`, using calibrated evidence rather than generic file-size counts.

**Scope**

- Compare current `application/core` hotspot program against candidate seams in:
  - `application`
  - `composition`
- Use multiple signals together:
  - raw hotspot inventory
  - duplication baseline
  - architecture pressure / dependency-map context where relevant
- Select at most 1-2 new named hotspot programs in this wave if the evidence is strong.

**Deliverables**

- A calibration memo ranking candidate seams.
- A decision on whether to keep, extend, or revise named hotspot coverage.
- If approved, scorecard updates for new named hotspot programs with explicit rationale and budgets.

**Out of scope**

- Repo-wide hotspot budgeting.
- Immediate repo-wide blocking gates on raw hotspot counts.
- Broad structural rewrites of all identified large files.

**Verification gates**

- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_regression_metrics.py`
- Any scorecard/exemption synchronization checks affected by the change
- Architecture regression slices if the hotspot-program changes touch governance scripts or policy docs

**Exit criteria**

- New named hotspot programs, if added, are justified by calibrated evidence rather than convenience.
- Governance still remains understandable: targeted budgets, not uncontrolled metric sprawl.
- The repo has a clearer path from raw hotspot visibility to enforceable, focused burn-down work.

## Practical Sequencing Rules

- Do not combine Wave 2 and Wave 3 into one PR. Visibility and enforcement should remain separate.
- Keep `C901` blocking from start to finish; it is the clean baseline that makes the rest interpretable.
- Prefer report generation and policy wording changes before any new fail conditions.
- When a wave changes governance semantics, pair it with documentation updates in the same changeset.

## Suggested Minimal Verification Matrix Per Wave

| Wave   | Must stay green                                                                             |
| ------ | ------------------------------------------------------------------------------------------- |
| Wave 1 | `check-c901`, `test_regression_metrics.py`, `test_documentation_sync.py`                    |
| Wave 2 | existing duplication check, `test_regression_metrics.py`, touched workflow/doc checks       |
| Wave 3 | `test_regression_metrics.py`, scorecard sync checks, relevant architecture/governance tests |

## Recommended Immediate Next Action

Review the Wave 3 calibration memo and decide whether to operationalize one additional named hotspot program for `src/bioetl/application/composite/` while keeping `composition` in report-only observation mode.
