## Outcome

The documentation navigation KPI is within its existing hard limit and has no
orphan candidates, without raising limits or adding exclusions.

## Evidence

- Exact weekly KPI implementation reports outside-nav `139 > 135` and orphan
  candidates `14 > 0`.
- Orphans comprise one governance plan, ten sequence/state-machine diagram
  descriptions, and three root-level analysis documents.
- Machine evidence:
  `reports/audit-runs/20260814T112947Z-audit-seq-8ab59e2395/step-01-prompt.audit.cycle.docs/docs-kpi.json`.
- Audit finding:
  `reports/audit-runs/20260814T112947Z-audit-seq-8ab59e2395/step-01-prompt.audit.cycle.docs/findings.json` (`DOCS-004`).

## Acceptance

- Outside-nav count is at most 135.
- Orphan candidate count is zero.
- Remediation uses meaningful navigation/inbound links or justified
  relocation/archive; limits, exclusions, and baselines do not increase.

## Verification

```bash
python -m scripts.docs.checks.report_docs_kpi \
  --kpi-target-not-in-nav 120 \
  --hard-limit-not-in-nav 135 \
  --max-orphans 0 \
  --target-deadline 2026-12-31 \
  --fail-on-breach
pytest tests/architecture/test_docs_kpi_workflow.py tests/unit/scripts/test_report_docs_kpi.py -q --no-cov
```

## Constraints

- Do not create or modify `.env` / `.env.*`.
- Do not increase debt budgets, thresholds, exclusions, or allowlists.
- Do not commit, push, or merge into `main`; use a fix branch.
- Merge to `main` is outside this audit run (`ALLOW_MERGE=false`).
