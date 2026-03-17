# GitHub Local Workflow

## Repository

- Canonical repository: `SatoryKono/BioactivityDataAcquisition`
- Default branch: `main`
- Local branch tracking: `origin/main`

## Local checks

Before opening a PR, run the project checks expected by the repository:

```bash
make lint
make test
uv run python -m mypy --strict src/bioetl/
```

## Branch workflow

Create feature branches from `main` using the naming convention from the GitHub policy:

```bash
git switch main
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

## Push and PR workflow

Push a new branch and create a PR:

```bash
git push -u origin HEAD
gh pr create --repo SatoryKono/BioactivityDataAcquisition
```

If `gh` cannot infer the repository from the local checkout, always pass:

```bash
--repo SatoryKono/BioactivityDataAcquisition
```

Useful daily commands:

```bash
gh pr status --repo SatoryKono/BioactivityDataAcquisition
gh run list --repo SatoryKono/BioactivityDataAcquisition --limit 10
gh workflow list --repo SatoryKono/BioactivityDataAcquisition
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

## Notes

- The local repository is already connected to `origin`.
- The current GitHub CLI account is authenticated.
- The repository uses fast-forward-only pulls and `push.default=simple` in local Git config.
