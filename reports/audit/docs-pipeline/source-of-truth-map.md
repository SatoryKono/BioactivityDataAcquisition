# Source of truth map (docs pipeline)

| Surface | SoT | Generator / checker |
| --- | --- | --- |
| Unified docs CLI | `scripts/docs/__main__.py` | `python -m scripts.docs <cmd>` |
| Link/spec/config | `scripts/docs/checks/check_links.py` | `python -m scripts.docs check-links` |
| Drift | `scripts/docs/checks/check_drift.py` | `python -m scripts.docs check-drift` |
| KPI | `scripts/docs/checks/report_docs_kpi.py` | `python -m scripts.docs check-kpi` |
| Cleanup inventory | `docs/reports/generated/documentation-cleanup-inventory.*` | `python -m scripts.docs generate-cleanup-inventory` |
| Verify chain | `scripts/docs/checks/verify.py` | `python -m scripts.docs verify` |
| CI docs gate | `.github/workflows/docs.yml` | `python -m scripts.docs verify` |
| Nav | `mkdocs.yml` | MkDocs `--strict` (not reached this run) |
| AI runtime | `.codex/**` ≡ `.junie/**` | docs mirrors only |
