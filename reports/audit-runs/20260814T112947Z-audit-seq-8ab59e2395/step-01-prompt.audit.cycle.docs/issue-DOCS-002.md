## Outcome

The published documentation hub advertises the exact current governance
version from `docs/00-project/RULES.md`.

## Evidence

- `docs/00-project/RULES.md:3` is `Version: 6.1.10`.
- `docs/00-project/index.md:132` still says `v6.1.9`.
- `python -m scripts.engineering.repo check-versions` returns non-zero with the
  exact mismatch.
- The gate is required by `.github/workflows/tests.yml`, `docs.yml`, and
  `release.yml`.
- Audit evidence:
  `reports/audit-runs/20260814T112947Z-audit-seq-8ab59e2395/step-01-prompt.audit.cycle.docs/findings.json` (`DOCS-002`).

## Acceptance

- `docs/00-project/index.md` matches the current RULES governance version.
- Version-consistency regression tests pass.

## Verification

```bash
python -m scripts.engineering.repo check-versions
pytest tests/unit/scripts/engineering/repo/test_check_version_consistency.py -q --no-cov
```

## Constraints

- Do not create or modify `.env` / `.env.*`.
- Do not increase debt budgets, thresholds, exclusions, or allowlists.
- Do not commit, push, or merge into `main`; use a fix branch.
- Merge to `main` is outside this audit run (`ALLOW_MERGE=false`).
