# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audited commit SHA: `af206b51a9133f7a260ee9372ee869afdf7fc7bd`

Evidence surface SHA-256: `78f2d6b4b06ee374834b48817aecb5ded93ff8c82dbf2d2eff944f558294b47f`

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary: {"architecture_quality":{"integral_score":9.41,"interpretation":"good_targeted_improvements"},"audit_id":"total-tech-debt-main-2026-07-30","audited_commit_sha":"af206b51a9133f7a260ee9372ee869afdf7fc7bd","compatibility":{"expired":0,"retained_entrypoints":[{"module":"bioetl.domain.composite.config","src_importers":0,"test_importers":39},{"module":"bioetl.application.composite.merger","src_importers":0,"test_importers":5}],"sunset":0,"transition":0,"twin_pairs":0},"debt_governance":{"fail_count":0,"gate_count":45,"pass_count":45},"evidence_surface_sha256":"78f2d6b4b06ee374834b48817aecb5ded93ff8c82dbf2d2eff944f558294b47f","layer_violations":0,"module_inventory":{"fully_covered":1476,"no_executable_lines":94,"partially_covered":744,"source_module_count":2314,"uncovered":0,"unmeasured":0}} -->

## Executive summary

1. Debt-governance gates: **45 pass / 0 fail** (`45/45` debt-governance gates passing).
1. Architecture quality integral score: **9.41** (`good_targeted_improvements`). Integral score `9.41`.
1. Module inventory:
   - source_module_count: **2314**
   - fully_covered: **1476**
   - partially_covered: **744**
   - no_executable_lines: **94**
   - uncovered: **0**
   - unmeasured: **0**
   - check: status total = 2314 == source_module_count
1. Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**.
1. Layer violations: **0**.

## Evidence anchors

- `configs/quality/compatibility_facade_inventory.yaml`
- `configs/quality/debt_scorecard.yaml`
- `reports/quality/architecture-quality-scorecard.json`
- `reports/quality/compatibility-importer-census.json`
- `reports/quality/dead-code-inventory.json`
- `reports/quality/debt-governance-gates.json`
- `reports/quality/module-coverage-inventory.json`
- `reports/quality/test-governance-current.json`

## Reproducibility

```bash
python -m scripts.engineering.qa validate-technical-debt-audit --json
python -m scripts.engineering.qa validate-technical-debt-audit --update-current
```

## Compatibility retained entrypoints (importer census)

| module | src importers | test importers |
| --- | ---: | ---: |
| `bioetl.domain.composite.config` | 0 | 39 |
| `bioetl.application.composite.merger` | 0 | 5 |
