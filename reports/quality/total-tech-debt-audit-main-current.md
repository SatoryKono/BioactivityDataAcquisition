# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-28

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `09ab9ac286bacb7eee3324e950603539a5c62ee6`

Evidence surface SHA-256: `40df0463994378a0678517de766b24d65f8e50fdeb433c9c7d4bdcfd1f1d5fb7`

Evidence metadata refresh (2026-09-09): the canonical registry digest was
recomputed after rebinding `architecture-quality-scorecard.json`
`coverage_xml_sha256` to the live module-coverage inventory (post-#10259 rebase).
The historical audited commit above is retained; this metadata refresh does not
constitute a new repository-wide architecture audit.

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "09ab9ac286bacb7eee3324e950603539a5c62ee6",
  "evidence_surface_sha256": "40df0463994378a0678517de766b24d65f8e50fdeb433c9c7d4bdcfd1f1d5fb7",
  "metrics": {
    "architecture_integral_score": 9.14,
    "architecture_interpretation": "good_targeted_improvements",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 45,
    "debt_gate_fail_count": 0,
    "debt_gate_pass_count": 45,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 1611,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 4,
    "partially_covered_module_count": 854,
    "source_module_count": 2469,
    "sunset_compat_count": 0,
    "transition_compat_count": 0,
    "twin_pair_count": 0,
    "uncovered_module_count": 0,
    "unmeasured_module_count": 0
  },
  "schema_version": "technical-debt-audit-summary-v1"
}
-->

Refresh reason: Reconcile the current evidence surface and semantic summary with the canonical generated artifacts while preserving the accepted audited commit. The generated debt-governance evidence records 45/45 passing gates. No budget growth.

## Executive summary

1. Debt-governance gates: **45 pass / 0 fail** (45 debt-governance gates).
1. Release status: **debt-governance gates passing**; no blocking gaps remain.
1. Architecture quality integral score: **9.14** (`good_targeted_improvements`). Integral score `9.14`.
1. Module inventory (from module-coverage-inventory.json only):
   - source_module_count: **2469**
   - fully_covered: **1611**
   - partially_covered: **854**
   - no_executable_lines: **4**
   - uncovered: **0**
   - unmeasured: **0**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2469 == source_module_count
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
