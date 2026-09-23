# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-28

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `09ab9ac286bacb7eee3324e950603539a5c62ee6`

Evidence surface SHA-256: `0c0c9482983f6a6107a175a6db43f8dbd05163583bae32e67e78459a06866b1e`

Evidence metadata refresh (2026-09-23): the canonical registry digest was
recomputed after S2 transformer split, test-governance unique-name/marker
repair, and module-coverage inventory rebind.
Current headline evidence:
Debt-governance gates: **45 pass / 0 fail**;
Architecture quality integral score: **10.0** (`excellent`);
Integral score `10.00`. architecture score `10.00`.
source_module_count: **2479** with fully_covered: **2471**;
partially_covered: **7**; no_executable_lines: **1**;
uncovered: **0**; unmeasured: **0** (= 2479 == source_module_count).
Contract coverage matrix schema: **contract-coverage-matrix-v3**.
Constructor waivers (shrink-only inventory): **1** entries.
Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**.
Layer violations: **0**.
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Evidence metadata refresh (2026-09-19): the canonical registry digest was
recomputed after hotspot fan-in closeout, assertless-triage reduction,
ADR-matrix rebind, and module-coverage inventory rebind.
Current headline evidence:
Debt-governance gates: **45 pass / 0 fail**;
Architecture quality integral score: **9.47** (`good_targeted_improvements`);
source_module_count: **2497** with fully_covered: **2486**;
partially_covered: **10**; no_executable_lines: **1**;
uncovered: **0**; unmeasured: **0** (= 2497 == source_module_count).
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Evidence metadata refresh (2026-09-16): the canonical registry digest was
recomputed after selected-run merge coverage rebind
(`source_module_count=2484`, fully_covered=1622, integral_score=9.36).
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Evidence metadata refresh (2026-09-11): the canonical registry digest was
recomputed after #10304 adopted the SHA-bound coverage-verify inventory for
folded control-plane replay score-card modules (`source_module_count=2469`).
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Evidence metadata refresh (2026-09-15): the canonical registry digest was
recomputed after #10449/#10450/#10451 moved observability backend I/O into
infrastructure and added the measured coverage-inventory rows
(`source_module_count=2474`). Local archive verification later added one row;
the architecture closeout removed one obsolete Protocol module, retaining 2474.
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "09ab9ac286bacb7eee3324e950603539a5c62ee6",
  "evidence_surface_sha256": "0c0c9482983f6a6107a175a6db43f8dbd05163583bae32e67e78459a06866b1e",
  "metrics": {
    "architecture_integral_score": 10.0,
    "architecture_interpretation": "excellent",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 45,
    "debt_gate_fail_count": 0,
    "debt_gate_pass_count": 45,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 2471,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 1,
    "partially_covered_module_count": 7,
    "source_module_count": 2479,
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
1. Architecture quality integral score: **9.47** (`good_targeted_improvements`). Integral score `9.47`.
1. Module inventory (from module-coverage-inventory.json only):
   - source_module_count: **2493**
   - fully_covered: **2485**
   - partially_covered: **7**
   - no_executable_lines: **1**
   - uncovered: **0**
   - unmeasured: **0**
   - check: fully + partial + no_exec + uncovered + unmeasured = 2493 == source_module_count
1. Contract coverage matrix schema: **contract-coverage-matrix-v3** (v3: strict Gold required for availability).
1. Constructor waivers (shrink-only inventory): **1** entries.
1. Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**.
1. Layer violations: **0**.

## Retained facade importer census

| Facade | Source importers | Test importers |
| --- | ---: | ---: |
| `bioetl.domain.composite.config` | 0 | 44 |
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
