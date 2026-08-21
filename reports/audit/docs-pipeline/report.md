# Docs pipeline audit

Source run: `20260821T113346Z-docs-cycle-78d0fc88c7`.

`surface_score=2`. `check-links` (unflagged), `check-kpi`, and
`check-drift --ports --classes --runtime-mirrors --freshness` are green.
`docs.yml` runs `python -m scripts.docs verify` and passports check.
PROVEN pipeline gap: `scripts/docs/README.md` mapped `check-drift` /
`check-docstrings` to `architecture.yml` (#9322). MkDocs strict build not
executed in this Windows `.venv-win` (no `mkdocs` extra).

Canonical evidence: `reports/audit-runs/20260821T113346Z-docs-cycle-78d0fc88c7/`.
