______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-19'

______________________________________________________________________

# GitHub Local Workflow

## Repository

- Canonical default branch: `main`
- Local tracking branch: `origin/main`
- Always verify the effective remote before push/PR operations:

```bash
git remote -v
git config --get remote.origin.url
```

- If your local checkout points at a fork or a renamed repository, use the **actual `origin` URL** for push operations and pass an explicit `--repo <owner/name>` to `gh` when needed.

## Local checks

Before opening a PR, run the project checks expected by the repository:

```bash
# CI / single-OS checkout
uv run ruff check .
uv run ruff format --check .
uv run mypy --config-file pyproject.toml --strict --no-incremental src/bioetl
uv run python -m scripts.engineering.dev run-tests cov
```

For mixed Windows + WSL checkout, prefer the OS-specific wrappers instead of a
shared `.venv`:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
.\scripts\engineering\dev\run_pytest.ps1 tests\ --timeout=120 -n 1 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
bash scripts/engineering/dev/run_pytest.sh tests/ --timeout=120 -n auto --lf
bash scripts/engineering/dev/run_mypy.sh
```

The direct uv commands above are the canonical single-OS checks. The wrappers
remain the preferred route when the same checkout is used from both
PowerShell and WSL. For Windows PowerShell, keep the wrapper at `-n 1` unless
you explicitly raise `BIOETL_PYTEST_WINDOWS_XDIST_WORKERS`.

## Local Git hooks

Install the repository hooks through the maintained setup helper so
`pre-commit`, `pre-push`, and `commit-msg` stay aligned:

```bash
uv run python -m scripts.ops setup-plugins

# hook-only reinstall
bash scripts/ops/launchers/codex/setup_plugins.sh --hooks-only
```

Daily local hooks intentionally stay narrow:

- `pre-commit` runs fast formatting, file hygiene, config/schema path guards,
  root cleanliness, diagram checks when diagrams are touched, and a blocker for
  secret-bearing `.env` files.
- `commit-msg` performs a strict local Conventional Commit header fast-fail for
  newly authored commits. CI `commit-lint` remains tolerant of historical
  non-conventional and merge commits.
- `pre-push` runs the heavier local gates already configured for strict typing,
  architecture smoke, Bandit, and Gitleaks.

If hook execution fails with `git-lfs filter-process` errors, fix checkout
health before treating `--all-files` results as actionable:

```bash
python3 scripts/engineering/dev/run_project_python.py -m scripts.engineering.qa.check_test_audit_preflight --strict
```

Run the baseline hook suites explicitly when needed:

```bash
uv run python -m pre_commit run smoke-lane --hook-stage manual --all-files
uv run python -m pre_commit run --hook-stage pre-push --all-files
```

For a stricter pre-PR pass, use the maintained repository commands instead of
moving CI-scale checks into `pre-commit`:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy --config-file pyproject.toml --strict --no-incremental src/bioetl
uv run python -m scripts.engineering.dev run-tests quick
uv run python -m scripts.engineering.dev run-tests arch
python3 scripts/engineering/dev/run_project_python.py -m pre_commit run smoke-lane --hook-stage manual --all-files
```

Do not add repo-wide coverage verification, architecture governance,
documentation link crawls, observability metric inventory, Silver/Gold parity,
Docker/promtool, or VCR/LFS audit checks to default `pre-commit`; those surfaces
are too slow or environment-sensitive for the daily edit loop and remain
manual/CI gates.

## Recommended local Git defaults

The repository-local Git workflow is configured around fast-forward sync and conflict minimization:

```bash
git config --get-regexp '^(pull\.ff|push\.default|fetch\.prune|rerere\.enabled|rebase\.autosquash|branch\.autosetupmerge|branch\.autosetuprebase|merge\.conflictstyle)$'
```

Expected values:

- `pull.ff=only`
- `push.default=simple`
- `fetch.prune=true`
- `rerere.enabled=true`
- `rebase.autosquash=true`
- `merge.conflictstyle=zdiff3`
- `branch.autoSetupMerge=true`
- `branch.autoSetupRebase=always`

## Branch workflow

Create feature branches from `main` using the naming convention from the GitHub policy:

```bash
git switch main
git fetch --prune origin
git pull --ff-only
git switch -c feat/short-description
```

Allowed branch prefixes:

- `feat/`
- `fix/`
- `refactor/`
- `docs/`
- `test/`
- `chore/`
- `ci/`

## Preferred implementation workflow

For non-trivial work, prefer an isolated worktree instead of stacking changes in a dirty primary checkout:

```bash
git fetch --prune origin
git worktree add .worktrees/feat-short-description -b feat/short-description origin/main
cd .worktrees/feat-short-description
```

Use worktrees by default when:

- the main working tree already has local changes
- you are evaluating multiple approaches
- you are cherry-picking from bot or review branches
- the task is large enough to live for more than one commit

## Daily sync flow

Keep topic branches current without merge commits:

```bash
git fetch --prune origin
git rebase origin/main
```

Use `git pull --ff-only` on `main`, and prefer `git fetch + git rebase origin/main` on feature branches.

## Consolidation and cherry-pick flow

When multiple remote branches contain mixed-value commits, use a consolidation branch instead of merging noisy history:

```bash
git fetch --prune origin
git switch -c chore/consolidate-scope origin/main
git cherry-pick <sha1> <sha2>
```

Prefer cherry-pick over merge when:

- source branches include bot-generated churn
- only 1-3 commits are actually useful
- review branches contain reports, registries, or temporary artifacts
- you need a clean PR narrative

## Push and PR workflow

Push a new branch and create a PR:

```bash
git push -u origin HEAD
```

Then create the PR against the effective GitHub repository:

```bash
gh repo view --json nameWithOwner
gh pr create
```

If `gh` cannot infer the repository from the local checkout, pass the repository explicitly:

```bash
gh pr create --repo <owner/name>
```

Useful daily commands:

```bash
gh pr status
gh run list --limit 10
gh workflow list
```

## Commit format

Use Conventional Commits:

```text
<type>(<scope>): <description>
```

Examples:

- `feat(chembl): add activity pipeline`
- `fix(pubchem): handle rate limit 429`
- `docs: update github workflow guide`

## Required PR checks

The main blocking checks called out by repository policy are:

- `checks-complete`
- `coverage-verify`
- `schema-governance-status`
- `detect-secrets`
- `commit-lint`
- `type-check`

## Cleanup workflow

Prune stale remote-tracking refs regularly:

```bash
git fetch --prune origin
```

Delete merged local branches after PR completion:

```bash
git branch --merged main
git branch -d <branch-name>
```

Delete remote branches only after confirming the PR is merged and no longer needed:

```bash
git push origin --delete <branch-name>
```

## Notes

- The local repository is already connected to `origin`.
- The repository workflow assumes fast-forward-only sync on `main`.
- For larger tasks, isolated `git worktree` usage is the preferred path.
- For branch consolidation, prefer selective cherry-pick over merging noisy automation branches.
- In mixed Windows + WSL work, do not share the same `.venv`; use `.venv-win`
  in PowerShell and `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` in WSL.
