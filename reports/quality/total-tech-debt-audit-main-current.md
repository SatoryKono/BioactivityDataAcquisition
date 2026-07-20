# Total Technical Debt Audit: GitHub `main`

Lifecycle status: current

Audit date: 2026-07-19

Audited repository: `SatoryKono/BioactivityDataAcquisition`

Audited branch: `main`

Audited commit SHA: `80c9ae958d22d589f03b2f0a013e5e10fa62665c`

Evidence surface SHA-256: `144c6b67ccd4287cbd8ef86f7694b144965f885984644259db0ff98e4464d7f2`

Registry: `configs/quality/technical_debt_audit_registry.yaml`

Refresh reason: #6355 — replace ambiguous/current evidence with a reproducible
snapshot and correct compatibility claims that drifted from machine-readable
artifacts.

## Executive summary

1. The reviewed quality gate snapshot is passing: architecture score `8.92`,
   `45/45` debt-governance gates passing, with no failures or warnings.
1. Module coverage inventory contains `2,241` source modules: `1,398` fully
   covered, `824` partially covered, `19` with no executable lines, and
   zero uncovered or unmeasured modules. These are module-inventory facts, not
   a claim of complete line or branch coverage.
1. Compatibility transition debt remains zero. The census contains `12`
   retained public entrypoints, `4` retained public export facades, and zero
   twin pairs; retained public API is not relabelled as removable dead code.
1. Test governance reports `22,561` test functions across `2,020` pytest
   files, with zero duplicate test names, markerless tests, compatibility test
   files, and refined assertless residuals.
1. The largest directly evidenced residual is the `824`-module partial
   coverage tail. Debt budgets and exclusions are unchanged by this audit.

## Evidence snapshot

| Area | Current fact | Evidence |
| --- | --- | --- |
| Architecture score | Integral score `8.92` | `reports/quality/architecture-quality-scorecard.json` |
| Debt gates | `45` pass, `0` fail, `0` warn | `reports/quality/debt-governance-gates.json` |
| Module inventory | `2241` total; `1398` full; `824` partial; `19` no executable lines; `0` uncovered/unmeasured | `reports/quality/module-coverage-inventory.json` |
| Test governance | `22561` functions; `2020` files; duplicate/markerless/compatibility counts all `0` | `reports/quality/test-governance-current.json` |
| Compatibility | `12` retained entrypoints; `4` public export facades; `0` twin pairs | `reports/quality/compatibility-importer-census.json` |
| Transition compatibility debt | Current/max count `0/0` | `configs/quality/debt_scorecard.yaml` |

## Corrected compatibility claims

| Surface | Source importers | Test importers | Current disposition |
| --- | ---: | ---: | --- |
| `bioetl.domain.composite.config` | 0 | 39 | Retained public entrypoint; no first-party source importer claim |
| `bioetl.application.composite.merger` | 0 | 5 | Retained public entrypoint; no first-party source importer claim |
| `src/bioetl/infrastructure/compat/pandera_compat.py` | — | — | File absent; the previous audit's live-shim claim is superseded |

The earlier audit incorrectly merged test imports into source-importer
narrative and described a Pandera compatibility file that no longer exists.
This report keeps source and test evidence separate and makes no removal
recommendation solely from a zero source-import count.

## Prioritized residual work

| Priority | Evidence-backed residual | Action boundary |
| --- | --- | --- |
| P0 | `824` partially covered modules | Reduce with focused invariant/regression tests; do not reinterpret module inventory as line/branch closure |
| P1 | Retained compatibility entrypoints | Preserve public contracts; removal requires explicit deprecation and external-consumer evidence |
| P1 | Reviewed hotspot/debt gates | Ratchet downward only; no budget, threshold, exemption, or exclusion growth |

## Reproducibility and lifecycle

The registry declares exactly one current audit and archives superseded reports.
The evidence hash is computed from the ordered path/content identities listed in
the current registry record:

```bash
python -m scripts.engineering.qa.technical_debt_audit_registry --json
```

If any declared evidence file changes, the registry check fails until a new
review produces a new hash and, when appropriate, a new current audit. Archived
reports remain historical evidence and are not edited in place.

## Limitations

- This audit is non-normative and does not replace `RULES.md`, accepted ADRs,
  or machine-readable quality gates.
- A passing gate snapshot does not mean technical debt is absent.
- Counts are valid only for the pinned commit/evidence surface above.
