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

## Other Files

| File | Description |
|------|-------------|
| `run_tests.sh` | Run tests (shell variant) |
| `run_tests.ps1` | Run tests (PowerShell variant) |
| `run_pytest.sh` | Run pytest directly |
| `setup_copilot_codex_mcp.sh` | Setup MCP (shell variant) |
| `setup_copilot_codex_mcp.ps1` | Setup MCP (PowerShell variant) |
