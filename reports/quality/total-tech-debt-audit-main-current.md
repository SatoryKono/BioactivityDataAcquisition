# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-07-29

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `947902209629f5666170cd49fbf776f4bcb5f3d2`

Evidence surface SHA-256: `a118c47f388bdc2ddb9d7c5fc549398749d544f86564db7663c08c0d9a474500`

Registry: configs/quality/technical_debt_audit_registry.yaml

Refresh reason: CR-03 / #6695 regenerate from one consistent evidence snapshot after CodeRabbit audit remediation (CR-01/CR-02). No debt budget growth.

## Executive summary

1. Debt-governance gates: **45 pass / 0 fail** (`45/45` debt-governance gates passing).
1. Architecture quality integral score: **9.41** (`good_targeted_improvements`). Integral score `9.41`.
1. Module inventory (from `module-coverage-inventory.json` only):
   - source_module_count: **2311**
   - fully_covered: **1406**
   - partially_covered: **816**
   - no_executable_lines: **55**
   - uncovered: **0**
   - unmeasured: **0**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2277 == source_module_count
1. Contract coverage matrix schema: **contract-coverage-matrix-v3** (v3: strict Gold required for availability).
1. Constructor waivers (shrink-only inventory): **5** entries.
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
