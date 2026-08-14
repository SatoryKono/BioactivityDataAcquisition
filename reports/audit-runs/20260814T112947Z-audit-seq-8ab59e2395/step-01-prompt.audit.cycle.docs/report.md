# Step 01 — `prompt.audit.cycle.docs`

## Executive summary

- Baseline: `origin/main@8ab59e239589bb22bde0da54f4646a51b65feeab`.
- Scope: `README.md`, `docs/`, `mkdocs.yml`, `scripts/docs/`, relevant CI callers.
- Contours: `content` and `pipeline`; `MODE=full`, `DEPTH=full`, `N=1`.
- PROVEN findings: 4 (`P1=2`, `P2=2`, `P0=0`, `P3=0`).
- Baseline `surface_score`: content `1`, pipeline `0`, overall `0`.
- Candidate `surface_score`: content `3`, pipeline `3`, overall `3` for the
  audited docs surface.
- Links/spec/config checks, runtime mirror/freshness drift, docstrings and lock parity pass.
- The four audited findings are remediated and their targeted acceptance gates pass.

## Scope and method

The audit used `prompt.audit.docs-content` for purpose, information architecture,
freshness, commands, links and contradictions, and `prompt.audit.docs-pipeline`
for source → generator → validation → artifact → CI/publication. Existing
generated inventory was used as the per-file documentation inventory rather
than substituting a Markdown file count for semantic evidence.

## Results

| ID | Priority | Contour | Outcome |
| --- | --- | --- | --- |
| DOCS-001 | P1 | pipeline | Unified router rejects exact CI/documented argv for `verify` and `check-kpi`. |
| DOCS-002 | P1 | content | Published hub says RULES `v6.1.9`; canonical RULES is `6.1.10`. |
| DOCS-003 | P2 | pipeline | 52 prompt-library docs lack completed nav classification; cleanup inventory is stale. |
| DOCS-004 | P2 | content | KPI is `139 > 135` outside nav with `14 > 0` orphans. |

Full finding objects and exact commands are in `findings.json`.

## Positive evidence

- Full link scan: relative links, nav existence/scope, specs, configs, Gold
  contract index, workflow inventory, provider overview and governance sections
  pass; failure is isolated to not-in-nav growth.
- `python -m scripts.docs check-drift --runtime-mirrors --freshness --ai-surfaces --json`: PASS, 0 issues.
- `python -m scripts.docs check-docstrings --summary`: thresholds pass.
- `UV_CACHE_DIR=/tmp/bioetl-uv-cache uv lock --check`: PASS.
- `python -m bioetl --help`, `python -m scripts.ops --help`, and
  `python -m scripts.engineering.dev --help`: documented entrypoint families load.

## Baseline failed evidence

- `python -m scripts.docs verify --skip-build`: rc=2 at router boundary.
- Direct `python -m scripts.docs.checks.verify --skip-build`: rc=1 due 52
  not-in-nav additions.
- `python -m scripts.docs check-kpi ...`: rc=2 at router boundary.
- Direct KPI implementation: rc=1, outside-nav 139, orphans 14.
- `python -m scripts.engineering.repo check-versions`: rc=1, `6.1.9 != 6.1.10`.
- `python -m scripts.docs generate-cleanup-inventory --check`: rc=1 on a clean
  tracked snapshot; both generated artifacts differ.
- Focused docs test set: one failure,
  `test_documentation_cleanup_inventory_check_passes`; remaining selected tests pass.

## Post-fix verification

- `python -m scripts.docs verify --skip-build`: PASS.
- Isolated frozen docs environment, `python -m scripts.docs verify`: PASS,
  including strict MkDocs build (`321.77s`).
- Full links/spec/config/not-in-nav check: PASS (`273 <= 285`).
- Exact weekly KPI command through the unified router: PASS; outside nav
  `127 <= 135`, orphan candidates `0`.
- Cleanup inventory owner command in `--check` mode: PASS.
- Version consistency: PASS (`release=6.1.0`, `governance=6.1.10`).
- Targeted docs test matrix: PASS; Ruff and `git diff --check`: PASS.

## Repository-wide proof status

Proof-or-stop outcome is `STOP`, with `failed_receipt:governance` and
`failed_receipt:debt`. The failures are baseline-wide and outside this docs
diff: the scripts inventory is stale, while module-coverage/architecture debt
artifacts have pre-existing drift. No budget, threshold, baseline, exclusion,
or allowlist was increased to hide either failure. See `proof-verification.json`.

## Skipped / not verifiable

- No publish operation was attempted.
- No monitoring stack was started.

## Constraints preserved

- No `.env` or `.env.*` file was created or modified.
- No debt budget, threshold, exclusion or allowlist was increased.
- No commit, push or merge to `main` occurred.
- Runtime mirrors were audited but not changed; mirror sync is not applicable yet.

## Issue gate

Mandatory open-issue/open-PR duplicate search completed before creation. No
duplicate outcomes existed. Tracking issues #8807, #8808, #8809, and #8810
were closed after checkout-scoped evidence was posted. Candidate PR: #8813;
not merged.
