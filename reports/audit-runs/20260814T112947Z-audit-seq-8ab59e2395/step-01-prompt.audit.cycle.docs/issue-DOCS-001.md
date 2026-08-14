## Outcome

All CI-owned and documented `python -m scripts.docs` commands forward their
declared arguments through the unified router.

## Evidence

- `scripts/engineering/common/cli_dispatch.py:55` rejects forwarded argv when a
  target exposes zero-argument `main()`.
- `scripts/docs/checks/verify.py:18` parses `sys.argv` but does not accept argv.
- `scripts/docs/checks/report_docs_kpi.py:421` has the same contract mismatch.
- `.github/workflows/tests.yml:1746` invokes
  `python -m scripts.docs verify --skip-build` and receives rc=2.
- `.github/workflows/docs-kpi-weekly.yml:30` invokes routed `check-kpi` with
  flags and receives rc=2 before report generation.
- Audit evidence:
  `reports/audit-runs/20260814T112947Z-audit-seq-8ab59e2395/step-01-prompt.audit.cycle.docs/findings.json` (`DOCS-001`).

## Acceptance

- `verify.main(argv)` and `report_docs_kpi.main(argv)` obey the shared router
  contract.
- Exact workflow commands reach argparse rather than returning router rc=2.
- Regression tests cover both routed commands with their CI flags.

## Verification

```bash
python -m scripts.docs verify --skip-build
python -m scripts.docs check-kpi --help
pytest tests/unit/scripts/test_cli_dispatch.py tests/architecture/test_docs_kpi_workflow.py -q --no-cov
```

## Constraints

- Do not create or modify `.env` / `.env.*`.
- Do not increase debt budgets, thresholds, exclusions, or allowlists.
- Do not commit, push, or merge into `main`; use a fix branch.
- Merge to `main` is outside this audit run (`ALLOW_MERGE=false`).
