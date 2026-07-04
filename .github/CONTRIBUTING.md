# Contributing to BioETL

## Quick Start

```bash
# 1. Clone and install
# Clone the canonical repository or your fork, then verify origin:
git clone <repo-url>
cd BioactivityDataAcquisition
git remote -v
uv sync --extra dev --extra tests --extra tracing
# Windows/.venv fallback:
# .venv/Scripts/python.exe -m pip install -e .[dev,tests]

# 2. Run checks before any changes
make lint && make test

# 3. After changes
make lint && make test && git commit
```

## Essential Reading

Before contributing, read these documents:

|| Document                                                           | Purpose                           |
|| ------------------------------------------------------------------ | --------------------------------- |
|| [docs/00-project/NORMATIVE_SOURCES.md](../docs/00-project/NORMATIVE_SOURCES.md) | Normative stack index (start here) |
|| [docs/00-project/RULES.md](../docs/00-project/RULES.md)            | Project constitution (MUST read)  |
|| [docs/01-requirements/REQUIREMENTS.md](../docs/01-requirements/REQUIREMENTS.md) | Testable requirements (MUST read) |
|| [AGENTS.md](../AGENTS.md)                                          | Development workflow and patterns |
|| [docs/00-project/00-map.md](../docs/00-project/00-map.md)          | Documentation navigator           |
|| [GitHub Policy](../docs/00-project/governance/05-github-policy.md) | CI/CD, branch protection, reviews |

## Workflow

1. **Create branch** from `main`
1. **Prefer an isolated worktree** for non-trivial tasks
1. **Read** relevant sections of RULES.md
1. **Implement** following architecture constraints
1. **Test** (`make test` before AND after changes)
1. **Lint** (`make lint`)
1. **Commit** using Conventional Commits format

For the full local GitHub workflow, including worktrees, sync/rebase, PR creation, and cleanup, see:

- [docs/03-guides/github-local-workflow.md](../docs/03-guides/github-local-workflow.md)

### Governance Metrics Note

- `check-c901` is the blocking baseline for new complexity debt.
- Scorecard file-size values describe **exemption debt** from `configs/quality/architecture_metric_exemptions.yaml`.
- Raw large-file counts like `>10 KB` or `>350 LOC` are **hotspot inventory**, not automatically blocking debt.
- When you need the structural size snapshot, use the canonical command in [`scripts/engineering/README.md`](../scripts/engineering/README.md) and treat the result as analysis/evidence unless a policy explicitly says otherwise.

## Commit Format

```
<type>(<scope>): <description>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Examples:**

- `feat(chembl): add activity pipeline`
- `fix(pubchem): handle rate limit 429`
- `docs: update architecture diagram`

## Architecture Constraints

### Layer Dependencies (MUST follow)

|| From ↓ / To →      | domain | application | composition | infrastructure | interfaces |
|| ------------------ | ------ | ----------- | ----------- | -------------- | ---------- |
|| **domain**         | ✅     | ❌          | ❌          | ❌             | ❌         |
|| **application**    | ✅     | ✅          | ❌          | ❌             | ❌         |
|| **composition**    | ✅     | ✅          | ✅          | ✅             | ❌         |
|| **infrastructure** | ✅     | ❌          | ❌          | ✅             | ❌         |
|| **interfaces**     | ✅     | ✅          | ✅          | ❌             | ✅         |

### Key Rules

- **Dependency Injection**: Dependencies via constructor, not created inside classes
- **Composition Root**: `src/bioetl/composition/bootstrap/` is the only place for wiring
- **Adapter HTTP**: Provider/runtime HTTP goes through `UnifiedHTTPClient`; do not bypass it with direct client usage in adapters
- **Blocking I/O**: Use `run_in_executor` for blocking operations
- **Logging**: Use `structlog` with `run_id`, never `print()`
- **Secrets**: Environment variables only (`BIOETL_{PROVIDER}_{KEY}`)

Direct `interfaces -> infrastructure` imports are forbidden. If an interface
needs concrete runtime behavior, route it through composition-owned entrypoints
instead of importing infrastructure modules directly.

## Testing Requirements

|| Type         | Directory             | Requirements                                           |
|| ------------ | --------------------- | ------------------------------------------------------ |
|| Unit         | `tests/unit/`         | No mocking domain entities, mock ports only            |
|| Integration  | `tests/integration/`  | VCR.py for HTTP, sanitize secrets from cassettes       |
|| Architecture | `tests/architecture/` | Validates layer imports, contracts, naming, governance |

**Coverage target:** ≥85% line coverage

Canonical integration / E2E / VCR execution policy, including replay vs refresh
rules and local/CI command paths, is documented in
[docs/03-guides/testing.md](../docs/03-guides/testing.md) and tracked in
`configs/quality/integration_vcr_policy.yaml`.

## Branch Protection / PR Validation

Direct merges to `main` are currently allowed. When you open a PR, keep these
checks green even though GitHub branch protection is not currently enforcing
them:

- `checks-complete` (from `.github/workflows/import-linter.yml` — lint, C901 governance, import-linter + architecture gates)
- `coverage-verify` (from `.github/workflows/tests.yml` — 85% coverage threshold)
- `type-check` (from `.github/workflows/type-checking.yml` — mypy strict compliance)
- `Schema Governance Status` (from `.github/workflows/schema-governance.yml`)
- `detect-secrets` (from `.github/workflows/security.yml`)
- `root-hygiene` (from `.github/workflows/root-hygiene.yml` — root allowlist, docs/plans catalog, and generated artifact bans)

These checks still reduce the risk of merging failing tests, lint errors, or
secret leaks.

`checks-complete` is intentionally non-skippable: `.github/workflows/import-linter.yml`
must materialize on every PR and push, including docs-only or markdown-only
changesets.

### Import-linter local repro

Canonical local command:

```bash
uv run lint-imports --config .importlinter
```

If `tests/architecture/test_layer_dependencies.py::test_import_linter_contracts`
skips locally, treat that as a degraded local environment and install the full
test capability set before trusting the result. Required CI exports
`BIOETL_REQUIRE_TEST_CAPABILITIES=1`, so missing `lint-imports`,
missing import-linter dependencies, or import-linter encoding/runtime failures
must fail fast there instead of silently skipping.


### Dependency Preflight Triage

If many jobs fail quickly, inspect `dependency-preflight` first.
Download and review `reports/ci/dependency-preflight.log` from its artifact and summary before debugging downstream jobs.

### Triage rule for `checks-complete`

- If `checks-complete` fails, **always** open job logs in this order first:
  1. `lint`
  2. `c901-governance`
  3. `arch-tests`
- `checks-complete` is an aggregate status and **must not be debugged separately**.

## Pull Request Checklist

- [ ] `make lint` passes
- [ ] `make test` passes (before AND after changes)
- [ ] No hardcoded secrets or paths
- [ ] Documentation updated if behavior changed
- [ ] Follows Conventional Commits format

## Getting Help

- **Questions**: Open an issue
- **Bugs**: Include reproduction steps
- **Features**: Discuss in issue first

## RFC 2119 Keywords

- **MUST**: Absolute requirement, violation is a release blocker
- **SHOULD**: Strong recommendation, deviation requires justification in PR
- **MAY**: Optional, developer discretion

## Troubleshooting

### Common Issues

**1. "Watermark not found" errors**

- Check local state under `data/output/checkpoints/` and `data/output/bronze/`.
- Ensure `Watermark` class usage is consistent (use `Watermark.from_*` factory methods).

**2. "Lock acquisition failed"**

- BioETL runs in Local-Only mode and uses in-process/local lock implementations, not Redis.
- Check logs for `Lock lost` / `lock_acquisition_failed` messages and remove stale local state only if the run was interrupted.

**3. "Missing dependencies"**

- Re-sync the environment: `uv sync --extra dev --extra tests --extra tracing`.
- Or use the local virtualenv fallback if `uv` is unavailable.
- Check `pyproject.toml` for new groups.

**4. "ERROR: Missing required plugins: pytest-asyncio>=0.23, pytest-cov>=4.0"**

- Установите тестовые зависимости перед запуском: `make install` или `pip install -e .[tests]`.
- При использовании uv запустите `uv sync --extra tests --extra dev`.
- Убедитесь, что активировано корректное окружение (`uv run` или `source .venv/bin/activate`).

### Observability & Metrics

- Metrics are available at `http://localhost:8000/metrics`.
- Dashboards are in `grafana/dashboards/`.
- Tracing is disabled by default. To enable: `export BIOETL_OBSERVABILITY__TRACING_ENABLED=true`.
