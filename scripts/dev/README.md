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

## Unified Entry Point

```bash
python -m scripts.dev --help
python -m scripts.dev <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `setup` | `dev_setup.sh` | Legacy shell facade; currently not the supported onboarding path |
| `setup --quick` | `dev_setup.sh` | Legacy placeholder mode; not recommended for current setup |
| `setup --ci` | `dev_setup.sh` | Legacy placeholder mode; not recommended for current setup |
| `install-deps` | `install_deps.py` | Auxiliary helper script, not a full project bootstrap |
| `run-tests` | `run_tests.py` | Run tests |
| `mock-metrics` | `metrics_mock_server.py` | Start mock metrics server |
| `test-changed` | `test_changed.sh` | Run tests for changed files only (shell) |
| `setup-mcp` | `setup_copilot_codex_mcp.py` | Setup Copilot/Codex MCP integration |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `setup` | Legacy compatibility entrypoint only; use `make install` instead | Manual, only if intentionally testing the shell facade |
| `setup --quick` | Legacy compatibility entrypoint only; use `make install` + targeted verify commands instead | Manual, exceptional use only |
| `setup --ci` | Legacy compatibility entrypoint only; CI should use the maintained repo commands | CI migration/legacy compatibility only |
| `install-deps` | Specialized helper for one auxiliary package; not for normal repo setup | Manual, rare maintenance task |
| `run-tests` | Local test execution; supports modes: `all`, `unit`, `arch`, `integration`, `contract`, `smoke`, `security`, `cov` | Manual, during development |
| `mock-metrics` | When developing or testing Grafana dashboards locally; starts Prometheus mock server with sample data | Manual, during dashboard development |
| `test-changed` | Quick feedback during development; runs tests only for files changed since last commit | Manual, during development |
| `setup-mcp` | One-time AI tooling setup; configures Copilot/Codex MCP integration | Manual, initial setup |

## Other Files

| File | Description |
|------|-------------|
| `run_tests.sh` | Run tests (shell variant) |
| `run_tests.ps1` | Run tests (PowerShell variant) |
| `run_mypy.sh` | Run mypy with local-environment fallbacks (shell variant) |
| `run_mypy.ps1` | Run mypy with local-environment fallbacks (PowerShell variant) |
| `run_pytest.sh` | Run pytest directly |
| `run_pytest.ps1` | Run pytest directly (PowerShell variant) |
| `setup_copilot_codex_mcp.sh` | Setup MCP (shell variant) |
| `setup_copilot_codex_mcp.ps1` | Setup MCP (PowerShell variant) |
