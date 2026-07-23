# Total Technical Debt Audit: GitHub `main`

Lifecycle status: current

Audit date: 2026-07-23

Audited repository: `SatoryKono/BioactivityDataAcquisition`

Audited branch: `main`

Audited commit SHA: `ea463cd0871141e990ad3a32473379ba6665ee18`

Evidence surface SHA-256: `08509e023f3260e8c7fa8470de599d37fd556ab2fc571111b5b92a0e1545b320`

Registry: `configs/quality/technical_debt_audit_registry.yaml`

Refresh reason: re-pin after dead-code inventory review-window alignment
(`last_reviewed` / `next_review_by` = `2026-07-23` / `2026-10-21`) and live
scorecard pin at `9.11`. No debt budget, threshold, exemption, or exclusion
growth.

## Executive summary

1. The reviewed quality gate snapshot is passing: architecture score `9.11`,
   `45/45` debt-governance gates passing, with no failures or warnings and
   zero stale generated quality artifacts.
1. Module coverage inventory contains `2,248` source modules: `1,406` fully
   covered, `816` partially covered, `26` with no executable lines, and
   zero uncovered or unmeasured modules. These are module-inventory facts, not
   a claim of complete line or branch coverage.
1. Compatibility transition debt remains zero. The census contains `12`
   retained public entrypoints, `4` retained public export facades, and zero
   twin pairs; retained public API is not relabelled as removable dead code.
1. Test governance reports `22,854` test functions across `2,053` pytest
   files, with zero duplicate test names, markerless tests, compatibility test
   files, and refined assertless residuals.
1. Dead-code inventory (`snapshot_date: 2026-07-23`) reports
   `repo_wide_untriaged_zero_import_candidate_count: 0`, with one classified
   zero-import candidate retained as a module entrypoint.
1. The largest directly evidenced residual is the `816`-module partial
   coverage tail (down from `824` in the 2026-07-19 audit). Debt budgets and
   exclusions are unchanged by this audit.

## Evidence snapshot

| Area | Current fact | Evidence |
| --- | --- | --- |
| Architecture score | Integral score `9.11` | `reports/quality/architecture-quality-scorecard.json` |
| Debt gates | `45` pass, `0` fail, `0` warn; `stale_artifact_count=0` | `reports/quality/debt-governance-gates.json` |
| Module inventory | `2247` total; `1403` full; `819` partial; `25` no executable lines; `0` uncovered/unmeasured | `reports/quality/module-coverage-inventory.json` |
| Test governance | `22854` functions; `2053` files; duplicate/markerless/compatibility/refined-assertless counts all `0` | `reports/quality/test-governance-current.json` |
| Compatibility | `12` retained entrypoints; `4` public export facades; `0` twin pairs | `reports/quality/compatibility-importer-census.json` |
| Transition compatibility debt | Current/max count `0/0` | `configs/quality/debt_scorecard.yaml` |
| Dead code | `untriaged=0`; `1` classified zero-import candidate (`retain_module_entrypoint`); `18` triaged retained entries | `reports/quality/dead-code-inventory.json` |

## Corrected / preserved compatibility claims

| Surface | Source importers | Test importers | Current disposition |
| --- | ---: | ---: | --- |
| `bioetl.domain.composite.config` | 0 | 39 | Retained public entrypoint; no first-party source importer claim |
| `bioetl.application.composite.merger` | 0 | 5 | Retained public entrypoint; no first-party source importer claim |
| `src/bioetl/infrastructure/compat/pandera_compat.py` | — | — | File absent; prior live-shim claim remains superseded |

Source and test importer evidence stay separated. Zero source-import count alone
is not a removal recommendation.

## Prioritized residual work

| Priority | Evidence-backed residual | Action boundary |
| --- | --- | --- |
| P1 | `816` partially covered modules | Reduce with focused invariant/regression tests; do not reinterpret module inventory as line/branch closure |
| P1 | Retained compatibility entrypoints | Preserve public contracts; removal requires explicit deprecation and external-consumer evidence |
| P1 | Reviewed hotspot/debt gates | Ratchet downward only; no budget, threshold, exemption, or exclusion growth |
| P2 | Dead-code review window | `last_reviewed=2026-07-23`, `next_review_by=2026-10-21`; keep untriaged at zero on every inventory refresh |

Linked child issues under tracker #6486 track structural burn-down and docs
sync after this evidence re-pin.

## Reproducibility and lifecycle

The registry declares exactly one current audit and archives superseded reports.
The evidence hash is computed from the ordered path/content identities listed in
the current registry record:

```bash
python -m scripts.engineering.qa validate-technical-debt-audit --json
```

If any declared evidence file changes, the registry check fails until a new
current audit is published and the previous report is archived under
`docs/99-archive/reports/quality/`.

Canonical refresh sequence used for this snapshot:

```bash
python -m scripts.engineering.qa.report_architecture_quality_scorecard
python -m scripts.engineering.qa report-architecture-debt-remote-main-baseline --update
python -m scripts.engineering.qa report-dead-code-inventory --snapshot-date 2026-07-23
python -m scripts.engineering.qa report-debt-governance-gates --update
python -m scripts.engineering.qa report-dead-code-inventory --check
python -m scripts.engineering.qa validate-technical-debt-audit --json
```
