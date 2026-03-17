# scripts/dev — Developer Workflows

Local developer setup and test utilities.

## Unified Entry Point

```bash
python -m scripts.dev --help
python -m scripts.dev <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `setup` | `dev_setup.sh` | Full developer environment setup (shell) |
| `setup --quick` | `dev_setup.sh` | Fast setup, skip tests/linters (shell) |
| `setup --ci` | `dev_setup.sh` | CI mode, non-interactive (shell) |
| `install-deps` | `install_deps.py` | Install project dependencies |
| `run-tests` | `run_tests.py` | Run tests |
| `mock-metrics` | `metrics_mock_server.py` | Start mock metrics server |
| `test-changed` | `test_changed.sh` | Run tests for changed files only (shell) |
| `setup-mcp` | `setup_copilot_codex_mcp.py` | Setup Copilot/Codex MCP integration |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `setup` | First time cloning the repo or after major dependency changes; installs everything, runs linters and tests | Manual, initial onboarding |
| `setup --quick` | Quick re-setup after minor changes; skips tests and linters | Manual, fast iteration |
| `setup --ci` | CI pipeline environment setup; non-interactive mode | CI pipeline (automatic) |
| `install-deps` | After modifying `pyproject.toml` or when dependencies are out of date | Manual, after dependency changes |
| `run-tests` | Local test execution; supports modes: `all`, `unit`, `arch`, `integration`, `contract`, `smoke`, `security`, `cov` | Manual, during development |
| `mock-metrics` | When developing or testing Grafana dashboards locally; starts Prometheus mock server with sample data | Manual, during dashboard development |
| `test-changed` | Quick feedback during development; runs tests only for files changed since last commit | Manual, during development |
| `setup-mcp` | One-time AI tooling setup; configures Copilot/Codex MCP integration | Manual, initial setup |

## Other Files

| File | Description |
|------|-------------|
| `run_tests.sh` | Run tests (shell variant) |
| `run_tests.ps1` | Run tests (PowerShell variant) |
| `run_pytest.sh` | Run pytest directly |
| `run_pytest.ps1` | Run pytest directly (PowerShell variant) |
| `setup_copilot_codex_mcp.sh` | Setup MCP (shell variant) |
| `setup_copilot_codex_mcp.ps1` | Setup MCP (PowerShell variant) |
