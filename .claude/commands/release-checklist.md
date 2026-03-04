---
description: "Pre-release чеклист BioETL — версии, тесты, docs, security, ADR, CI. Режимы: check, prepare, validate."
---

# /release-checklist

## Использование
```
/release-checklist [mode]
```
**Режимы:** `check` (default), `prepare`, `validate`

## check (default)

Run all checks, produce readiness report:

1. **Version consistency**: `uv run python -c "import bioetl; print(bioetl.__version__)"` vs `grep "^version" pyproject.toml`
2. **CHANGELOG**: `head -30 CHANGELOG.md` — [Unreleased] not empty, Keep-a-Changelog format
3. **Tests**: `uv run pytest tests/ -v --tb=short -q` — 0 FAILED, coverage ≥85%
4. **Type checking**: `uv run mypy --strict src/bioetl/` — 0 errors
5. **Linting**: `uv run ruff check src/ tests/` + `uv run ruff format --check src/ tests/`
6. **Security**: `make security` — no critical vulns
7. **ADR status**: `grep -r "Status:" docs/02-architecture/decisions/ADR-*.md | grep -v Accepted | grep -v Superseded`
8. **Docs**: orphan rate <10%, mkdocs.yml nav current
9. **Dependencies**: `uv run pip-audit --skip-editable`
10. **Git**: `git status --short` — no uncommitted changes

Output: table with 12 checks, Overall READY/NOT READY, blockers list.

## prepare

1. Ask release type: major | minor | patch
2. `make bump-version TYPE={type}`
3. Rename `[Unreleased]` → `[X.Y.Z] - YYYY-MM-DD` in CHANGELOG
4. Update RULES.md version header
5. Run `check` to verify

## validate
```bash
make ci 2>&1 | tail -30
# Or: make lint && make test && make security
```
