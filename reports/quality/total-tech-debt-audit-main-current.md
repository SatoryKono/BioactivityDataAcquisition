# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-26

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `8472592a3cc0a3348b183aec8a265626c5d74727`

Evidence surface SHA-256: `2dee28875aaf612d8614350ab08fc8b007a4810da0c4e948d8f7d1985eb0b4db`

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "8472592a3cc0a3348b183aec8a265626c5d74727",
  "evidence_surface_sha256": "2dee28875aaf612d8614350ab08fc8b007a4810da0c4e948d8f7d1985eb0b4db",
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
    "fully_covered_module_count": 1476,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 13,
    "partially_covered_module_count": 978,
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
1. Architecture quality integral score: **9.41** (`good_targeted_improvements`). Integral score 9.41.
1. Module inventory (from module-coverage-inventory.json only):
   - source_module_count: **2467**
   - fully_covered: **1476**
   - partially_covered: **978**
   - no_executable_lines: **13**
   - uncovered: **0**
   - unmeasured: **0**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2467 == source_module_count
1. Contract coverage matrix schema: **contract-coverage-matrix-v3** (v3: strict Gold required for availability).
1. Constructor waivers (shrink-only inventory): **1** entries.
1. Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**.
1. Layer violations: **0**.

## Evidence anchors

- 
eports/quality/module-coverage-inventory.json
- 
eports/quality/architecture-quality-scorecard.json
- 
eports/quality/debt-governance-gates.json
- 
eports/quality/contract-coverage-matrix.json
- configs/quality/debt_scorecard.yaml
- configs/quality/constructor_waivers.yaml

## Validation

`	ext
python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
python -m scripts.engineering.qa validate-technical-debt-audit --json
python -m scripts.engineering.qa check-exemptions
`

## Guard

- **REJECTED_POLICY:** any increase of tech-debt budgets / exemptions / hotspot caps
