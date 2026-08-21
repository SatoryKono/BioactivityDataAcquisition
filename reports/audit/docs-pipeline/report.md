# Docs pipeline audit

Source run: `20260821T082249Z-docs-cycle-9c56e1edbb`.

`surface_score=2`. `check-links` (after content fix), `check-kpi`, and
`check-drift --ports --classes --runtime-mirrors --freshness` are green.
`python -m scripts.docs verify` includes unflagged `check-links` and
`--runtime-mirrors --freshness`. Residual: `docs.yml` path filters omit
`.github/workflows/**` (#9266). MkDocs strict build not executed in this
Windows `.venv-win` (no `mkdocs` extra).

Canonical evidence: `reports/audit-runs/20260821T082249Z-docs-cycle-9c56e1edbb/`.
