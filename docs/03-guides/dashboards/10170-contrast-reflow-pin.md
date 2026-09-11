______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-09-11'

______________________________________________________________________

# #10170-A pin: SHA, pack id, UID, window, commands

Parent: #10170. Child: #10357. This pin is **not** live capture and **not**
contrast PASS. Grafana is not started here. `.env` is not modified.

## Candidate

| Field | Value |
| --- | --- |
| `origin/main` SHA | `fe1b7ea01c87ede7edcac20f8bc65b53ea2d1416` |
| Pack id | `10170-fe1b7ea01c87` |
| Pack directory | `reports/audit/grafana/10170-fe1b7ea01c87/` |
| Timezone | `UTC` |
| `--range-from` | `2026-09-10T00:00:00.000Z` |
| `--range-to` | `2026-09-11T00:00:00.000Z` |

C–F must reuse this SHA, window, and variables. If `origin/main` moves, open a
new pin; do not rewrite this file in place.

## Seven UID

- `bioetl-overview-v2`
- `bioetl-runtime`
- `bioetl-dq-v2`
- `bioetl-incident-v1`
- `bioetl-control-plane-v1`
- `bioetl-provider-health-v2`
- `bioetl-run-explorer-v1`

## Grafana variables (matched for all capture children)

| Variable | Value |
| --- | --- |
| `workflow` | `All` |
| `pipeline` | `chembl_target` |
| `run_type` | `incremental` |
| `run_id` | `-` |

These match `scripts/ops/observability/grafana/audit_live_grafana_panels.py`
defaults. They are not secrets.

## Profiles by child

| Child | Profiles |
| --- | --- |
| #10359 C | `1366x768-dark`, `1366x768-light`, `1366x768-dark-full`, `1366x768-light-full` |
| #10360 D | `1366x768-dark-zoom-200`, `1366x768-light-zoom-200` |
| #10361 E | `1440x900-dark`, `1440x900-light`, `1440x900-dark-full`, `1440x900-light-full` |
| #10362 F | `1920x1080-dark`, `1920x1080-light`, `1920x1080-dark-full`, `1920x1080-light-full` |

Native browser zoom only. CSS zoom is not reflow. Kiosk 2560/3840 is out of
#10170 scope. Repeat `1440x900-dark-repeat` is not required for E.

## Commands (no secrets)

Set `GRAFANA_BASE_URL` only after explicit endpoint approval. Default in code is
`http://localhost:3000`. Do not put passwords in git. Prefer
`GRAFANA_SERVICE_ACCOUNT_TOKEN` at runtime. Do not start
`docker-compose.monitoring.yml` unless the operator asked.

Matrix (example for C; swap `--profiles` per table):

```text
.\.venv-win\Scripts\python.exe -m scripts.ops.observability.grafana.run_grafana_render_matrix `
  --output-dir reports/audit/grafana/10170-fe1b7ea01c87 `
  --range-from 2026-09-10T00:00:00.000Z `
  --range-to 2026-09-11T00:00:00.000Z `
  --no-include-kiosk `
  --uids bioetl-overview-v2 bioetl-runtime bioetl-dq-v2 bioetl-incident-v1 bioetl-control-plane-v1 bioetl-provider-health-v2 bioetl-run-explorer-v1 `
  --variable workflow=All `
  --variable pipeline=chembl_target `
  --variable run_type=incremental `
  --variable run_id=- `
  --profiles 1366x768-dark 1366x768-light 1366x768-dark-full 1366x768-light-full
```

Acceptance JSON from manifests (after capture):

```text
.\.venv-win\Scripts\python.exe -m scripts.ops.observability.grafana.capture_acceptance `
  --output-dir reports/audit/grafana/10170-fe1b7ea01c87/acceptance-C `
  --require-native-browser-zoom `
  reports/audit/grafana/10170-fe1b7ea01c87/1366x768-dark/render-manifest.json `
  reports/audit/grafana/10170-fe1b7ea01c87/1366x768-light/render-manifest.json
```

Preflight (after capture; skip if endpoint not approved):

```text
.\.venv-win\Scripts\python.exe -m scripts.ops.observability.grafana.check_grafana_dashboard_audit_preflight `
  --screenshot-dir reports/audit/grafana/10170-fe1b7ea01c87/1366x768-dark `
  --screenshot-uids bioetl-overview-v2 bioetl-runtime bioetl-dq-v2 bioetl-incident-v1 bioetl-control-plane-v1 bioetl-provider-health-v2 bioetl-run-explorer-v1
```

Do not rewrite `10165-postmerge-bundle-*` or `20260907-*`.
