## Outcome

The new prompt-library documentation has an intentional published/repo-only
classification and the deterministic cleanup inventory is current, without
raising the not-in-nav debt baseline.

## Evidence

- `python -m scripts.docs check-links --not-in-nav-growth` returns rc=1 with
  52 additions against the exact 285-path baseline.
- Most additions are under `docs/00-project/ai/prompts/fragments/` and
  `docs/00-project/ai/prompts/library/`, including the canonical cycle cards.
- `mkdocs.yml:973` publishes only a subset of the prompt library.
- On a clean tracked snapshot of `8ab59e239589`,
  `python -m scripts.docs generate-cleanup-inventory --check` reports drift in
  both generated cleanup artifacts.
- Audit evidence:
  `reports/audit-runs/20260814T112947Z-audit-seq-8ab59e2395/step-01-prompt.audit.cycle.docs/findings.json` (`DOCS-003`).

## Acceptance

- Every new prompt card is intentionally navigated, consolidated, or routed by
  the existing ownership model.
- `scripts/engineering/baselines/not_in_nav_baseline.txt` is not increased.
- Cleanup inventory is regenerated only through its owner command.
- Full link and cleanup-inventory checks pass.

## Verification

```bash
python -m scripts.docs check-links --not-in-nav-growth
python -m scripts.docs generate-cleanup-inventory --check
python -m scripts.docs verify --skip-build
```

## Constraints

- Do not create or modify `.env` / `.env.*`.
- Do not increase debt budgets, thresholds, exclusions, or allowlists.
- Do not delete unique prompt cards or invent replacement SSOT.
- Do not commit, push, or merge into `main`; use a fix branch.
- Merge to `main` is outside this audit run (`ALLOW_MERGE=false`).
