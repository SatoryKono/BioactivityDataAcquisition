# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-26

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `a066536957a6d77782d6319bfa2516b5a73bff58`


Evidence surface SHA-256: `fdf0f88deeb6cb66a60965d2804f99df2d4860c6518d8c1c82883f5e1a7deabf`


Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "a066536957a6d77782d6319bfa2516b5a73bff58",
  "evidence_surface_sha256": "fdf0f88deeb6cb66a60965d2804f99df2d4860c6518d8c1c82883f5e1a7deabf",
  "metrics": {
    "architecture_integral_score": 7.41,
    "architecture_interpretation": "satisfactory_system_refactoring_required",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 45,
    "debt_gate_fail_count": 1,
    "debt_gate_pass_count": 44,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 1447,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 13,
    "partially_covered_module_count": 923,
    "source_module_count": 2467,
    "sunset_compat_count": 0,
    "transition_compat_count": 0,
    "twin_pair_count": 0,
    "uncovered_module_count": 0,
    "unmeasured_module_count": 84
  },
  "schema_version": "technical-debt-audit-summary-v1"
}
-->



Refresh reason: Re-pin to origin/main `a066536957` after repairing merge-conflicted module-coverage-inventory.json (#9676); hotspot measured LOC aligned without budget growth (#9674); honest residual unmeasured_module_count=84 vs max_count 0 remains (#9678). No debt budget grew.


## Executive summary

1. Debt-governance gates: **44 pass / 1 fail** (`44/45` debt-governance gates).
1. Release status: **debt-governance gates failing** (`module_coverage_unmeasured_modules` 84 vs max_count 0).
1. Architecture quality integral score: **7.41** (`satisfactory_system_refactoring_required`). Integral score `7.41`.
1. Module inventory (from `module-coverage-inventory.json` only):
   - source_module_count: **2467**
   - fully_covered: **1447**
   - partially_covered: **923**
   - no_executable_lines: **13**
   - uncovered: **0**
   - unmeasured: **84**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2467 == source_module_count
1. Contract coverage matrix schema: **contract-coverage-matrix-v3** (v3: strict Gold required for availability).
1. Constructor waivers (shrink-only inventory): **1** entries.
1. Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**.
1. Layer violations: **0**.

## Evidence anchors

- `reports/quality/module-coverage-inventory.json`
- `reports/quality/architecture-quality-scorecard.json`
- `reports/quality/debt-governance-gates.json`
- `reports/quality/contract-coverage-matrix.json`
- `configs/quality/debt_scorecard.yaml`
- `configs/quality/constructor_waivers.yaml`

## Reproducibility

```bash
python -m scripts.engineering.qa report-compatibility-importer-census --snapshot-date 2026-08-01
python -m scripts.engineering.qa report-dead-code-inventory --snapshot-date 2026-08-01
python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml
python scripts/engineering/qa/report_architecture_quality_scorecard.py
python -m scripts.engineering.qa report-contract-coverage-matrix
python -m scripts.engineering.qa report-debt-governance-gates --update
python -m scripts.engineering.qa validate-technical-debt-audit --json
```

## Compatibility retained entrypoints (importer census)

| module | src importers | test importers |
| --- | ---: | ---: |
| `bioetl.domain.composite.config` | 0 | 40 |
| `bioetl.application.composite.merger` | 0 | 5 |

## TD2 residual closeout (2026-07-29)

- Epic #7033 / children #7034–#7041: artifact drift cleared, hotspot re-export trim, shim review, scripts ratchet 17→15, public API interim review.

## Related closeouts

- CodeRabbit epic CR-00 / #6692 (children CR-01..CR-07)
- Residual tech-debt epic TD-R-00 / #6676
