# Root Hygiene Refactoring Plan - 2026-07-08

Status: active verification plan

Owner: Engineering / Architecture

Related issues: HGN-001, HGN-002, HGN-003, HGN-004, HGN-005, HGN-006

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
