# scripts/dev — Developer Workflows

Local developer setup and test utilities.

## Canonical Bootstrap

For normal local onboarding, prefer the maintained project entrypoints:

```bash
make install
make test-deps
make setup-plugins
python -m scripts.dev setup-mcp  # optional MCP tooling
```

`dev_setup.sh` is still wired into `python -m scripts.dev setup`, but it is currently a legacy placeholder rather than the supported bootstrap path.

## Stable Dual-OS Environments

If you work from both Windows PowerShell and WSL against the same checkout, do
not share a single `.venv`. Use separate environment directories instead:

```text
.venv-win  # PowerShell / native Windows Python
$HOME/.venvs/bioetl  # WSL / Linux Python by default
```

Bootstrap commands:

```powershell
.\scripts\dev\setup_env_windows.ps1
```

```bash
bash scripts/dev/setup_env_wsl.sh
```

Preferred runners automatically select the OS-appropriate environment:

```powershell
.\scripts\dev\run_pytest.ps1 tests\unit --narrow --timeout=120 --lf
.\scripts\dev\run_mypy.ps1
```

```bash
bash scripts/dev/run_pytest.sh tests/unit --narrow --timeout=120 --lf
bash scripts/dev/run_mypy.sh
bash scripts/dev/run_pytest_sharded.sh
```

For fast, reproducible narrow slices during refactoring, use the explicit
`--narrow` mode:

```bash
bash scripts/dev/run_pytest.sh --narrow --collect-only tests/architecture/test_boundary_assertions.py
bash scripts/dev/run_pytest.sh --narrow tests/architecture/test_boundary_assertions.py
bash scripts/dev/run_mypy.sh --narrow --config-file pyproject.toml --strict src/bioetl/domain/__init__.py
python -m scripts.dev probe-quality --timeout 15
```

`--narrow` intentionally favors startup stability over full plugin/import graph
coverage:

- `run_pytest.* --narrow` disables plugin autoload and uses a minimal explicit
  plugin allowlist suitable for narrow architecture and unit slices
- `run_mypy.* --narrow` adds `--follow-imports=skip` so single-file strict
  probes do not walk the whole repository graph

`run_pytest.ps1` and `run_pytest.sh` both add default pytest flags unless you ask
for help/version. `--collect-only` automatically drops coverage defaults to keep
startup lightweight:

```text
--cov=src/bioetl --cov-report=term -q --maxfail=1
```

Behavior differs slightly by platform:

- `bash scripts/dev/run_pytest.sh` runs `bash scripts/ops/setup_plugins.sh --pytest-only`
  first, so missing pytest plugins can be auto-installed in the selected Python environment.
- `.\scripts\dev\run_pytest.ps1` assumes `.venv-win` is already prepared via
  `.\scripts\dev\setup_env_windows.ps1` or `make setup-plugins`.

## Integration And E2E Quick Paths

For the tracked integration/VCR execution policy, prefer explicit replay for
normal local runs and targeted `new_episodes` only when intentionally
refreshing cassettes.

```powershell
# Windows PowerShell replay
.\scripts\dev\run_pytest.ps1 tests\integration\ --vcr-record=none -m "integration and not e2e"
.\scripts\dev\run_pytest.ps1 tests\e2e\ -m e2e --vcr-record=none

# Windows targeted cassette refresh
.\scripts\dev\run_pytest.ps1 tests\integration\adapters\test_pubmed.py --vcr-record=new_episodes -v
```

```bash
# WSL/Linux replay
bash scripts/dev/run_pytest.sh tests/integration/ --vcr-record=none -m "integration and not e2e"
bash scripts/dev/run_pytest.sh tests/e2e/ -m e2e --vcr-record=none

# WSL/Linux targeted cassette refresh
bash scripts/dev/run_pytest.sh tests/integration/adapters/test_pubmed.py --vcr-record=new_episodes -v
```

See `docs/03-guides/testing.md` and
`configs/quality/integration_vcr_policy.yaml` for the canonical policy scope,
supported test families, cassette lifecycle, and CI/live-contract split.

If you need MkDocs commands such as `make docs-build` or `make docs-serve`,
install the separate docs toolchain extra:

```bash
uv sync --extra dev --extra tracing --extra docs
# or, without uv:
pip install -e ".[dev,tracing,docs]"
```

## Unified Entry Point

```bash
python -m scripts.dev --help
python -m scripts.dev <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `setup` | `scripts/dev/dev_setup.sh` | Legacy shell facade; currently not the supported onboarding path |
| `setup --quick` | `scripts/dev/dev_setup.sh` | Legacy placeholder mode; not recommended for current setup |
| `setup --ci` | `scripts/dev/dev_setup.sh` | Legacy placeholder mode; not recommended for current setup |
| `install-deps` | `scripts/dev/install_deps.py` | Auxiliary helper script, not a full project bootstrap |
| `probe-quality` | `scripts/dev/quality_gate_probe.py` | Measure narrow pytest/mypy startup latency and timeout behavior |
| `run-tests` | `scripts/dev/run_tests.py` | Run tests |
| `pytest-sharded` | `scripts/dev/run_pytest_sharded.sh` | Run the recommended path-based pytest shards |
| `mock-metrics` | `scripts/dev/metrics_mock_server.py` | Start mock metrics server |
| `test-changed` | `scripts/dev/run_tests.py changed` | Run tests for changed files only |
| `setup-mcp` | `scripts/dev/setup_copilot_codex_mcp.py` | Setup Copilot/Codex MCP integration |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `setup` | Legacy compatibility entrypoint only; use `make install` instead | Manual, only if intentionally testing the shell facade |
| `setup --quick` | Legacy compatibility entrypoint only; use `make install` + targeted verify commands instead | Manual, exceptional use only |
| `setup --ci` | Legacy compatibility entrypoint only; CI should use the maintained repo commands | CI migration/legacy compatibility only |
| `install-deps` | Specialized helper for one auxiliary package; not for normal repo setup | Manual, rare maintenance task |
| `run-tests` | Local test execution; supports modes: `all`, `unit`, `arch`, `integration`, `contract`, `smoke`, `security`, `cov` | Manual, during development |
| `pytest-sharded` | Faster local feedback for the large pytest suite by running stable path-based shards through the maintained wrapper | Manual, during development |
| `mock-metrics` | When developing or testing Grafana dashboards locally; starts Prometheus mock server with sample data | Manual, during dashboard development |
| `test-changed` | Quick feedback during development; canonical changed-file runner with fast unit fallback | Manual, during development |
| `setup-mcp` | One-time AI tooling setup; configures Copilot/Codex MCP integration | Manual, initial setup |

## Other Files

| File | Description |
|------|-------------|
| `scripts/dev/run_tests.sh` | Run tests (shell variant) |
| `scripts/dev/run_tests.ps1` | Run tests (PowerShell variant) |
| `scripts/dev/run_mypy.sh` | Run mypy with local-environment fallbacks (shell variant) |
| `scripts/dev/run_mypy.ps1` | Run mypy with local-environment fallbacks (PowerShell variant) |
| `scripts/dev/run_pytest.sh` | Run pytest directly |
| `scripts/dev/run_pytest.ps1` | Run pytest directly (PowerShell variant) |
| `scripts/dev/run_pytest_sharded.sh` | Run the recommended path-based pytest shard plan (shell variant) |
| `scripts/dev/quality_gate_probe.py` | Diagnose narrow pytest/mypy startup latency and timeout behavior |
| `scripts/dev/setup_copilot_codex_mcp.sh` | Setup MCP (shell variant) |
| `scripts/dev/setup_copilot_codex_mcp.ps1` | Setup MCP (PowerShell variant) |
| `scripts/dev/setup_env_windows.ps1` | Create/update the stable Windows virtualenv at `.venv-win` |
| `scripts/dev/setup_env_wsl.sh` | Create/update the stable WSL virtualenv outside the repo (default: `$HOME/.venvs/bioetl`) |
| `scripts/dev/.wsl-vpn-fix.ps1` | Recover Windows-side VPN proxy settings for WSL interoperability |
| `scripts/dev/.setup_wsl_codex.sh` | WSL/Codex DNS and connectivity bootstrap helper for the documented WSL setup flow |
