# Docs pipeline audit

Cycle-run: `20260827T0846Z-docs-new-b9aa36efdd`  
Method: `prompt.audit.docs-pipeline`  
`surface_score`: **2**

## Chain

`python -m scripts.docs` → `check-links` / `check-drift` / `check-kpi` / `generate-cleanup-inventory` / `verify` → CI `docs.yml` + `tests.yml` producer.

## Command evidence

| Command | Exit |
| --- | --- |
| `check-links --links --specs --configs` | 0 |
| `check-drift --runtime-mirrors --freshness` | 0 |
| `check-kpi` | 0 (on_track; outside-nav 118 ≤ 120) |
| `generate-cleanup-inventory --check` | 0 after `--update` |
| `verify --skip-build` | 0 (`functions 90.0% >= 90%`) |

Full `verify` (MkDocs `--strict`) not reached: docstring step fails first.

`tests.yml` `docs_runtime` captures verify rc then `exit 0`.

Retired top-level `scripts/docs.py` shims: not restored.

## Findings

| ID | P | Outcome |
| --- | --- | --- |
| AUD-DOC-001 | P2 | remediated in worktree |
| AUD-DOC-003 | P2 | remediated in worktree (functions 90.0%; threshold unchanged) |
| AUD-DOC-004 | P3 | remediated in worktree (outside-nav 118 ≤ 120; hard 135 unchanged) |

## Kit extras

`docs-pipeline.csv`, `generated-files.csv`, `docs-build.log` (iteration copy), `link-report.json`, `source-of-truth-map.md`
