# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-26

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `8472592a3cc0a3348b183aec8a265626c5d74727`

Evidence surface SHA-256: `baf0e5187eaff73c7cfaef2329f9667e59a2f1f343a924c08d35c6f85986e26e`

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "8472592a3cc0a3348b183aec8a265626c5d74727",
  "evidence_surface_sha256": "baf0e5187eaff73c7cfaef2329f9667e59a2f1f343a924c08d35c6f85986e26e",
  "metrics": {
    "architecture_integral_score": 9.41,
    "architecture_interpretation": "good_targeted_improvements",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 45,
    "debt_gate_fail_count": 0,
    "debt_gate_pass_count": 45,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 1582,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 2,
    "partially_covered_module_count": 883,
    "source_module_count": 2467,
    "sunset_compat_count": 0,
    "transition_compat_count": 0,
    "twin_pair_count": 0,
    "uncovered_module_count": 0,
    "unmeasured_module_count": 0
  },
  "schema_version": "technical-debt-audit-summary-v1"
}
-->

Refresh reason: Re-pin to origin/main 8472592a3cc0 after measuring 84 previously unmeasured modules (#9678) and restoring 45/45 debt-governance gates. No budget growth.

## Executive summary

1. Debt-governance gates: **45 pass / 0 fail** (45/45 debt-governance gates).
1. Release status: **debt-governance gates passing**.
1. Architecture quality integral score: **9.41** (`good_targeted_improvements`). Integral score `9.41`.
1. Module inventory (from module-coverage-inventory.json only):
   - source_module_count: **2467**
   - fully_covered: **1582**
   - partially_covered: **883**
   - no_executable_lines: **2**
   - uncovered: **0**
   - unmeasured: **0**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2467 == source_module_count
1. Contract coverage matrix schema: **contract-coverage-matrix-v3** (v3: strict Gold required for availability).
1. Constructor waivers (shrink-only inventory): **1** entries.
1. Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**.
1. Layer violations: **0**.

## Retained facade importer census

| Facade | Source importers | Test importers |
| --- | ---: | ---: |
| `bioetl.domain.composite.config` | 0 | 40 |
| `bioetl.application.composite.merger` | 0 | 5 |

## Evidence anchors

- reports/quality/module-coverage-inventory.json
- reports/quality/architecture-quality-scorecard.json
- reports/quality/debt-governance-gates.json
- reports/quality/contract-coverage-matrix.json
- configs/quality/debt_scorecard.yaml
- configs/quality/constructor_waivers.yaml

## Validation

```text
python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
python -m scripts.engineering.qa validate-technical-debt-audit --json
python -m scripts.engineering.qa check-exemptions
```

## Guard

- **REJECTED_POLICY:** any increase of tech-debt budgets / exemptions / hotspot caps
