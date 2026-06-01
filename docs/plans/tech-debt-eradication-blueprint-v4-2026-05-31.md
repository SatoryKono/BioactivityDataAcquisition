______________________________________________________________________

Version: 4.1.0
Status: local_mirror
Class: mirror
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-01'

______________________________________________________________________

# BioETL Tech Debt Eradication Blueprint v4

Дата snapshot: `2026-05-31`
Incremental resync: `2026-06-01` after `#4705`, `#4847`, `#4848`, `#4849`, `#4850`, `#4851`, `#4610`, and `#4811` closeout.

**Authoritative status source**: live GitHub issue state plus governed quality artifacts.  
**Source command**: `curl -H "Authorization: Bearer ${GITHUB_TOKEN}" https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/{4610,4811,4847,4848,4849,4850,4851}`  
**Stale-warning policy**: this document is a local planning mirror. If GitHub issue state or governed debt budgets move, this file becomes stale until resynced. Do not use it as sole execution authority.

## Why This Mirror Still Exists

This file remains useful as a compact execution snapshot, but it is no longer
presented as the active authority for debt status. `#4850` closed the gap where
local debt plans could drift from GitHub and quality budgets while still
looking operationally current.

## Resynced Program Facts

1. Python runtime target remains `>=3.12`, with `3.13` supported.
2. Workflow baseline is `35`.
3. ADR registry baseline remains `48`; `ADR-003` and `ADR-008` stay `Superseded`.
4. ChEMBL target contract `v2.0` remains live.
5. Tracked twin families remain `3`.
6. `compatibility_test_file_max` is `53` in `configs/quality/test_governance_audit.yaml`; older local mirror values like `56` are stale.
7. Runtime cardinality governance now includes an explicit CI review summary/artifact path:
   - inventory artifact: `reports/observability/runtime_cardinality_inventory.json`
   - live/degraded review artifact: `reports/observability/runtime_cardinality_review.json`
   - workflow owner surface: `.github/workflows/tests.yml::quality-metrics-gate`
8. Deterministic identity governance now documents semantic replay anchors versus allowed operational correlation artifacts in `configs/quality/determinism_identity_policy.yaml`.
9. Config discrepancy reporting is rebaselined to family-scoped semantics:
   - actionable inconsistent parameters: `0`
   - sanctioned partial variance parameters: `140`
   - canonical report: `docs/config-discrepancies-report.md`
10. Canonical duplication evidence is synchronized across hotspot and specialized reports:
   - `reports/quality/hotspot-duplication-baseline.md` now reports `total_duplicate_clusters=5`
   - `src/bioetl/application/services/control_plane` carries the only live hotspot residual at `5`
   - `control-plane-duplication.*` and `runtime-builders-duplication.*` are derived from the same ruleset and drift-guarded by architecture tests
11. Final live GitHub queue check on 2026-06-01 reports no open `technical-debt` issues and only the umbrella epic `#4811` under `tech-debt`; `#4610` is closed.

## Closed Streams

### Stream A

Closed sub-issues: `#4812`, `#4813`, `#4814`, `#4815`, `#4816`, `#4817`,
`#4818`, `#4819`, `#4820`, `#4821`, `#4825`, `#4826`, `#4827`, `#4828`.

Governed outcome:

- duplicate evidence is reconciled across hotspot and specialized reports;
- `application/core`, `composition/bootstrap/runtime`, `composition/factories/pipeline`, and `composition/runtime_builders` are at duplicate baseline `0`;
- `application/services/control_plane` remains at `5` duplicate clusters in the canonical hotspot baseline and is now tracked as residual refactor pressure under `#4610`;
- twin-family no-growth remains enforced;
- config-contract drift closeout remains recorded on GitHub;
- dead-code triage governance is materialized in `reports/quality/dead-code-inventory.md`.

### Stream B

Closed issues: `#4764` through `#4772`.

Governed outcome:

- contract coverage matrix is materialized and green;
- strict Gold validation and composite waiver policy are explicit;
- Bronze fixture-gap wave is archived;
- compatibility usage graph / no-new-shim enforcement is no longer an active execution stream.

### Stream C, Stream D, and Stream E

Archived unless reopened on GitHub:

- `#4610`
- `#4266`, `#4268`, `#4276`, `#4292`, `#4293`, `#4294`, `#4295`, `#4296`, `#4316`
- `#4747`

## Active Queue After This Resync

The post-closeout target queue for the technical-debt program is empty.

If GitHub still reports additional open `technical-debt` or `tech-debt`
issues, GitHub wins and this mirror must be resynced again.

## Governance Contract For Future Mirrors

Every future local debt-planning mirror must include:

1. generation timestamp;
2. exact source command or source workflow;
3. explicit stale-warning policy;
4. explicit statement that live GitHub issue state overrides the mirror when they conflict;
5. governed debt-budget anchors rather than copied freehand counts.

## Evidence Anchors

- `reports/quality/hotspot-duplication-baseline.md`
- `reports/quality/compatibility-importer-census.md`
- `reports/quality/contract-coverage-matrix.md`
- `reports/quality/dead-code-inventory.md`
- `reports/observability/runtime_cardinality_inventory.json`
- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `configs/quality/test_governance_audit.yaml`
- `configs/quality/observability_metric_governance.yaml`
- `tests/architecture/test_hotspot_duplication_family_ratchets.py`
- `tests/architecture/test_compatibility_importer_census_governance.py`
- `tests/architecture/test_contract_coverage_matrix_drift.py`
- `tests/architecture/test_observability_metric_governance.py`

## Next Actions

1. Finish `#4610` with responsibility-owned control-plane decomposition.
2. Re-verify the live tech-debt queue on GitHub.
3. Close epic `#4811` only after the live queue is exhausted and no-governance-growth guards remain green.
