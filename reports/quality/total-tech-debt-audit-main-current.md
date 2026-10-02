# Total Technical Debt Audit: GitHub main

Lifecycle status: current

Audit date: 2026-08-28

Audited repository: SatoryKono/BioactivityDataAcquisition

Audited branch: main

Audited commit SHA: `09ab9ac286bacb7eee3324e950603539a5c62ee6`

Evidence surface SHA-256: `5d18c5eebdb753f5d697d6d95371b1f31915e2498d131cf8aebc0e525e8a22ec`

Registry: configs/quality/technical_debt_audit_registry.yaml

<!-- technical-debt-audit-summary-v1
{
  "audit_id": "total-tech-debt-main-2026-08-20-r1",
  "audited_commit_sha": "09ab9ac286bacb7eee3324e950603539a5c62ee6",
  "evidence_surface_sha256": "5d18c5eebdb753f5d697d6d95371b1f31915e2498d131cf8aebc0e525e8a22ec",
  "metrics": {
    "architecture_integral_score": 9.47,
    "architecture_interpretation": "good_targeted_improvements",
    "constructor_waiver_count": 1,
    "contract_coverage_schema": "contract-coverage-matrix-v3",
    "debt_gate_count": 46,
    "debt_gate_fail_count": 0,
    "debt_gate_pass_count": 46,
    "debt_gate_warn_count": 0,
    "expired_compat_count": 0,
    "fully_covered_module_count": 2490,
    "layer_violation_count": 0,
    "no_executable_lines_module_count": 4,
    "partially_covered_module_count": 27,
    "source_module_count": 2521,
    "sunset_compat_count": 0,
    "transition_compat_count": 0,
    "twin_pair_count": 0,
    "uncovered_module_count": 0,
    "unmeasured_module_count": 0
  },
  "schema_version": "technical-debt-audit-summary-v1"
}
-->

Refresh reason: Reconcile generated metadata while preserving the historical audited commit. Current gate results are recorded in the semantic summary; this is not full coverage acceptance. No budget growth.

## Current metadata refresh — 2026-10-02 (#11846)

Source commit: `1e50b76c1a06d32f9525d5358547775a8bec7b8b`.
Current generated metadata: 46/46 debt gates pass; architecture proxy score
9.47 (`good_targeted_improvements`). These results do not establish full coverage
acceptance or a release PASS.
The machine-readable semantic summary above is the sole current numerical
rollup; dated refresh notes are historical snapshots. The original audited
commit and audit date remain unchanged. This metadata rebind is not a new
repository-wide architecture audit or a fresh coverage measurement.

The module inventory retains 2521 measured rows, while the live source tree
contains 2541 Python modules: 20 modules have no inventory row. The
`test_module_coverage_inventory_covers_every_source_module` guard fails.
Its source-tree digest is
refreshed without adopting a new coverage XML. Full 17-group coverage producer
acceptance remains unverified under #11745 (still open); zero unmeasured and
uncovered rows do not prove that acceptance. No overall release PASS is claimed.

The live cast census is 353 total / 112 unjustified (previously 370 / 129).
Hotspot runtime-builders LOC is 6764 (previously 6760); files, oversized-file
counts and fan-in are unchanged. Budget and exemption values are unchanged.
Debt outcome: decreased for unjustified casts, flat for bounded hotspot debt.

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

Historical metadata refresh (2026-09-29): workflow-evidence closeout and coverage inventory reconciliation. Historical headline evidence (not current):
Debt-governance gates: **46 pass / 0 fail**;
Architecture quality integral score: **9.89** (`excellent`);
source_module_count: **2522**;
fully_covered: **2490**;
partially_covered: **28**;
no_executable_lines: **4**;
uncovered: **0**;
unmeasured: **0**;
= 2522 == source_module_count;
Contract coverage matrix schema: **contract-coverage-matrix-v3**;
Constructor waivers (shrink-only inventory): **1** entries;
Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**;
Layer violations: **0**.
No budget growth.

Historical metadata refresh (2026-09-28): wave-2 test-governance paydown (duplicate names, assertion bypass, 39 markers, deterministic run IDs, zero-ref triage). Historical headline evidence (not current):
Debt-governance gates: **45 pass / 1 fail**;
Architecture quality integral score: **9.74** (`excellent`);
source_module_count: **2491**;
fully_covered: **2483**;
partially_covered: **7**;
no_executable_lines: **1**;
uncovered: **0**;
unmeasured: **0**;
= 2491 == source_module_count;
Contract coverage matrix schema: **contract-coverage-matrix-v3**;
Constructor waivers (shrink-only inventory): **1** entries;
Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**;
Layer violations: **0**.
Residual fail: hotspot_family_baseline_budget_warnings (3 modules ≥250 LOC pending split).

Historical metadata refresh (2026-09-28): hotspot wave-3 splits (artifact_recording, replay_readiness, batch_metrics facades + cohesive submodules; 143+181+31 focused tests green, ruff clean). Historical headline evidence (not current):
Debt-governance gates: **46 pass / 0 fail**;
Architecture quality integral score: **9.89** (`excellent`);
source_module_count: **2491**;
fully_covered: **2483**;
partially_covered: **7**;
no_executable_lines: **1**;
uncovered: **0**;
unmeasured: **0**;
= 2491 == source_module_count;
Contract coverage matrix schema: **contract-coverage-matrix-v3**;
Constructor waivers (shrink-only inventory): **1** entries;
Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**;
Layer violations: **0**.


Historical metadata refresh (2026-09-30): source and governance rebind for Grafana fixes; historical coverage measurements retained.
Debt-governance gates: **46 pass / 0 fail**;
Architecture quality integral score: **9.36** (`good_targeted_improvements`);
source_module_count: **2521**;
fully_covered: **2490**;
partially_covered: **27**;
no_executable_lines: **4**;
uncovered: **0**;
unmeasured: **0**;
= 2521 == source_module_count;
Contract coverage matrix schema: **contract-coverage-matrix-v3**;
Constructor waivers (shrink-only inventory): **1** entries;
Compatibility transition/sunset/expired: **0/0/0**; twin pairs: **0**;
Layer violations: **0**.

## Historical metadata snapshots (not current)

Historical metadata refresh (2026-09-26): rebind after main suite-green merge. Historical headline evidence (not current):
Debt-governance gates: **43 pass / 3 fail**;
Architecture quality integral score: **9.68** (`excellent`);
source_module_count: **2491**;
fully_covered: **2483**;
= 2491 == source_module_count.
No budget growth. Linked issues: #11228 #11230.


Historical metadata refresh (2026-09-23): the canonical registry digest was
recomputed after S2 transformer split, test-governance unique-name/marker
repair, and module-coverage inventory rebind.
Historical headline evidence (not current):
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

Historical metadata refresh (2026-09-19): the canonical registry digest was
recomputed after hotspot fan-in closeout, assertless-triage reduction,
ADR-matrix rebind, and module-coverage inventory rebind.
Historical headline evidence (not current):
Debt-governance gates: **45 pass / 0 fail**;
Architecture quality integral score: **9.47** (`good_targeted_improvements`);
source_module_count: **2497** with fully_covered: **2486**;
partially_covered: **10**; no_executable_lines: **1**;
uncovered: **0**; unmeasured: **0** (= 2497 == source_module_count).
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Historical metadata refresh (2026-09-16): the canonical registry digest was
recomputed after selected-run merge coverage rebind
(`source_module_count=2484`, fully_covered=1622, integral_score=9.36).
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Historical metadata refresh (2026-09-11): the canonical registry digest was
recomputed after #10304 adopted the SHA-bound coverage-verify inventory for
folded control-plane replay score-card modules (`source_module_count=2469`).
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.

Historical metadata refresh (2026-09-15): the canonical registry digest was
recomputed after #10449/#10450/#10451 moved observability backend I/O into
infrastructure and added the measured coverage-inventory rows
(`source_module_count=2474`). Local archive verification later added one row;
the architecture closeout removed one obsolete Protocol module, retaining 2474.
The historical audited commit above is retained; this metadata refresh does
not constitute a new repository-wide architecture audit.
