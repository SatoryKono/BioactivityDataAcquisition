# LF1-30 Run Explorer saved-run matrix

Issue: #12823. UID: `bioetl-run-explorer-v1`.

- Source SHA: `48dc0257ed980decaf0d8bf4c209c7e39309a4c4` (`origin/main`).
- Observation UTC: `2026-11-09T08:37:00Z`.
- Local Ops HTTP: `http://127.0.0.1:8000`.
- Deploy SHA and Grafana screenshots: `NOT_VERIFIABLE`. `docker` is not installed.

## Data-backed panels

The shipped UID has one data-backed panel. Text panels without targets are not data-backed. Panel ids from other UIDs are not included.

| Panel | Title | Query |
| --- | --- | --- |
| 3010 | Inspect Recent Runs (last 10) | `GET /ops/observability/pipeline-run-reports` |

`noValue`: `UNKNOWN — required launch evidence is unavailable. QUERY ERROR means the backend request failed, not an empty fleet.`

Pinned UUIDs from LF1-05: `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37` (`uniprot_protein`) and `d7cdb35b-e37a-5767-b30e-aa8dfb60d775` (`uniprot_idmapping`).

## B and C

B is `pipeline=All` with the UUID. C is the UUID with its own pipeline. `view=recent` and `limit=10` match panel 3010.

| Mode | Pipeline | Run ID | HTTP | index_state | Row |
| --- | --- | --- | --- | --- | --- |
| B | `All` | `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37` | 200 | `tree_missing` | diagnostic `TREE_MISSING`, `run_id=-`, `count=0` |
| C | `uniprot_protein` | `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37` | 200 | `tree_missing` | diagnostic `TREE_MISSING`, `run_id=-`, `pipeline=uniprot_protein` |
| B | `All` | `d7cdb35b-e37a-5767-b30e-aa8dfb60d775` | not repeated | same tree | the second UUID was read in mode C |
| C | `uniprot_idmapping` | `d7cdb35b-e37a-5767-b30e-aa8dfb60d775` | 200 | `tree_missing` | diagnostic `TREE_MISSING`, `run_id=-`, `pipeline=uniprot_idmapping` |

`selected-run-status` for both exact pairs returned HTTP 200, `verdict=UNKNOWN`, `reason=run_not_found`, `replay_readiness_now=INSUFFICIENT`. `pipeline=All` with the first UUID returned the same not-found verdict. That HTTP 200 is not a query error and not a saved success.

The diagnostic row does not contain a shortened form of the requested UUID. It uses the empty sentinel `-` because `reports/run-reports` has no tree. It is not a saved run row and must not be read as `OK`. No saved report was available to compare values. Screenshots and Grafana frames were not captured.

## Decision

No generator change. The positive catalog required by the matrix is not mounted, and no ETL run was started. The missing tree stays a diagnostic row, not a successful launch.

## Checklist

- Positive B/C coverage of saved panels: `NOT_RUN`. The only data-backed panel was called, and both UUIDs are absent.
- `tree_missing` is not recorded as success. Global evidence was not substituted for a saved run: the row is a diagnostic with `run_id=-`.
- Evidence is this report, the receipt and checksums. Deploy SHA is `NOT_VERIFIABLE`.
