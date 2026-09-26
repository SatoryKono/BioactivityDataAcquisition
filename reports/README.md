# `reports/` — working outputs (repo-only)

**Status:** active orientation (docs-cycle remediation)  
**Class:** repo-only (not published in MkDocs nav)

This tree holds **generated or working** analysis outputs before any curation
into `docs/reports/**`. It is **not** normative SSOT.

## What belongs here

| Path pattern | Role |
| --- | --- |
| `reports/quality/**` | Debt gates, residual snapshots, inventories, closeouts |
| `reports/audit/**`, `reports/audit-runs/**` | Audit pair outputs and cyclic runs |
| `reports/observability/**` | Grafana/prom live evidence, screenshots |
| `reports/docs-evidence/**` | Bulk historical docs evidence packs |
| Other `reports/<topic>/` | Model-specific or one-off investigations |

## What does **not** belong here

- Active operator/contributor instructions → `docs/00-05/**`
- Curated thin manifests → `docs/reports/**`
- Secrets or raw `.env` contents (never)

## Related

- Curated map: [`docs/reports/README.md`](../docs/reports/README.md)
- File policy: `docs/00-project/governance/03-file-policy.md`
- Docs verification: `docs/03-guides/docs-verification.md`

Regenerate quality artifacts only via project scripts (for example
`python -m scripts.engineering.qa …`). Do not hand-edit gate JSON to greenwash
budgets.
