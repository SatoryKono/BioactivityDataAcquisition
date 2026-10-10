# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-28

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `09ab9ac286bacb7eee3324e950603539a5c62ee6`

Evidence surface SHA-256: `47262cf0b491336caee3ef813fef9bcf4e5f4869c00d30f2033e4e8ca659bd8f`

## Current evidence summary

Evidence metadata refresh: 2026-10-01 (RF-001, #11846).
The single machine-readable summary below is generated from the canonical
coverage inventory, architecture scorecard and debt-governance gates. Its
`evidence_surface_sha256` binds those artifacts; the inventory's
`source_tree_sha256` identifies the source tree, not the date of measurement.

This is a metadata rebind, not a new repository-wide audit. The audited SHA
and audit date above remain historical. Earlier conflicting headline values
are retained in Git history, not presented as current conclusions here.

Current result: debt-governance gates passing. The current architecture score `10.00`
replaces the historical score `9.47`; the audited SHA and date remain historical.

Coverage measurements require the complete local 17-shard producer (#11745).
A hash-only refresh preserves historical measurements and cannot prove full
coverage of new modules. Successful governance gates alone do not establish
full-suite success or release readiness. Producer results and any blocker are
reported separately in the issue closeout evidence.

<!-- current-audit-headlines:start -->

Debt-governance gates: **46 pass / 0 fail**

Architecture quality integral score: **10.0** (`excellent`)

source_module_count: **2566**

fully_covered: **2524**

partially_covered: **41**

no_executable_lines: **1**

uncovered: **0**

unmeasured: **0**

= 2566 == source_module_count

Contract coverage matrix schema: **contract-coverage-matrix-v3**

Constructor waivers (shrink-only inventory): **1** entries

Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**

Layer violations: **0**

<!-- current-audit-headlines:end -->

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "09ab9ac286bacb7eee3324e950603539a5c62ee6",
  "evidence_surface_sha256": "47262cf0b491336caee3ef813fef9bcf4e5f4869c00d30f2033e4e8ca659bd8f",
  "metrics": {
    "architecture_integral_score": 10.0,
    "architecture_interpretation": "excellent",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 46,
    "debt_gate_fail_count": 0,
    "debt_gate_pass_count": 46,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 2524,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 1,
    "partially_covered_module_count": 41,
    "source_module_count": 2566,
    "sunset_compat_count": 0,
    "transition_compat_count": 0,
    "twin_pair_count": 0,
    "uncovered_module_count": 0,
    "unmeasured_module_count": 0
  },
  "schema_version": "technical-debt-audit-summary-v1"
}
-->

## Retained facade importer census

| Facade | Source importers | Test importers |
| --- | ---: | ---: |
| `bioetl.domain.composite.config` | 0 | 43 |
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
