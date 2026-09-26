# Grafana / Trust / observability — audited RF plan

Status: audited and rebased 2026-08-17. Planning artifact only.
Does **not** authorize `.env` edits, new external services, retention-policy
changes, or debt-budget / threshold increases.

| Field | Original plan | This audit |
| --- | --- | --- |
| Evidence | 7-dashboard QA, `run_id=eb1a6a55-8b6a-5ca2-8195-b25d7574580b` | Same findings still hold for Trust/control-plane. Six-board fill re-audited the same day on `run_id=64927f44-df86-533f-bcaa-1554d5105473`. |
| Baseline SHA | `89a65851d7` (clean worktree) | Ancestor of current HEAD `05c2b416f3`. Worktree is **not** clean. |
| Risk | V4 | V4 unchanged. |
| Active checkout | n/a | `fix/issue-8859-exact-cover-closeout` plus foreign WIP (#8859, OBS-FILL rehydrate). Do not implement this plan on that dirty tree. |

Companion execution plan for the six operator boards:
[`plan.md`](plan.md) / epic [#8927](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8927).
PR in flight: [#8933](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/8933).
This Trust lane: epic [#8935](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8935)
(`#8939 → {#8940, #8938, #8941} → #8936 → #8937`).

## 1. Verdict

The original RF-001…RF-008 plan is still the right **Trust / exact-run
evidence** program. It is **not** the right vehicle for restoring Prometheus
current-metrics. That gap was re-diagnosed on 2026-08-17 as publication
topology (CLI process vs scraped `bioetl health server`) and already has
OBS-FILL issues plus PR #8933.

Do **not** start dashboard JSON rewrites for D1–D6 from this plan. Do **not**
turn `UNKNOWN` / `INCOMPLETE` into green before write-side evidence exists.

Target state is unchanged: three independent truths —

1. data-processing outcome (`processing_status`);
2. exact-run forensic evidence (Ops HTTP / run report / lineage / retention);
3. control-plane trust / replay readiness (`trust_status`).

Terminal `success` must keep meaning “data processing succeeded”. It must not
be read as lineage closed, retention compliant, or replay-ready.

## 2. What changed since `89a6585`

- Six-board fill audit (`reports/observability/remediation/20260817/plan.md`)
  explicitly left Trust / `bioetl-control-plane-v1` out of that pass.
- Closed the same day, **not live-proven**: #8920, #8921, #8922, #8923, #8924.
  Live re-check still had `count(bioetl_pipeline_runs_total)=empty` and
  `bioetl_runtime_trust_gap_status_10m=1`.
- Open OBS-FILL epic #8927 and children #8930, #8928, #8929, #8931, #8932.
- PR #8933 claims to close that wave via health-server rehydrate. Treat as
  **in flight**, not live-proven, until Prometheus probes pass after container
  recreate.
- `current_metrics_rehydrate.py` now exists (was not in the original RF file
  list). Local uncommitted edits to that file belong to OBS-FILL / #8859 WIP.
- All original RF file paths still exist.

## 3. Code audit of original RF items

Checked on this checkout (HEAD `05c2b416f3` plus dirty OBS-FILL files).

| RF | Original outcome | Code fact | Disposition |
| --- | --- | --- | --- |
| RF-001 | `processing_status` ≠ `trust_status`; `INCOMPLETE` fail-closed | `EvidenceStatus` is only `OK` / `WARNING` / `ERROR` / `UNKNOWN`. No `trust_status`, `scope_kind`, `evidence_freshness`, or aggregation helper. `service_payload()` returns per-check rows only. | **Open.** First implementation item. |
| RF-002 | Write-side lineage closure/identity | Read-side still reports raw `node:` / `fragment:` gaps. No `edge_endpoint_missing` / `ledger_fragment_missing` families. No publish-time closure preflight found in the planned persistence path. | **Open.** Depends on RF-001 contract. |
| RF-003 | Immutable contract comparison, not “anchors present ⇒ almost OK” | `_contract_check()` still returns `UNKNOWN` / `manifest_contract_compatibility_not_verified` when anchors exist. | **Open.** |
| RF-004 | Run-scoped retention, no full catalog scan | `retention_compliance()` still calls `lifecycle_planner.plan(...)`. Store still walks `_iter_artifact_refs()` over `base_path`. No `plan_for_manifest`. | **Open.** Explains GRAF-QA-009 `deadline_exceeded`. |
| RF-005 (graph) | HTTP budget / failure rendering | `_forensic_request_budget.py` still emits `deadline_exceeded`. Do not raise the global deadline. | **Open.** After RF-004. |
| RF-005 (old §3 text) / RF-006 (graph) | Fresh telemetry + Prom rules | Superseded by OBS-FILL. Do not invent series or add `run_id` labels. | **Superseded** by #8927 / #8930 / #8928 / #8929 / #8931 / PR #8933. |
| RF-007 | D0–D6 UX | D1–D6 blocked on live Prometheus proof (#8932). D0 Trust still mixes current Prom readiness with exact-run HTTP and has no `trust_status` headline. | **Split.** Trust D0 remains here. |
| RF-008 | Docs / generators / closeout | `promql_max_over_time_counter_policy.yaml` still `reviewed_expression_count: 40` (2026-07-16). Inventory YAML still hardcodes panel counts (Trust=63). | **Open** for Trust + GRAF-QA-005/006. Six-board docs wait for OBS-FILL live proof. |

GRAF-QA mapping after audit:

| Evidence | Still a product gap? | Owner now |
| --- | --- | --- |
| GRAF-QA-001 / 007 Overview/Trust current vs exact-run | Yes for Trust D0. Overview current-metrics owned by OBS-FILL. | GRAF-TRUST-01 + GRAF-TRUST-06; Overview → #8927 |
| GRAF-QA-002 / 003 Provider/DQ empty vs TELEMETRY MISSING | Yes, but publication-first. | #8929, #8931; closed-not-proven #8921 / #8922 |
| GRAF-QA-004 Ledger vs run-report duration | Not re-verified this pass. Keep as Trust D0 / Run Explorer label work, not a Prom fix. | GRAF-TRUST-06 |
| GRAF-QA-008 Lineage ERROR | Yes. Read-side detector is strict; write-side still broken. | GRAF-TRUST-02 |
| GRAF-QA-009 retention `deadline_exceeded` | Yes. Full-catalog `plan()` still on the HTTP path. | GRAF-TRUST-04 / 05 |
| GRAF-QA-010 / 011 contract UNKNOWN, missing replay anchors | Yes. Anchors present still yield `UNKNOWN`. | GRAF-TRUST-03 |
| GRAF-QA-005 / 006 stale panel-count / `max_over_time` policy | Yes. Policy date 2026-07-16, count 40. | GRAF-TRUST-06 |

## 4. Revised dependency graph

```
Lane A — Trust / exact-run evidence (this plan)
RF-001 Trust status model and HTTP contract          GRAF-TRUST-01
├── RF-002 Write-side lineage closure/identity       GRAF-TRUST-02
├── RF-003 Persist manifest contract/replay anchors  GRAF-TRUST-03
└── RF-004 Run-scoped retention evidence             GRAF-TRUST-04
    └── RF-005 HTTP budget + failure rendering       GRAF-TRUST-05
        └── RF-007/008 Trust D0 UX + docs/gates      GRAF-TRUST-06

Lane B — current Prometheus (do not re-plan here)
OBS-FILL-01..05  #8930 #8928 #8929 #8931 #8932
PR #8933 (in flight)
```

One implementation item at a time on Lane A. Do not start GRAF-TRUST-06
dashboard JSON until RF-001…RF-005 have additive HTTP fields and fail-closed
reasons. Do not implement Lane A on the dirty #8859 / OBS-FILL worktree;
use a clean branch from `origin/main` after #8933 lands or in a separate
worktree.

## 5. Remaining file-level plan (Lane A only)

### RF-001 — Trust verdict for an exact run

Outcome: HTTP control-plane responses expose `processing_status`,
`trust_status`, `scope_kind`, `evidence_freshness`. `INCOMPLETE` and `ERROR`
stay fail-closed. Additive JSON only.

| File | Action |
| --- | --- |
| `src/bioetl/application/observability/control_plane_evidence/service.py` | Build one bounded trust summary from checkpoint, manifest, lineage, retention, failure-reason checks. Do not mutate `RunManifest`. Do not map `UNKNOWN` → `OK`. |
| `src/bioetl/application/observability/control_plane_evidence/checks.py` | Add typed precedence `ERROR > INCOMPLETE/UNKNOWN > WARNING > OK`. Extend `EvidenceStatus` only if `INCOMPLETE` is required as a first-class status; otherwise keep `UNKNOWN` for missing evidence and reserve `INCOMPLETE` for the aggregate `trust_status`. |
| `src/bioetl/application/observability/control_plane_evidence/service_support.py` | Put the summary on the existing payload (`resolved_via`, timestamps, reasons). |
| `src/bioetl/interfaces/http/_health_server_control_plane_evidence_routing.py` | Export the summary through the current HTTP contract. No Infrastructure import. |
| `src/bioetl/domain/ports/control_plane/run_manifest.py` | Touch only if raw inspection cannot return comparison/anchor results. |
| `tests/unit/application/services/test_control_plane_evidence_service.py` | Precedence, exact scope, no false OK. |
| `tests/unit/interfaces/http/test_health_server_control_plane_validation_evidence.py` | success+INCOMPLETE, ERROR, unavailable envelopes. |

Rollback: optional fields; Grafana keeps old check rows.

### RF-002 — Write-side lineage closure and identity

Outcome: persisted graph for a manifested run has no unresolved edge/ledger
refs and no conflicting node definitions. Validation stays a detector.

Files unchanged from the original plan:
`_fragment_finalization.py`, `lineage_persistence.py`, `file_lineage_store.py`,
`lineage.py`, `lineage_closure.py`, `lineage_identity.py`, plus the listed
unit/integration tests.

Add stable reason families `edge_endpoint_missing` / `ledger_fragment_missing`
/ node-definition conflict. Do not last-write-wins a conflict. Strict
fail-closed only for existing `STRICT_PERSISTENCE_PROFILES`.

### RF-003 — Manifest contract / replay-anchor evidence

Outcome: `contract_compatibility` is OK only from a stored immutable
comparison result. Missing evidence stays `UNKNOWN` with drilldown.
`resume_contract` / `lock_owner_id` are a value or explicit N/A + reason.

Stop for ADR/RFC if a versioned `RunManifest` schema change is required.

### RF-004 / RF-005 — Bounded retention + HTTP budget

Outcome: `/ops/control-plane/retention-compliance` does not scan the full
artifact catalog. 503/504 remain capacity/deadline; business `UNKNOWN` is not
a 504. Do **not** raise `FORENSIC_ENDPOINT_TIMEOUT_SECONDS`.

`ControlPlaneLifecyclePlanner` gains a read-only `plan_for_manifest(...)` (or
equivalent). CLI full `plan()` stays.

### RF-007 / RF-008 — Trust D0 UX and closeout only

After evidence exists:

- `grafana/dashboards/bioetl-control-plane-v1.json` — headline uses HTTP
  `trust_status`; Prom current-readiness stays scoped and labelled.
- Panel docs + `run-manifest-inspection.md` triage:
  run outcome → Trust readiness → lineage → retention → replay.
- `DASHBOARD_REQUIREMENTS.md` — present-zero ≠ absent telemetry ≠ unavailable
  ≠ exact-run outcome.
- `report_dashboard_panel_audit_matrix.py` — derive count from the seven-UID
  inventory; do not hide growth.
- `promql_max_over_time_counter_policy.yaml` — review the extra expression;
  set count from the reviewed list, do not bump blindly.
- Refresh `module-coverage-inventory.json` only if `src/bioetl/**/*.py` changes.

Out of this item: D1–D6 JSON (OBS-FILL-05 / #8932).

## 6. What not to implement from the original §3

- New Prometheus series names or `run_id` Prom labels.
- Dashboard JSON for Overview / Runtime / Provider / DQ / Incident / Run
  Explorer before #8933 is live-proven.
- Raising forensic HTTP deadline or retention_days.
- Retroactive rewrite of already published run artifacts.
- Implementing on the dirty #8859 branch.

## 7. Validation (Lane A)

Use project help for exact flags. Minimum:

```
python -m pytest tests/unit/application/services/test_control_plane_evidence_service.py tests/unit/interfaces/http/test_forensic_request_budget.py tests/unit/infrastructure/control_plane/test_file_lineage_store.py tests/unit/infrastructure/control_plane/test_file_artifact_lifecycle_store.py -q
python -m pytest tests/integration/application/services/test_control_plane_evidence_manifest_raw.py tests/integration/application/services/test_control_plane_evidence_retention_profiles.py -q
python -m pytest tests/integration/test_grafana_dashboard_metric_semantics.py tests/integration/test_grafana_dashboard_first_screen_contract.py tests/integration/test_grafana_layout_and_metadata.py -q
```

Lane B stays on the OBS-FILL commands in [`plan.md`](plan.md).

## 8. Approval boundaries

Owner review required before: versioned `RunManifest` schema change; making
lineage persistence strict for currently permissive profiles; changing
`retention_days`; adding an external registry; changing the meaning of
terminal success.

Expected debt outcome: improved (explicit missing-evidence states, no budget
increase).
