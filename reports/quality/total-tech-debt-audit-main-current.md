# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-07-27

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `f5e68efbe6acd3bc0e7c9077c0bd10fa715f1679`

Evidence surface SHA-256: `c8f67926ba76935f6144f35b23230c2dec40d52a05b5a7aeee266a83865390b9`

Registry: configs/quality/technical_debt_audit_registry.yaml

Refresh reason: TD-03 re-pin after TD-01..TD-10 closeout. No debt budget growth.

## Executive summary

1. Debt-governance: integral score 9.11, fail_count=0, pass_count=45.
1. Module inventory: fully_covered=1406, partially_covered=816, uncovered=0, unmeasured=0.
1. Hotspot composition_runtime_builders duplication_clusters = 0 (TD-06).
1. Constructor waivers 19 to 10 (TD-07).
1. Scripts zero-ref budget green with untriaged 0 (TD-01/TD-02).
1. Compatibility transition/sunset/expired 0/0/0; twin pairs 0 (TD-10).
1. Closeout inventory fold fraction >= 0.25 (TD-05).
1. Partial-coverage top-50 + domain tranche (TD-04).
1. infrastructure.config sunset design (TD-08); public API hygiene (TD-09).

## Reproducibility

python -m scripts.engineering.qa report-debt-governance-gates --update

python -m scripts.engineering.qa validate-technical-debt-audit --json
