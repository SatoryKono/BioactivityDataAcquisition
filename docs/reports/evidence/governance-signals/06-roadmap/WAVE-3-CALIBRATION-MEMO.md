# Wave 3 Calibration Memo: named hotspot programs

## Purpose

This memo calibrates whether BioETL should expand named hotspot programs beyond the existing `application/core` scope.

The goal is intentionally narrow:

- keep targeted governance understandable,
- avoid turning generic file-size noise into program sprawl,
- rank candidate seams in `application` and `composition` using the evidence now available after Wave 2.

## Inputs

- [`SYN-governance-signals.md`](../03-synthesis/SYN-governance-signals.md)
- [`DECISIONS.yaml`](../04-decisions/DECISIONS.yaml)
- [`EXECUTION-ROADMAP.md`](EXECUTION-ROADMAP.md)
- `reports/quality/duplication-baseline.md`
- `RF-FS-002-baseline-2026-03-19.md` (historical archive path no longer published; see `docs/99-archive/README.md`)
- `RF-FS-001-baseline-2026-03-19.md` (historical archive path no longer published; see `docs/99-archive/README.md`)

## Calibration Rules

Candidates were ranked against four questions:

1. Is the pressure concentrated in a seam that developers can name and navigate?
1. Do we see more than one signal at once: large-file tail, duplication, or known structural pain?
1. Would a named program create a focused burn-down path rather than a vague repo-wide obligation?
1. Is the signal clean enough that a hotspot budget would guide behavior instead of amplifying noise?

## Current Program To Preserve

### `application/core`

**Status:** keep as the current named hotspot program.

This remains the cleanest existing program boundary:

- it is already budgeted in `configs/quality/debt_scorecard.yaml`,
- it still appears in the raw large-file tail,
- it was already called out in prior structural planning as a cognitively wide package that mixes lifecycle, batch execution, callbacks, tracing-adjacent helpers, and shared execution contracts.

This is still the best reference model for what a named hotspot program should look like in this repo: bounded, legible, and already tied to recognizable maintenance pressure rather than generic size counts.

## Candidate Ranking

### Rank 1: `application/composite`

**Recommendation:** add as the next named hotspot program in a future follow-up wave.

**Why it ranks first**

- It is already called out in `RF-FS-002-baseline-2026-03-19.md` (historical archive path no longer published; see `docs/99-archive/README.md`) as one of the four hotspot packages and is described there as mixing planning, dependency/join logic, validation, preflight, and runner behavior.
- The raw file tail is concentrated enough to look like one seam rather than scattered provider noise. Current larger files include:
  - `runner_pkg/runner_support_mixin.py`
  - `dependency_joiner.py`
  - `checkpoint/service.py`
- Wave 2 duplication output already shows composite-specific duplication examples around `runner_pkg` stage-support code, which suggests real internal overlap rather than only package-barrel noise.

**Why it is governable**

- The seam is conceptually coherent: composite runtime orchestration.
- The likely remediation path is understandable: runner support, checkpointing, join/dependency logic, and composite lifecycle helpers.
- A named program here would still be narrow enough to support targeted refactor waves without pretending the entire `application/` tree is one hotspot.

**Main caution**

- The package is broad enough that the budget should be path-based and narrow.
- Prefer `src/bioetl/application/composite/` as the program scope, not all of `application`.

### Rank 2: `composition/factories`

**Recommendation:** keep as a calibrated candidate, but do not promote to a named hotspot program yet.

**Why it is a real candidate**

- The raw large-file tail is visibly concentrated in factory-heavy seams:
  - `factories/pipeline/configs.py`
  - `factories/transformer_factory.py`
  - `factories/storage/_helpers.py`
  - `factories/services/pipeline_builder.py`
  - `factories/pipeline/runner_assembly.py`
- Prior planning in `RF-FS-001-baseline-2026-03-19.md` (historical archive path no longer published; see `docs/99-archive/README.md`) already identifies `pipeline_builder.py` as a composition hotspot that should be decomposed by actual seams, not just by line count.

**Why it does not rank first**

- The current duplication baseline for `composition` is still visibly noisy around:
  - `__init__` facades,
  - export barrels,
  - service/factory wrappers,
  - compatibility-style assembly helpers.
- That means the seam is real, but the governance signal is not clean enough yet to justify a named budget without a normalization pass.

**Practical read**

- This is a good next report-only pressure seam.
- It is not yet a good named-budget seam.

### Rank 3: `application/pipelines/*`

**Recommendation:** do not create a named hotspot program here.

**Why not**

- The large-file tail is real, but it is distributed across provider-specific modules:
  - `pubmed/extractors/date.py`
  - `pubmed/blocks.py`
  - `openalex/transformer.py`
  - `semanticscholar/transformer.py`
  - `uniprot/extractors/_comment_facets.py`
- The duplication baseline also points to provider and transformer overlap, but that overlap is not one cohesive seam. It is a mix of extractor patterns, transformer business logic, and provider-specific inheritance/mixin reuse.

**Consequence**

- This area is better served by provider-focused refactor waves or pipeline-family cleanups.
- A named hotspot program here would likely be too broad or too arbitrary to be useful.

### Rank 4: `composition/providers`

**Recommendation:** do not promote at this stage.

**Why not**

- There is still some structural pressure here, but it currently looks more like a local refactor queue than a hotspot-program candidate.
- Recent work already reduced pressure in provider registration modules such as `registration_biblio.py`, which weakens the case for elevating this entire seam into a standing named budget.

## Recommended Outcome

### Decision

If Wave 3 expands named hotspot programs at all, it should add exactly one new program:

- `application_composite`

and defer any `composition` expansion until after one more normalization/calibration pass.

### Why this is the lowest-risk expansion

- It aligns with both the evidence pack and existing RF planning.
- It adds one coherent seam rather than several weakly justified ones.
- It keeps governance understandable: `application/core` plus `application/composite` is still a targeted program set, not metric sprawl.
- It avoids converting noisy `composition` duplication into a budget before the team has separated real assembly debt from facade noise.

## Not Recommended In This Wave

- Do not create repo-wide hotspot budgets.
- Do not create one giant `application` hotspot program.
- Do not create a `composition` named program yet without a duplication-normalization pass.
- Do not use raw `>10 KB` or `>350 LOC` counts alone as program-creation criteria.

## Proposed Follow-Up Change

If the user wants to operationalize Wave 3, the next change should be a small governance PR that:

1. adds a second named hotspot program in `configs/quality/debt_scorecard.yaml` for `src/bioetl/application/composite/`,
1. keeps budgets intentionally narrow and symmetric with the existing `core_orchestration` style,
1. does not add any new blocking duplication gate,
1. leaves `composition/factories` in report-only observation mode.

## Verification Gates For That Follow-Up

- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_regression_metrics.py`
- scorecard validation tests that cover hotspot budgets and debt-scorecard schema
- any touched governance/docs sync tests

## Bottom Line

Wave 3 should expand carefully, not broadly.

The evidence supports:

- **keep** `application/core`,
- **add next** `application/composite`,
- **observe but do not budget yet** `composition/factories`,
- **leave provider-distributed pipeline modules to separate refactor programs rather than hotspot governance.**
