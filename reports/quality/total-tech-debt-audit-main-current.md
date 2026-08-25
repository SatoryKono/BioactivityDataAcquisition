# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-25

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `cdff5b63e6f31bee5c31ae1d3c19a4fe7045481b`


Evidence surface SHA-256: `b749f19138a43d8563b3448e7ff3adf9c77e6df0942cc6a52fbfeddd19f8fdbc`


Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "cdff5b63e6f31bee5c31ae1d3c19a4fe7045481b",
  "evidence_surface_sha256": "b749f19138a43d8563b3448e7ff3adf9c77e6df0942cc6a52fbfeddd19f8fdbc",
  "metrics": {
    "architecture_integral_score": 9.28,
    "architecture_interpretation": "good_targeted_improvements",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 45,
    "debt_gate_fail_count": 0,
    "debt_gate_pass_count": 45,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 1534,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 3,
    "partially_covered_module_count": 898,
    "source_module_count": 2435,
    "sunset_compat_count": 0,
    "transition_compat_count": 0,
    "twin_pair_count": 0,
    "uncovered_module_count": 0,
    "unmeasured_module_count": 0
  },
  "schema_version": "technical-debt-audit-summary-v1"
}
-->



Refresh reason: Re-pin to origin/main `cdff5b63e6` for #9646/#9647 after Wave B artifact refresh; remote-main baseline updated; no budget growth.


## Executive summary

1. Debt-governance gates: **45 pass / 0 fail** (`45/45` debt-governance gates).
1. Release status: **debt-governance gates passing**.
1. Architecture quality integral score: **9.28** (`good_targeted_improvements`). Integral score `9.28`.
1. Module inventory (from `module-coverage-inventory.json` only):
   - source_module_count: **2435**
   - fully_covered: **1534**
   - partially_covered: **898**
   - no_executable_lines: **3**
   - uncovered: **0**
   - unmeasured: **0**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2435 == source_module_count
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
