# Great Expectations Spike Report

## Summary

- Date: 2026-04-01
- Scope: `#2595` "Spike: Great Expectations Integration for Data Quality Checks"
- Recommendation: Do not adopt Great Expectations now. Revisit later only if BioETL develops a clear need for stakeholder-facing validation reports, persistent checkpoint/action workflows, or warehouse-style validation surfaces that are not well served by the current code-centric stack.

## Question

Should Great Expectations (GX) be integrated into the current BioETL quality
stack, and if so, where would it add value beyond the existing `Pandera`,
contract-test, and DQ runtime surfaces?

## Current Repo Baseline

The repository already has multiple active data-quality layers:

1. Runtime DataFrame validation through `PanderaSilverValidator` and
   `PanderaGoldValidator` in
   `src/bioetl/infrastructure/validation/pandera_validator.py`.
1. Threshold- and anomaly-oriented DQ evaluation through
   `src/bioetl/application/services/data_quality_service.py`.
1. Silver schema contract protection through
   `tests/contract/silver_schemas/` and the published
   `docs/03-guides/silver-schema-testing-guide.md`.
1. Gold contract governance through
   `docs/02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md`
   plus contract-test surfaces under `tests/contract/` and `tests/architecture/`.
1. Operational handling for DQ failures through
   `docs/05-operations/runbooks/dq-failure-investigation.md`.

This means the repo already supports:

- in-process schema validation for pandas-backed ETL records;
- contract drift detection for schema evolution;
- DQ thresholding and alert-oriented metrics;
- explicit operational runbooks for DQ failures.

The current gap is not "we have no data-quality framework". The real question is
whether GX adds enough differentiated value to justify a second validation
authoring and execution surface.

## What Great Expectations Adds

Based on current official GX Core docs, a dataframe-based GX workflow introduces
additional concepts beyond the in-code schema itself:

- Data Context
- Data Source
- Data Asset
- Batch Definition
- Expectation Suite
- Validation Definition
- Checkpoint
- Actions / validation-result processing

Official docs also show that even an in-memory dataframe flow is organized
through a Data Source, Data Asset, and Batch Definition before validation runs.
That model is useful when validation results need to be grouped, persisted, and
operated as a first-class workflow, but it is meaningfully heavier than the
current BioETL pattern of "build schema in code, validate records in process,
then enforce contracts in tests and CI".

Important nuance: this is not a rejection based on ecosystem maturity. The
latest official package metadata shows GX as production/stable and compatible
with Python 3.10-3.13, which overlaps with the project's supported interpreter
range. The issue is fit and operating cost, not basic compatibility.

## Comparison Against Current BioETL Needs

| Need                                                               | Current BioETL path                                             | GX value-add                                                                | Assessment      |
| ------------------------------------------------------------------ | --------------------------------------------------------------- | --------------------------------------------------------------------------- | --------------- |
| Runtime dataframe validation in ETL code                           | `PanderaSilverValidator` / `PanderaGoldValidator`               | Overlapping capability with more orchestration concepts                     | Weak fit        |
| Silver schema stability and contract drift                         | Snapshot and contract tests in `tests/contract/silver_schemas/` | Can express expectations, but duplicates existing CI enforcement            | Weak fit        |
| Gold breaking-change governance                                    | ADR-036 + contract tests + future compatibility gate (`#2516`)  | Does not replace versioning policy or contract governance                   | Weak fit        |
| DQ thresholding and anomaly decisions                              | `DataQualityService`                                            | GX is not a natural replacement for metrics thresholds and anomaly handling | Weak fit        |
| Human-readable validation reports for non-dev consumers            | Limited today                                                   | Stronger due to expectation/result/reporting workflow                       | Moderate fit    |
| Scheduled validation workflows with persistent checkpoints/actions | Limited today                                                   | Stronger due to Checkpoints and Actions model                               | Moderate fit    |
| External warehouse / SQL / multi-asset validation surfaces         | Not the current dominant repo surface                           | Potentially useful if this becomes central later                            | Future fit only |

## Lightweight Prototype Decision

No executable prototype was required to reach a recommendation.

Reason:

- The repo already exposes the relevant local comparison point in code.
- A minimal GX dataframe workflow would still require adding and maintaining a
  second conceptual surface around Data Context / Data Source / Data Asset /
  Batch Definition / Expectation Suite / Checkpoint for validations that are
  already naturally expressed through `Pandera` plus contract tests.
- The architectural and maintenance trade-off is visible before package
  installation, so adding the dependency now would create churn without
  materially improving the decision quality.

## Recommendation

### Decision

Do not adopt Great Expectations now.

### Why

1. The current BioETL stack is already code-centric and schema-centric.
   `Pandera` is integrated into runtime validators, test suites, and schema
   documentation. GX would introduce a second validation-authoring surface with
   overlapping responsibility.
1. The strongest GX features are workflow/reporting features, not missing core
   validation features. BioETL's immediate quality work is about tightening
   gates, schema compatibility, and lineage-aware governance, not about
   introducing a new validation platform.
1. The current roadmap issues already point to better near-term leverage:
   `#2511` for focused test/DQ gates and `#2516` for Gold schema compatibility.
   Those items build directly on existing repo surfaces instead of creating a
   parallel framework track.
1. Maintenance burden would increase immediately:
   dependency management, onboarding, config conventions, checkpoint storage,
   expectation ownership, and CI/runtime policy decisions.

## Revisit Triggers

Re-open the question only if one or more of the following becomes true:

1. BioETL needs stakeholder-facing validation artifacts or "data docs" that are
   materially more useful than current test output and runbooks.
1. Validation moves from mostly in-process pandas ETL checks to persistent
   multi-dataset or warehouse-backed validation workflows.
1. The project needs checkpoint/action orchestration as a first-class platform
   concern, rather than as plain CI/test/runtime logic.
1. `Pandera`-based validation becomes difficult to maintain or cannot express a
   required class of checks without substantial custom code.

## Practical Next Steps Instead Of GX Adoption

1. Keep `Pandera` as the primary runtime dataframe validation layer.
1. Use `#2511` to narrow and formalize:
   - unit-test standards around transformer validation,
   - VCR/integration policy,
   - contract drift checks,
   - small, high-signal validation gates.
1. Use `#2516` to implement the Gold schema compatibility CI gate described by
   ADR-036.
1. If reporting or persistent checkpoint needs emerge later, run a second spike
   scoped specifically to:
   - Gold publication checks,
   - external warehouse datasets,
   - or operator-facing validation reporting.

## Follow-up Issue Decision

No new implementation issue should be created from this spike.

The recommendation is no-go for immediate adoption, so the correct outcome is to
continue using and strengthening the current `Pandera` + contract-test + DQ
service stack rather than opening a GE rollout track.

## Sources

External official sources:

- Great Expectations GX Core overview:
  `https://docs.greatexpectations.io/docs/core/introduction/gx_overview`
- Great Expectations dataframe workflow:
  `https://docs.greatexpectations.io/docs/core/connect_to_data/dataframes/`
- PyPI package metadata for `great-expectations`:
  `https://pypi.org/project/great-expectations/`

Local repo evidence:

- `src/bioetl/infrastructure/validation/pandera_validator.py`
- `src/bioetl/application/services/data_quality_service.py`
- `tests/contract/silver_schemas/README.md`
- `docs/03-guides/silver-schema-testing-guide.md`
- `docs/04-reference/components/dq-contract-system.md`
- `docs/05-operations/runbooks/dq-failure-investigation.md`
- `docs/02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md`
