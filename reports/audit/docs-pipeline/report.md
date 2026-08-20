# Docs pipeline audit

Source run: `20260820T064946Z-docs-cycle-d297d3d14b`.

`surface_score=2`. `check-links`, `check-kpi`, and `check-drift --ports --classes` were green. `check-drift --runtime-mirrors --freshness` failed until SUMMARY.md was refreshed. `python -m scripts.docs verify` now includes those flags (#9115). Residual: freshness is still not on a scheduled workflow (#9114). Exit 0 on verify-slice is not claimed as semantic completeness of the whole docs corpus.

Canonical evidence: `reports/audit-runs/20260820T064946Z-docs-cycle-d297d3d14b/`.
