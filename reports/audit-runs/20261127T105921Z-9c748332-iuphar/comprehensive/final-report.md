# Issue #13413: IUPHAR audit slices on a clean base

## Verdict and scope

**G-IUPHAR-01: CLOSED for the audited revision.** The owner defined this gap as P04/P07/P09 IUPHAR snapshot and target-classification coverage being UNBOUND because the previous run used a changing, dirty branch. This targeted rerun binds its evidence to the clean main commit below. This closes the provenance gap, not a product defect, and does not establish biological accuracy or certify a production deployment.

Run ID: `20261127T105921Z-9c748332-iuphar`

Audited commit: `9c748332854748cfcdac3533f3e582c13f49a7e6`

Base: freshly fetched `origin/main`; before starting the audit, `HEAD` equalled `origin/main` and `git status --porcelain=v1 --untracked-files=all` returned no entries. The audit branch was created at the same commit. Source and tests were read and executed before writing this report; status remained empty after the checks. Only evidence explicitly listed below is CURRENT for that commit. Earlier run `20261127T0855Z-b0006414-25d61514` remains historical and UNBOUND; its absent evidence is not reconstructed.

This is a targeted three-slice rerun, not a P00–P20 comprehensive audit. P08/P12 handoffs from a full campaign were not available; relevant configuration, provider and schema controls were inspected directly, and the missing full-campaign handoffs remain unresolved. No P20 independent reconciliation was performed. No claims extend beyond the inspected IUPHAR surfaces.

## Evidence ledger

All source references below are repository paths at the audited commit. Line ranges identify the inspected controls, not generated coverage metrics.

| ID | Evidence | Result / boundary |
| --- | --- | --- |
| EV-BASE-01 | `git fetch origin main`; `git rev-parse HEAD origin/main`; `git status --porcelain=v1 --untracked-files=all` | Both SHAs `9c748332854748cfcdac3533f3e582c13f49a7e6`; status empty before the run. |
| EV-TEST-01 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/unit/iuphar_target_class tests/unit/infrastructure/adapters/iuphar -q -p no:cacheprovider --disable-warnings -o addopts=''` | **1199 passed in 18.82s**, exit 0. Tests include synthetic fixtures; not live-provider or production evidence. |
| EV-P04-01 | `src/bioetl/infrastructure/adapters/iuphar/_manifest.py:16-31,41-66`; `snapshot_payload.py:136-169`; `snapshot_loader.py:158-205` | Path confinement, hashes and duplicate-key rejection; v2 source projection is recomputed and checked. |
| EV-P04-02 | `src/bioetl/infrastructure/adapters/iuphar/acceptance_receipt.py:75-145`; `tests/unit/infrastructure/adapters/iuphar/test_snapshot_builder.py:428-443,529-551` | Acceptance binds snapshot and outputs; tests cover forged completeness, altered projections and legacy receipt rejection. |
| EV-P07-01 | `configs/entities/chembl/target.yaml:1-6,16-21,295-310`; `src/bioetl/domain/config/target_classification.py:41-105` | Checked-in configuration is off; mode, contract and manifest requirements are validated. This is not evidence of deployed configuration. |
| EV-P07-02 | `src/bioetl/infrastructure/schemas/silver_chembl_target_classification.py:14-35`; `src/bioetl/infrastructure/config/target_classification_profile.py:220-267`; `src/bioetl/infrastructure/storage/target_classification_guard.py:24-39,50-62,75-93,107-133` | Versioned target fields, selected schema/contract and physical-table compatibility guards. |
| EV-P07-03 | `src/bioetl/composition/bootstrap/assembly/target_classification_runtime.py:39-72,119-149`; `src/bioetl/application/composite/merger_post_join.py:167-181`; `src/bioetl/application/composite/helpers/merger_post_join_persist.py:39-50`; `src/bioetl/application/composite/helpers/target_classification_stage.py:96-102,124-138` | Runtime profile binding, post-join classification call, persistence call and evidence commit/abandon lifecycle inspected. |
| EV-P09-01 | `src/bioetl/infrastructure/adapters/iuphar/_official_targets_csv.py:47-123`; `src/iuphar_target_class/normalization.py:47-72,97-165,306-341` | Required CSV columns and row shape checked; normalization and invalid-row isolation inspected. Extra upstream columns are permitted, not a proven defect. |
| EV-P09-02 | `src/iuphar_target_class/snapshot.py:151-203,226-230`; `src/bioetl/infrastructure/adapters/iuphar/canonical_target_rows.py:38-81,185-200` | Completeness limits negative matches; canonical rows validate identity and payload shape. |
| EV-MEM-01 | Read-only `memory.tooling.workflow pre-task` with `--skip-refresh-if-missing --skip-session-note` | Exit 1, degraded: retrieval artifacts missing; no refresh. Conclusions use source and tests instead. |

## Stage handoffs and coverage

| Stage | Primary concern and evidence | Result | Uncovered / prerequisite limits |
| --- | --- | --- | --- |
| P04 | Snapshot infrastructure and adapter; EV-P04-01, EV-P04-02, EV-TEST-01 | No actionable defect established in inspected scope. Source-derived projection, receipt binding and tampering controls were checked. | Live acquisition and a specific production snapshot were not verified. |
| P07 | Medallion target contracts; EV-P07-01–03, EV-TEST-01 | No blocking defect established in inspected scope. Version selection, compatibility and evidence lifecycle were checked. | P08 full handoff unavailable; configuration was inspected directly. No live Silver/Gold write, migration or production data assessment. |
| P09 | DQ, normalization and drift; EV-P09-01–02, EV-P04-01, EV-TEST-01 | No blocking defect established in inspected scope. Invalid inputs, completeness and schema admission were checked. | P08/P12 full handoffs unavailable; provider/config controls inspected directly. Additive upstream columns are accepted; live upstream schema and data were not examined. |

Finding status: no new product finding is asserted. The gap verdict is limited to the evidence-binding concern defined by the owner; it does not imply that the above coverage is exhaustive or that every control is proven correct. No root-cause cluster or reconciliation verdict is newly asserted. External provider behavior and biological reference accuracy are **NOT_PROVEN**. Runtime/docs mirror changes and debt-budget changes: none.
