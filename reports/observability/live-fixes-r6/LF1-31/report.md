# LF1-31 Replay Readiness saved-run matrix

Issue: #12824. UID: `bioetl-control-plane-v1`.

- Source SHA: `48dc0257ed980decaf0d8bf4c209c7e39309a4c4` (`origin/main`).
- Observation UTC: `2026-11-09T08:37:00Z`.
- Local Ops HTTP: `http://127.0.0.1:8000`.
- Deploy SHA and Grafana frames: `NOT_VERIFIABLE`. `docker` is not installed. No dashboard injection was saved.

## Panels and routes

| Panel | Title | Route |
| --- | --- | --- |
| 9422 | Review Exact Replay Readiness | dashboard reduction of the evidence panels |
| 9423 | Review Exact Replay Checks | dashboard reduction of the evidence panels |
| 9408 | Review Replay Evidence | `/ops/control-plane/identity-evidence?view=anchors` |
| 9418 | Review Selected-Run Trust | `/ops/observability/selected-run-status` |
| 9414 | Review Manifest Validation | `/ops/control-plane/manifest-validation` |
| 9415 | Review Lineage Validation | `/ops/control-plane/lineage-validation` |
| 9416 | Review Retention Compliance | `/ops/control-plane/retention-compliance` |
| 9413 | Review Checkpoint Validation | `/ops/control-plane/checkpoint-validation` |
| 9406 | Compare Checkpoint Anchors | `/ops/control-plane/identity-evidence?view=checkpoint_compare` |

## Live catalog calls

Every route below returned HTTP 200 with `resolved_via=selected_run_id_not_found` and trust `INCOMPLETE` where the validation contract includes trust. None returned a transport error body. `identity-evidence` for these ids returned the same `resolved_via` on contract `control_plane_identity_evidence_v1`.

| Label | Pipeline | Run ID | Routes |
| --- | --- | --- | --- |
| zero | `chembl_assay` / `incremental` | `00000000-0000-0000-0000-000000000000` | manifest, lineage, checkpoint, retention, identity anchors |
| LF1-05 positive 1 | `uniprot_protein` / `backfill` | `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37` | same five routes |
| LF1-11 historical | `chembl_activity` / `backfill` | `8ed593ce-3b75-56e0-a337-192953048582` | same five routes |

`selected-run-status` for the two LF1-05 UUIDs returned HTTP 200, `verdict=UNKNOWN`, `reason=run_not_found`, `replay_readiness_now=INSUFFICIENT`. Mode B (`pipeline=All`) for `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37` returned the same not-found verdict. Mode C is the pipeline-specific row above.

## Retained manifest is not READY

`reports/observability/live-fixes-r6/LF1-11/manifest.json` is on disk and is not in the server catalog (the historical id is `selected_run_id_not_found`). Offline fields:

- `run_id=8ed593ce-3b75-56e0-a337-192953048582`
- `manifest_id=6da492a7-cc24-5adf-88f0-b9c2ad0e8df2`
- `objects={}`
- `launch_context.cached_bronze.bronze_path=null`
- `launch_context.exact_replay_ready=false`
- `launch_context.replay_readiness_verdict=rebuild_only`

A manifest id and the dependency-lock hash inside `code_provenance` do not establish READY. The empty `objects` map and `exact_replay_ready=false` are the opposite conclusion. No second mounted positive UUID was available, and no ETL run was started to create one.

## Decision

No generator change. HTTP 200 `selected_run_id_not_found` stays `UNKNOWN` / `INCOMPLETE`, not `QUERY ERROR` and not `READY`. Positive object checks against a live catalog are `NOT_RUN`.

## Checklist

- Two confirmed positive UUIDs with real object checks: `NOT_RUN`. The negative zero UUID and the unmounted historical UUID are recorded as not-found.
- Applicable route receipts are in this report. Rendered panel frames are `NOT_VERIFIABLE`. Mandatory live FAIL rows were not closed as PASS.
- Evidence is this report, the receipt and checksums. Deploy SHA is `NOT_VERIFIABLE`.
