# Root Hygiene Refactoring Plan - 2026-07-08

Status: closed verification record

Owner: Engineering / Architecture

Related issues: HGN-001, HGN-002, HGN-003, HGN-004, HGN-005, HGN-006,
HGN-007, HGN-008, HGN-009, HGN-011, HGN-012, HGN-013, HGN-014, HGN-015,
HGN-017, HGN-019

## Verified Baseline

The root hygiene refactoring plan separates governed tracked root surfaces from
local working-tree clutter.

Current verified tracked baseline:

- `scripts/engineering/repo/audit_root_cleanliness.py` validates 45 root files
  and 12 root directories.
- `.github/root-allowlist.txt` contains 45 allowed tracked root file entries.
- The current root policy keeps `.mcp.json`, core Docker compose files,
  `Dockerfile.bioetl`, AI runtime entrypoints, and reviewed launcher/setup
  shims at root while exact-root contracts still apply.

Current strict-local baseline:

- `.mypy_cache/` is a reviewed local mypy cache. It may exist untracked and may
  be pruned by the reviewed root-local cleanup tooling.
- `path/` has no root governance owner and must not be promoted to allowlist or
  tolerated local root governance.
- root `silver/` is a forbidden generated-output root. Silver outputs belong
  under governed data output locations such as `data/output/silver/**`.

Already-ignored local surfaces that must not be reintroduced as plan actions:

- `.env` is secret-bearing local state and is ignored by `*.env`. Agents must
  not create, edit, move, delete, rename, or inspect `.env*` content without
  explicit per-task user approval.
- `mcp-shell.log` is ignored by `*.log`.
- `.vscode/` and `.cursor/` are explicitly ignored local/editor roots unless
  curated content is promoted through structure governance.

## HGN-001 / HGN-003 Cleanup Model

Use exact reviewed candidates, not broad repository cleanup.

Resolution:

- Delete or rehome unexpected root `path/` when it appears.
- Delete root `silver/` when it appears; do not add it to
  `local_tolerated_root_dirs`.
- Treat `.mypy_cache/` as a reviewed local cache that remains untracked and is
  eligible for exact root-local cleanup.
- Keep `.env*` out of cleanup automation unless an explicit security task
  grants permission.

Required validation:

```bash
./.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
./.venv/bin/python scripts/engineering/repo/cleanup_root_local_clutter.py --json
./.venv/bin/python -m scripts.engineering.repo check-root-review-registry
```

## HGN-004 Codex / WSL Shim Exit Criteria

The following root shims are retired from the repository root. Operator flows
must use the scripts-owned replacements:

| Retired root shim | Canonical owner | Restoration policy |
| --- | --- | --- |
| `.wsl_proxy_env.sh` | `scripts/engineering/dev/bash/.wsl_proxy_env.sh` | Do not restore root sourcing shim without fresh owner review. |
| `codex.bat` | `scripts/ops/codex.bat` | Do not restore root CMD transport. |
| `codex.ps1` | `scripts/ai/codex/run-codex.ps1` | Do not restore root PowerShell transport. |
| `setup-codex-wsl.bat` | `scripts/ai/codex/setup-codex-wsl.bat` | Do not restore root Windows setup transport. |
| `setup-codex-wsl.ps1` | `scripts/ai/codex/setup.ps1` | Deletion-first decision; do not add a new alias without lifecycle review. |
| `setup-codex-wsl.sh` | `scripts/ai/codex/helper/setup-wsl-complete.sh` | Do not restore root Bash setup transport. |

Validation:

```bash
git ls-files '*.sh' '*.ps1' '*.py' '*.bat' | awk -F/ 'NF == 1 { print }'
./.venv/bin/python -m pytest tests/architecture/test_root_hygiene_issues_5992_5999_closeout.py::test_issue_5994_root_codex_shims_are_retired_from_root -q
```

If any root script appears in the filtered `git ls-files` output, root script
hygiene has regressed.

## HGN-005 Docker Setup Shim Exit Criteria

Core Docker root entrypoints remain at root while exact-root operator contracts
exist:

- `Dockerfile.bioetl`
- `docker-compose.yml`
- `docker-compose.monitoring.yml`
- `docker-compose.codex.yml`
- `docker-compose.neo4j.yml`
- `docker-compose.neo4j-audit.yml`

Root `docker-setup.ps1` and `docker-setup.sh` are retired. Their legacy verbs
are retained in `scripts/ops/docker-setup.ps1` and
`scripts/ops/docker-setup.sh`.

Exit criterion for keeping them retired:

1. All operator docs and scripts point to `scripts/ops/docker-setup.ps1` or
   `scripts/ops/docker-setup.sh`.
2. CI, README, Makefile, and pyproject references no longer require the root
   filenames.
3. The Docker helper relocation audit keeps the RF-003 command compatibility
   matrix current.
4. `.github/root-allowlist.txt` and
   `configs/quality/root_hygiene_review_registry.yaml` continue to mark root
   setup helpers absent.

Reference-map command:

```bash
rg -n "docker-setup\\.(ps1|sh)|docker-compose(\\.monitoring|\\.codex|\\.neo4j-audit|\\.neo4j)?\\.yml|Dockerfile\\.bioetl" .github docs scripts README.md Makefile pyproject.toml configs/quality/root_hygiene_review_registry.yaml
```

## HGN-006 Regression Control

Root hygiene closure requires all of the following gates:

```bash
uv run python -m scripts.engineering.repo check-cleanliness --strict-untracked --check-local-forbidden-outputs
uv run python -m scripts.engineering.repo check-cleanup-governance
uv run python -m scripts.engineering.repo check-root-governance-docs
uv run python -m scripts.engineering.repo check-root-review-registry
uv run python -m scripts.engineering.diagnostics audit-structure --path .
uv run pytest tests/unit/scripts/repo/test_audit_root_cleanliness.py tests/unit/scripts/repo/test_check_cleanup_governance.py tests/unit/scripts/repo/test_check_root_governance_docs.py tests/unit/scripts/repo/test_audit_structure.py tests/unit/scripts/repo/test_check_root_hygiene_review_registry.py tests/unit/scripts/repo/test_cleanup_repository.py tests/unit/scripts/repo/test_cleanup_root_local_clutter.py tests/architecture/test_root_hygiene_workflow.py tests/architecture/test_root_hygiene_review_registry.py -q
```

Definition of done:

- strict root hygiene passes;
- root `silver/` stays forbidden;
- `.mypy_cache/` handling is explicit and reviewed;
- tracked root allowlist changes are synchronized with policy, registry, and
  tests;
- no cleanup step targets `.env*` without explicit security approval.

## HGN-003 Through HGN-019 Final Closure Report - 2026-07-10

This closure pass verifies that the root minimization and documentation hygiene
work is complete without increasing any technical-debt budget and without
changing runtime architecture, DDD boundaries, Medallion pipeline behavior, or
`src/bioetl/**/*.py`.

### Issue Disposition Matrix

| Issue | Closure evidence | Decision |
| --- | --- | --- |
| HGN-003 / #6173 | `.github/ISSUES/**` is classified by `docs/reports/generated/documentation-cleanup-inventory.{json,md}` as issue mirrors, issue packs, drafts, indexes, or guides. Live mirrors retain `reconcile-with-github-state`; drafts and packs retain `archive-after-github-state-check`. | No broad deletion. Future cleanup must reconcile exact paths against GitHub state before archive or removal. |
| HGN-004 / #6174 | `docs/plans/README.md` and `configs/quality/repo_structure_catalog.yaml` enforce `max_active_backlog = 1`; `docs/plans/consolidated-open-tasks-plan-2026-03-21.md` remains the only active backlog. | Closed. Additional plan artifacts must be supporting context or move to `docs/99-archive/plans/**`. |
| HGN-005 / #6175 | `docs/reports/generated/documentation-cleanup-inventory.{json,md}` classifies `docs/reports/**` and route-owned generated reports; `configs/quality/generated_artifact_routing.yaml` remains the generator contract. | Closed. Retain evidence reports when lifecycle says `keep`; archive only after migration. |
| HGN-007 / #6177 | `configs/quality/generated_artifact_routing.yaml` owns `ai-skill-reference-mirror` and `ai-skill-license-mirrors` through `scripts/ai/codex/check_skills_mirror.sh`. | Closed. Skill mirror duplicates are generator-owned checks, not manual cleanup targets. |
| HGN-008 / #6178 | `configs/quality/repo_structure_catalog.yaml` has `docs_drafts.allowed_files: []`; `find docs -maxdepth 1 -name 'D-*.md' -print` returned no flat D-series files. Root documentation entrypoints are retained through root allowlist and file policy. | Closed. D-series reintroduction requires catalog and successor review. |
| HGN-009 / #6179 | `docs/03-guides/docs-verification.md` documents `python -m scripts.docs generate-cleanup-inventory --check` and the full docs verification helper path. The inventory check passed in this closure pass. | Closed. Final docs hygiene gate is deterministic and route-backed. |
| HGN-011 / #6188 | `cleanup-root-local-clutter --include-logs --apply --json` removed reviewed local root clutter: `.benchmarks`, `.coverage`, `.import_linter_cache`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.xml`, `coverage.xml`, `logs`, `mcp-shell.log`, `test-output`, and `tmp`. | Closed with bounded residuals: `.hypothesis`, regenerated `.pytest_cache`, and locked `Test Results - Pytest_All.html` are local-only cleanup candidates; strict root audit still passes. `.env` was not touched. |
| HGN-012 / #6189 | `.aiassistant/` is absent from the working root. `docs/00-project/governance/03-file-policy.md` treats `.aiassistant/` as local/vendor/editor state unless explicitly promoted. | Closed. No root ownership promotion is needed. |
| HGN-013 / #6190 | Root AI launcher/setup shims are retired by file policy and registry; `git ls-files '*.sh' '*.ps1' '*.py' '*.bat' \| awk -F/ 'NF == 1 { print }'` returned no tracked root script shims. | Closed. Maintained launchers stay under `scripts/ai/**`, `scripts/ops/**`, or `scripts/engineering/**`. |
| HGN-014 / #6191 | `docs/05-operations/verification/docker-helper-root-relocation-audit.md` includes the RF-003 command compatibility matrix for `check`, `build`, `start`, `start-full`, `stop`, `stop-full`, `logs`, `health`, and `clean`. | Closed. Root `docker-setup.*` remains retired; scripts-owned helpers retain parity. |
| HGN-015 / #6192 | `docs/00-project/governance/03-file-policy.md`, `.github/root-allowlist.txt`, `configs/quality/root_hygiene_review_registry.yaml`, and the Docker relocation audit document root-required compose and `Dockerfile.bioetl` boundaries. | Closed. Required exact-root Docker files stay root until workflows/docs/helpers are repointed or wrapped. |
| HGN-017 / #6194 | Root vendor/tool exact-filename contracts are documented in file policy and machine-readable root governance; exact-root `.mcp.json`, package/tool config, human-facing docs, and Docker contracts remain allowlisted only where required. | Closed. No unreviewed moves remain in scope for this wave. |
| HGN-019 / #6196 | Final root minimization gates passed: strict cleanliness, cleanup governance, root governance docs, root review registry, structure audit, documentation cleanup inventory, and targeted tests. | Closed. The root minimization wave is complete. |

### Validation Snapshot

Commands run in this closure pass:

```bash
./.venv/bin/python -m scripts.engineering.repo check-cleanliness --strict-untracked --check-local-forbidden-outputs
./.venv/bin/python -m scripts.engineering.repo check-cleanup-governance
./.venv/bin/python -m scripts.engineering.repo check-root-governance-docs
./.venv/bin/python -m scripts.engineering.repo check-root-review-registry
./.venv/bin/python -m scripts.engineering.diagnostics audit-structure --path .
./.venv/bin/python -m scripts.docs generate-cleanup-inventory --check --print-summary
./.venv/bin/python -m scripts.docs check-links --links --specs --configs
./.venv/bin/python -m pytest tests/unit/scripts/repo/test_cleanup_root_local_clutter.py tests/unit/scripts/repo/test_audit_root_cleanliness.py tests/unit/scripts/repo/test_check_cleanup_governance.py tests/unit/scripts/repo/test_check_root_governance_docs.py tests/unit/scripts/repo/test_audit_structure.py tests/unit/scripts/repo/test_check_root_hygiene_review_registry.py tests/architecture/test_root_hygiene_review_registry.py tests/architecture/test_root_hygiene_workflow.py -q
find docs -maxdepth 1 -name 'D-*.md' -print
git ls-files '*.sh' '*.ps1' '*.py' '*.bat' | awk -F/ 'NF == 1 { print }'
./.venv/bin/python -m scripts.engineering.repo cleanup-root-local-clutter --include-logs --json
git check-ignore -v .env .coverage coverage.xml 'Test Results - Pytest_All.html' .xml mcp-shell.log .hypothesis .pytest_cache
```

Results:

- strict root layout audit passed with 37 root files and 13 root directories;
- cleanup governance guardrails passed;
- root governance docs align with machine-readable governance surfaces;
- root hygiene review registry is valid;
- structure audit reported 0 MUST and 0 SHOULD findings;
- documentation cleanup inventory is synchronized;
- docs link/spec/config checks passed;
- targeted pytest batch passed with 62 tests;
- no tracked flat `docs/D-*.md` files were found;
- no tracked root `.sh`, `.ps1`, `.py`, or `.bat` shims were found;
- cleanup dry-run after validation reported only `.hypothesis`, regenerated
  `.pytest_cache`, and locked local `Test Results - Pytest_All.html`;
- `.env` remains ignored and was not read, edited, moved, or deleted.

Skipped as out of scope for this governance-only closure: full repository
pytest, full mypy, full ruff, and architecture hash refresh. No
`src/bioetl/**/*.py` files changed, so the module coverage inventory source-tree
hash refresh requirement does not apply.
