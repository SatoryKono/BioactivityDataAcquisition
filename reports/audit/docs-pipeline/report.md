# Docs pipeline audit — `docs-pipeline`

| Field | Value |
| --- | --- |
| domain_id | `docs-pipeline` |
| prompt_id | `prompt.audit.docs-pipeline` |
| MODE | full |
| LANGUAGE | ru |
| Date | 2026-08-21 |
| SHA | `b48ac65c98` |
| surface_score | **3** |
| gate | PASS (pipeline) / cycle WARN from content residual |

## Executive summary

SoT to generator to validation to CI is intact:

- Unified entry: `python -m scripts.docs <command>`
- CI: `.github/workflows/docs.yml` jobs `docs-governance`, `validate-mkdocs`
- Path filters include `.github/workflows/**` (#9266 closed, re-verified)
- `check-links` full PASS including workflow inventory (42 files)
- `check-drift --runtime-mirrors --freshness` PASS
- `check-kpi` monitoring, no breaches
- MkDocs local build skipped: mkdocs not in `.venv-win`; CI uses `uv-extras: docs`

No new PROVEN pipeline defects on this SHA.

## Skipped

- `python -m scripts.docs build-site` (docs extra absent in Windows venv)
- `docker-compose.monitoring.yml` (no dashboard/render work)
