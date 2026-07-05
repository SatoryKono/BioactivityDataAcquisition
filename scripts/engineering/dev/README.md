# scripts/dev — Developer Workflows

Local developer setup and test utilities.

## Canonical Bootstrap

For normal local onboarding, prefer the maintained project entrypoints:

```bash
make install
make test-deps
make setup-plugins
make precommit-install  # hook-only reinstall via the same maintained hook installer
python -m scripts.engineering.dev setup-mcp  # optional MCP tooling via canonical backend
```

`python -m scripts.engineering.dev setup` is a retained legacy command that now fails fast with guidance to use `make install` or `setup-mcp`. Repository-local references to `dev_setup.sh` should be treated as historical compatibility evidence, not as proof that it is a canonical onboarding command.

## Stable Dual-OS Environments

If you work from both Windows PowerShell and WSL against the same checkout, do
not share a single `.venv`. Use separate environment directories instead:

```text
.venv-win  # PowerShell / native Windows Python
$HOME/.venvs/bioetl  # WSL / Linux Python by default
```

Bootstrap commands:

```powershell
.\scripts\engineering\dev\setup_env_windows.ps1
```

```bash
bash scripts/engineering/dev/setup_env_wsl.sh
```

Preferred runners automatically select the OS-appropriate environment:

```powershell
.\scripts\engineering\dev\run_pytest.ps1 tests\unit --narrow --timeout=120 --lf
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
bash scripts/engineering/dev/run_pytest.sh tests/unit --narrow --timeout=120 --lf
bash scripts/engineering/dev/run_mypy.sh
bash scripts/engineering/dev/pretest_guardrails.sh --mode check --scope full
bash scripts/engineering/dev/pretest_guardrails.sh --mode auto --scope full  # explicit write-capable metadata refresh
bash scripts/engineering/dev/run_pytest_sharded.sh
bash scripts/engineering/dev/run_pytest_sharded.sh --stream
bash scripts/engineering/dev/run_pytest_sharded.sh --tail
```

For fast, reproducible narrow slices during refactoring, use the explicit
`--narrow` mode:

```bash
bash scripts/engineering/dev/run_pytest.sh --narrow --collect-only tests/architecture/test_boundary_assertions.py
bash scripts/engineering/dev/run_pytest.sh --narrow tests/architecture/test_boundary_assertions.py
bash scripts/engineering/dev/run_mypy.sh --narrow --config-file pyproject.toml --strict src/bioetl/domain/__init__.py
python -m scripts.engineering.dev probe-quality --timeout 15
```

`--narrow` intentionally favors startup stability over full plugin/import graph
coverage:

- `run_pytest.* --narrow` disables plugin autoload and uses a minimal explicit
  plugin allowlist suitable for narrow architecture and unit slices
- `run_mypy.* --narrow` adds `--follow-imports=skip` so single-file strict
  probes do not walk the whole repository graph

`run_mypy.sh` and `run_mypy.ps1` also default to platform-specific cache
directories (`.mypy_cache/linux` and `.mypy_cache/windows`) to avoid cache
corruption when the same checkout is used from both WSL/Linux and Windows. To
override that behavior, pass `--cache-dir ...` explicitly or set
`BIOETL_MYPY_CACHE_DIR`.

`run_pytest.ps1` and `run_pytest.sh` both add default pytest flags unless you ask
for help/version. Local wrappers now keep coverage opt-in so the default startup
path stays lightweight; use `--with-coverage` or
`BIOETL_PYTEST_WITH_COVERAGE=1` when you intentionally want local coverage
instrumentation. `--collect-only` continues to avoid coverage instrumentation:

```text
-q --maxfail=1
```

Behavior differs slightly by platform:

- `bash scripts/engineering/dev/run_pytest.sh` runs `bash scripts/ops/launchers/codex/setup_plugins.sh --pytest-only`
  first, so missing pytest plugins can be auto-installed in the selected Python environment.
- `.\scripts\engineering\dev\run_pytest.ps1` assumes `.venv-win` is already prepared via
  `.\scripts\engineering\dev\setup_env_windows.ps1` or `make setup-plugins`.

Auto-preflight is now limited to full-repo selections (`tests`, no explicit
path) plus architecture/config-heavy slices such as `tests/architecture/`,
`tests/integration/config/`, and `tests/integration/ci/`. For other local runs,
invoke `bash scripts/engineering/dev/pretest_guardrails.sh --scope full`
explicitly when you want the cleanup + governance pass. The preflight cleans
common cache/build artifacts, refreshes the scripts inventory manifest, checks
inventory/lifecycle/catalog governance, verifies docs, and runs a targeted
fail-fast architecture slice for the recurring doc/governance regressions.
The same preflight also checks the committed RF-06 hotspot-family baseline
artifact via `python -m scripts.engineering.qa report-family-baseline --check`.
It now also validates the `src/memory/` subsystem, runs a refresh smoke on a
temporary output root, exercises the lightweight pre/post workflow smoke, and
performs a dry-run episodic prune check.

The canonical shard membership and ignore/deselect rules for
`run_pytest_sharded.sh` are now externalized in
`configs/quality/pytest_shards.yaml`. Update that inventory rather than editing
the shard plan inline in the shell runner.

Canonical test-health lane names live in
`configs/quality/test_matrix.yaml` under `test_lanes.lanes`. Developer wrapper
commands such as `run-tests unit`, `run-tests arch`, and `test-changed` are
local convenience aliases; do not treat those command names as comparable
CI/local telemetry suites unless the command explicitly records a canonical
`suite_name`.

For architecture-focused local runs, prefer the explicit aliases:

- `S7-architecture-fast-boundary`
- `S7-architecture-slow-governance`

For a deterministic parallel-safe unit wave, prefer the canonical QA lane
instead of ad hoc shard lists:

```bash
python -m scripts.engineering.qa run-tests --suite unit-parallel-safe --skip-preflight -- --no-cov
```

## Integration And E2E Quick Paths

For the tracked integration/VCR execution policy, prefer explicit replay for
normal local runs and targeted `new_episodes` only when intentionally
refreshing cassettes.

```powershell
# Windows PowerShell replay
.\scripts\engineering\dev\run_pytest.ps1 tests\integration\ --vcr-record=none -m "integration and not e2e"
.\scripts\engineering\dev\run_pytest.ps1 tests\e2e\ -m e2e --vcr-record=none

# Windows targeted cassette refresh
.\scripts\engineering\dev\run_pytest.ps1 tests\integration\adapters\test_pubmed.py --vcr-record=new_episodes -v
```

```bash
# WSL/Linux replay
bash scripts/engineering/dev/run_pytest.sh tests/integration/ --vcr-record=none -m "integration and not e2e"
bash scripts/engineering/dev/run_pytest.sh tests/e2e/ -m e2e --vcr-record=none

# WSL/Linux targeted cassette refresh
bash scripts/engineering/dev/run_pytest.sh tests/integration/adapters/test_pubmed.py --vcr-record=new_episodes -v
```

See `docs/03-guides/testing.md` and
`configs/quality/integration_vcr_policy.yaml` for the canonical policy scope,
supported test families, cassette lifecycle, and CI/live-contract split.

If you need MkDocs/site tooling, install the separate docs toolchain extra:

```bash
uv sync --extra dev --extra tracing --extra docs
# or, without uv:
pip install -e ".[dev,tracing,docs]"
```

## Unified Entry Point

```bash
python -m scripts.engineering.dev --help
python -m scripts.engineering.dev <command> [args...]
```

## Commands

| Command              | Script                                                       | Description                                                      |
| -------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------- |
| `setup`              | hard-fail guidance in `python -m scripts.engineering.dev`    | Legacy compatibility command; points users to maintained setup paths |
| `setup --quick`      | hard-fail guidance in `python -m scripts.engineering.dev`    | Legacy compatibility command; no shell bootstrap remains         |
| `setup --ci`         | hard-fail guidance in `python -m scripts.engineering.dev`    | Legacy compatibility command; CI should use maintained repo commands |
| `install-deps`       | `scripts/engineering/dev/install_deps.py`                    | Auxiliary helper script, not a full project bootstrap            |
| `probe-quality`      | `scripts/engineering/dev/quality_gate_probe.py`              | Measure narrow pytest/mypy startup latency and timeout behavior  |
| `pretest-guardrails` | `scripts/engineering/dev/pretest_guardrails.sh`              | Run cleanup + repo/docs/memory/architecture preflight            |
| `run-tests`          | `scripts/engineering/dev/run_tests.py`                       | Run tests                                                        |
| `pytest-sharded`     | `scripts/engineering/dev/run_pytest_sharded.sh`              | Run the recommended path-based pytest shards                     |
| `mock-metrics`       | `scripts/engineering/dev/metrics_mock_server.py`             | Start mock metrics server                                        |
| `mock-quarantine`    | `scripts/engineering/dev/quarantine_explorer_mock_server.py` | Start mock quarantine explorer API server                        |
| `test-changed`       | `scripts/engineering/dev/run_tests.py changed`               | Run tests for changed files only                                 |
| `setup-mcp`          | `python -m scripts.ai.codex.setup_mcp`                       | Public dev-router command for canonical Codex MCP/workspace setup |

## When to Use

| Command              | When                                                                                                                         | Trigger                                                |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `setup`              | Legacy compatibility entrypoint only; expect a hard-fail message that points to `make install` or `setup-mcp`               | Manual, only if intentionally verifying the retired command |
| `setup --quick`      | Legacy compatibility entrypoint only; expect the same hard-fail guidance as `setup`                                          | Manual, exceptional use only                           |
| `setup --ci`         | Legacy compatibility entrypoint only; expect the same hard-fail guidance as `setup`; CI should use maintained repo commands | CI migration/legacy compatibility only                 |
| `install-deps`       | Specialized helper for one auxiliary package; not for normal repo setup                                                      | Manual, rare maintenance task                          |
| `pretest-guardrails` | Before broad bash pytest runs when you want drift/governance/memory issues caught up front                                   | Manual, or auto-triggered by bash pytest runners       |
| `run-tests`          | Local test execution; supports modes: `all`, `unit`, `arch`, `integration`, `contract`, `smoke`, `security`, `memory`, `cov` | Manual, during development                             |
| `pytest-sharded`     | Faster local feedback for the large pytest suite by running stable path-based shards through the maintained wrapper          | Manual, during development                             |
| `mock-metrics`       | When developing or testing Grafana dashboards locally; starts Prometheus mock server with sample data                        | Manual, during dashboard development                   |
| `mock-quarantine`    | When validating `5. Silver Reject Explorer` against `/ops/quarantine/*` without real Delta data                              | Manual, during dashboard/API smoke checks              |
| `test-changed`       | Quick feedback during development; canonical changed-file runner with fast unit fallback                                     | Manual, during development                             |
| `setup-mcp`          | One-time AI tooling setup through the public dev router; synchronizes tracked workspace MCP settings plus Codex runtime config | Manual, initial setup                                  |

## Other Files

| File                                                         | Description                                                                               |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `scripts/engineering/dev/run_tests.sh`                       | Run tests (shell variant)                                                                 |
| `scripts/engineering/dev/run_tests.ps1`                      | Run tests (PowerShell variant)                                                            |
| `scripts/engineering/dev/run_mypy.sh`                        | Run mypy with local-environment fallbacks (shell variant)                                 |
| `scripts/engineering/dev/run_mypy.ps1`                       | Run mypy with local-environment fallbacks (PowerShell variant)                            |
| `scripts/engineering/dev/pretest_guardrails.sh`              | Run cleanup + repo/docs/memory/architecture preflight before broad bash pytest runs       |
| `scripts/engineering/dev/run_pytest.sh`                      | Run pytest directly                                                                       |
| `scripts/engineering/dev/run_pytest.ps1`                     | Run pytest directly (PowerShell variant)                                                  |
| `scripts/engineering/dev/run_pytest_sharded.sh`              | Run the recommended path-based pytest shard plan (shell variant)                          |
| `scripts/engineering/dev/quality_gate_probe.py`              | Diagnose narrow pytest/mypy startup latency and timeout behavior                          |
| `scripts/engineering/dev/quarantine_explorer_mock_server.py` | Start mock `/ops/quarantine/*` endpoints for Silver Reject Explorer smoke checks          |
| `scripts/engineering/dev/setup_env_windows.ps1`              | Create/update the stable Windows virtualenv at `.venv-win`                                |
| `scripts/engineering/dev/setup_env_wsl.sh`                   | Create/update the stable WSL virtualenv outside the repo (default: `$HOME/.venvs/bioetl`) |
| `scripts/engineering/dev/.wsl-vpn-fix.ps1`                   | Recover Windows-side VPN proxy settings for WSL interoperability                          |
| `scripts/engineering/dev/.setup_wsl_codex.sh`                | WSL/Codex DNS and connectivity bootstrap helper for the documented WSL setup flow         |
