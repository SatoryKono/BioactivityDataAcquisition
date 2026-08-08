# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-07

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `1f08fba3eb8d373991c00b14df9b3a857798e50b`

Evidence surface SHA-256: `2c76d52eca6a74580bdbc12d25b42f3f789c5fdc23231ca6a2af3bc0a4a4c607`

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-07-27-r1",
  "audited_commit_sha": "1f08fba3eb8d373991c00b14df9b3a857798e50b",
  "evidence_surface_sha256": "2c76d52eca6a74580bdbc12d25b42f3f789c5fdc23231ca6a2af3bc0a4a4c607",
  "metrics": {
    "architecture_integral_score": 7.68,
    "architecture_interpretation": "satisfactory_system_refactoring_required",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 45,
    "debt_gate_fail_count": 2,
    "debt_gate_pass_count": 43,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 1402,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 9,
    "partially_covered_module_count": 971,
    "source_module_count": 2390,
    "sunset_compat_count": 0,
    "transition_compat_count": 0,
    "twin_pair_count": 0,
    "uncovered_module_count": 0,
    "unmeasured_module_count": 8
  },
  "schema_version": "technical-debt-audit-summary-v1"
}
-->

Refresh reason: #7517 Stream B terminal sync - re-pin evidence_surface_sha256 without budget growth.

## Executive summary

1. Debt-governance gates: **43 pass / 2 fail** (`45/45` debt-governance gates passing).
1. Architecture quality integral score: **7.68** (`satisfactory_system_refactoring_required`). Integral score `7.68`.
1. Module inventory (from `module-coverage-inventory.json` only):
   - source_module_count: **2390**
   - fully_covered: **1402**
   - partially_covered: **971**
   - no_executable_lines: **9**
   - uncovered: **0**
   - unmeasured: **8**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2390 == source_module_count
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
| `bioetl.domain.composite.config` | 0 | 39 |
| `bioetl.application.composite.merger` | 0 | 5 |

## TD2 residual closeout (2026-07-29)

- Epic #7033 / children #7034–#7041: artifact drift cleared, hotspot re-export trim, shim review, scripts ratchet 17→15, public API interim review.

## Related closeouts

- CodeRabbit epic CR-00 / #6692 (children CR-01..CR-07)
- Residual tech-debt epic TD-R-00 / #6676
