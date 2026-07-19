# Zed Editor Configuration for BioETL Project

This directory contains Zed editor configuration for the BioETL project.

## Setup Instructions

### 1. Python Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install project with dev dependencies
pip install -e ".[dev]"
```

### 2. Zed Configuration

The configuration file in this directory should be automatically recognized by Zed:

- `settings.json` - Main Zed configuration for the project
- `tasks.json` - Worktree-specific Zed task definitions
- `README.md` - This file

**Note**: Zed automatically detects `.zed/settings.json` and `.zed/tasks.json`
in the project root.

### 3. LSP Servers

Zed uses built-in LSP servers (no extra installation required):

1. **basedpyright** (Primary) - Type checking and navigation (Zed default)
2. **ruff** (Built-in) - Formatting and linting (Zed default)

The configuration explicitly disables `pylsp` to avoid conflicts.

### 4. Available Tasks

Zed tasks are configured for common operations (access via Command Palette → Tasks):

- **Format code** - `ruff format .`
- **Lint code** - `ruff check .`
- **Type check** - `mypy src/`
- **Run unit tests** - `pytest tests/unit/ -v`
- **Run integration tests** - `pytest tests/integration/ -v`
- **Run architecture tests** - `pytest tests/architecture/ -v`
- **Run E2E smoke tests** - `pytest -m e2e_smoke -v`
- **Security scan** - `bandit -r src/`
- **Coverage report** - `pytest --cov=src/bioetl --cov-report=html`
- **Architecture compliance** - `import-linter --config .importlinter`
- **Run all tests** - `pytest -v -m "not benchmark and not slow"`
- **Run fast tests only** - `pytest -v -m unit`
- **Dependency audit** - `pip-audit`
- **Dead code detection** - `vulture src/bioetl`
- **Complexity check** - `xenon --max-absolute B --max-modules B --max-average A src/bioetl`

### 5. Project Structure Navigation

Key directories to add to Zed favorites:

- `src/bioetl/` - Main source code
- `tests/` - Test suite
- `docs/` - Documentation
- `configs/` - Pipeline configurations
- `scripts/` - Utility scripts

### 6. Architecture Layers

The project follows a layered architecture:

- `domain/` - Business logic and entities
- `application/` - Application services
- `infrastructure/` - External integrations
- `interfaces/` - Port definitions
- `composition/` - Dependency injection

### 7. Formatting and Linting

- **Line length**: 88 characters (soft), 120 characters (hard limit)
- **Formatter**: Ruff (replaces Black + isort)
- **Linter**: Ruff + MyPy (strict mode)
- **Type checking**: MyPy with strict mode enabled
- **Format on save**: Enabled in Zed configuration
- **Autosave**: Enabled with 1-second delay
- **Telemetry**: Disabled for privacy

### 8. Editor Configuration

- **Font**: JetBrains Mono (14pt)
- **Line height**: Comfortable
- **Tab size**: 4 spaces (Python)
- **Soft wrap**: At 88 characters
- **Language-specific settings**:
  - Python: Format on save, Ruff formatter, basedpyright type checking
  - YAML: Format on save
  - JSON: Format on save
  - Markdown: No format on save, soft wrap enabled

### 9. Testing

Test markers used in the project:

- `unit` - Fast unit tests (no I/O)
- `integration` - Integration tests (may use I/O)
- `e2e` - End-to-end tests (slow, local-only)
- `e2e_smoke` - PR-blocking E2E smoke subset
- `architecture` - Architecture compliance tests
- `contract` - Contract tests (API compatibility)
- `security` - Security tests
- `vcr` - VCR.py recorded HTTP interactions

### 10. Snippets

**Note**: Zed does not automatically load snippets from `.zed/snippets.json`. 

BioETL provides custom snippet files in `.zed/snippets/`:

- `python.json` - Python-specific snippets for BioETL patterns
- `yaml.json` - YAML configuration snippets for pipelines and providers

To use these snippets in Zed:
1. Open Zed settings (Ctrl+,)
2. Navigate to the Snippets section
3. Copy the contents from `.zed/snippets/python.json` to the Python snippets section
4. Copy the contents from `.zed/snippets/yaml.json` to the YAML snippets section
5. Save the settings

Available Python snippet prefixes:
- `bioetl-pipeline` - Import BioETL pipeline components
- `bioetl-schema` - Import BioETL domain schema
- `bioetl-logger` - Import and setup BioETL structured logger
- `bioetl-context` - Bind pipeline context for structured logging
- `bioetl-pandera` - Create a Pandera DataFrameModel schema
- `bioetl-test-fixture` - Create a BioETL test fixture
- `bioetl-test` - Create a BioETL unit test
- `bioetl-integration-test` - Create a BioETL integration test
- `bioetl-arch-test` - Create a BioETL architecture compliance test
- `bioetl-pydantic` - Create a BioETL Pydantic model
- `bioetl-settings` - Create BioETL settings with Pydantic Settings
- `bioetl-error` - Create BioETL error handling with structured logging
- `bioetl-stage` - Create a BioETL pipeline stage with logging
- `bioetl-contract` - Create a BioETL data contract validation
- `bioetl-medallion` - Create a BioETL medallion layer transformation

Available YAML snippet prefixes:
- `bioetl-pipeline-config` - Create a BioETL pipeline configuration
- `bioetl-dq-rules` - Create BioETL data quality rules configuration
- `bioetl-provider-config` - Create a BioETL provider configuration
- `bioetl-schema-mapping` - Create a BioETL schema mapping configuration
- `bioetl-medallion-config` - Create a BioETL medallion architecture configuration
- `bioetl-observability-config` - Create a BioETL observability configuration
- `bioetl-test-config` - Create a BioETL test configuration

### 11. Troubleshooting

#### LSP not working
- Ensure virtual environment is activated
- Zed automatically detects `.venv` via toolchain selector
- Check that `basedpyright` and `ruff` are enabled in settings

#### Tasks not showing
- Reload Zed workspace (Ctrl+Shift+R)
- Check that `.zed/tasks.json` is in project root
- Verify task syntax is correct (flat array, not nested)

#### Formatting not working
- Ensure Ruff is installed: `pip list | grep ruff`
- Check that format-on-save is enabled
- Verify Python language server is set to use Ruff

#### Type checking issues
- MyPy is configured in `pyproject.toml` with strict mode
- Run type check manually via task: "Type check"
- Check mypy overrides for external libraries

#### Environment variables
- `PYTHONPATH` is automatically set to `src;.` in terminal
- `PYTHONDONTWRITEBYTECODE=1` prevents .pyc file generation
- Ensure `.env` files are not committed (see RULES.md)

### 12. MCP (Model Context Protocol) Integration

BioETL keeps the shared MCP manifest in `.mcp.json`, generated by
`scripts/ai/codex/setup_mcp.py`. Zed's native Agent Panel reads MCP servers from
the `context_servers` setting in `.zed/settings.json`, so the project-level Zed
settings include only non-secret context servers.

#### Project Zed Context Servers
- **memory** - Persistent project memory
- **filesystem** - Workspace file system access
- **fetch** - HTTP fetch support
- **deepwiki** - Repository documentation

Secret-bearing or machine-local servers such as GitHub, Brave Search, Grafana,
Prometheus, Neo4j, and Docker should be configured in the user's Zed settings
or via Settings -> AI -> MCP Servers, not committed in project settings.

#### MCP Configuration Management
- **Source of truth**: `scripts/ai/codex/setup_mcp.py`
- **Shared generated files**: `.mcp.json`, `.vscode/mcp.json`,
  `.cursor/mcp.json`, `.qodo/mcp.json`, `.zed/mcp.json`
- **Zed Agent Panel runtime**: `.zed/settings.json` `context_servers`
- **Update process**: Run `py scripts/ai/codex/setup_mcp.py --skip-codex --skip-gemini-settings`
- **Governance**: See `docs/00-project/ai/mcp-governance.md`

#### MCP Usage in Zed
- Open Settings -> AI -> MCP Servers to check server status.
- Green server status means the server is active and available to Agent Panel.
- Project profile `BioETL Write` enables configured context servers.
- Project profile `BioETL Ask` keeps MCP disabled for read-only questions.

#### MCP Troubleshooting
- **MCP servers not starting**: Ensure Node.js, Python, and `uvx` are installed
- **Cache issues**: Clear `.cache/` directory and retry setup
- **Secret-backed servers**: Configure credentials in user settings, not here
- **Generated mirrors stale**: Run the "Refresh MCP config" Zed task

### 13. Running AI Agents

#### Zed Built-in Agent
Zed has a built-in AI agent in Agent Panel:
- Access via Agent Panel (Ctrl+Shift+A)
- Select `BioETL Ask` for read-only work
- Select `BioETL Write` for edits, terminal commands, and MCP tools
- Tool actions require confirmation by default
- Project settings set `vim_mode` to `false` so the Agent Panel input stays editable in this workspace

Model provider, account authentication, and External Agent definitions remain in
the user's Zed settings. Open `agent: open settings` if Zed Agent cannot send a
message because no model is selected or the provider is not authenticated.

#### Terminal Threads
Run CLI-based agents in Zed's Agent Panel:
1. Open Agent Panel -> `+` -> "New Thread" -> "Terminal"
2. Run a CLI agent such as `codex`
3. Terminal appears as a managed thread in the sidebar

#### BioETL Project Agents
BioETL uses Codex runtime for project-specific agents:
```bash
# Check Codex CLI
codex --version

# Run specific BioETL agents
codex agent run py-audit-bot
codex agent run py-test-bot
codex agent run py-doc-bot
```

#### Agent Profiles
Project profiles are stored under `agent.profiles` in `.zed/settings.json`:
- `BioETL Ask` - read/search/fetch only, no edits or terminal
- `BioETL Write` - edit/terminal/MCP enabled with full permissions

**Tool Permissions Configuration:**
- **Default**: `allow` (changed from `confirm` for better workflow)
- **Security**: Protected paths always denied (.env, secrets/, .git, .pem, .key files)
- **Dangerous commands**: Always denied (rm -rf /, sudo rm)
- **Git push**: Always requires confirmation
- **Sudo commands**: Always requires confirmation

**To switch profiles:**
- Agent Panel → Profile selector → Choose profile
- Or set default profile in settings

### 14. Zed Tasks for BioETL

Zed tasks are configured for common BioETL operations (access via Command Palette → Tasks):

**Code Quality:**
- **Format code** - `ruff format .`
- **Lint code** - `ruff check .`
- **Type check** - `mypy src/`
- **Refresh MCP config** - Regenerate MCP configuration

**Testing:**
- **Run unit tests** - `pytest tests/unit/ -v`
- **Run integration tests** - `pytest tests/integration/ -v`
- **Run architecture tests** - `pytest tests/architecture/ -v`
- **Run E2E smoke tests** - `pytest -m e2e_smoke -v`
- **Run all tests** - `pytest -v -m "not benchmark and not slow"`
- **Run fast tests only** - `pytest -v -m unit`
- **Coverage report** - `pytest --cov=src/bioetl --cov-report=html`

**Security & Quality:**
- **Security scan** - `bandit -r src/`
- **Dependency audit** - `pip-audit`
- **Dead code detection** - `vulture src/bioetl`
- **Complexity check** - `xenon --max-absolute B --max-modules B --max-average A src/bioetl`
- **Architecture compliance** - `import-linter --config .importlinter`

**BioETL Agents (via Codex):**
- **Run py-audit-bot** - Code/architecture audit
- **Run py-test-bot** - Test execution and coverage
- **Run py-doc-bot** - Documentation and ADR updates
- **Run py-config-bot** - YAML configuration management
- **Run py-debug-bot** - Debugging and RCA

**BioETL Skills (via Devin):**
- **Invoke grafana-dashboard-render** - Dashboard screenshot rendering
- **Invoke py-test-swarm** - Hierarchical test campaigns
- **Invoke documentation-audit** - Full documentation audit

### 15. Zed Authentication

#### Sign In Process
Zed authentication is **optional** for most features. Sign-in is only required for:
- Real-time collaboration features
- LLM-powered features when using Zed as the provider
- Zed Pro features

BioETL project settings show the Sign In button so Zed-hosted models can be
configured from the Agent Panel:
```json
{
  "show_sign_in": true
}
```

To sign in for Zed-hosted models, click the button or run `client: sign in`
from Command Palette (Ctrl+Shift+P).

**Requirements:**
- GitHub account (Zed uses GitHub OAuth)
- Only `read:user` GitHub scope required (read-only profile access)

#### Alternative: Use Your Own API Keys
If you need AI features but don't want to sign in:
1. Open Settings → AI
2. Choose a different provider (OpenAI, Anthropic, etc.)
3. Add your own API keys
4. Use AI features without Zed sign-in

#### Troubleshooting Sign In Issues
- **Network issues**: Check your DNS/firewall settings
- **GitHub username conflicts**: If your GitHub username was previously used by a deleted account, contact Zed support
- **Browser issues**: Try incognito/private mode
- **Proxy issues**: Configure proxy settings if needed

## Additional Resources

- Project documentation: `docs/`
- Architecture decisions: `docs/02-architecture/decisions/`
- Rules and requirements: `docs/00-project/RULES.md`
- Testing standards: `docs/styleguide/05-testing-standards.md`
- Zed documentation: https://zed.dev/docs/
