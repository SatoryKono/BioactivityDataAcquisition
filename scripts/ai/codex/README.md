# BioETL Codex runtime

Единая точка входа для project-scoped Codex runtime в BioETL. Команды
выполняются из корня репозитория; Windows transport делегирует в canonical
WSL/Bash launcher.

## Fresh checkout

После того как checkout отмечен trusted в Codex, project runtime обнаруживается
без копирования файлов в пользовательский home:

- `.codex/config.toml` — portable project policy;
- `.codex/agents/py-*.toml` — девять native custom-agent descriptors;
- `.codex/agents/py-*.md` — подробные behavioral profiles;
- `.codex/skills/**` — canonical skill behavior;
- `.agents/skills/**` — generated native discovery adapters.

Статическая проверка не требует login, сети, Docker или live MCP:

```bash
python3 scripts/ai/codex/doctor.py static --no-write
bash scripts/ai/codex/setup_agents.sh --check
bash scripts/ai/codex/setup_skills.sh --check
```

`setup_agents.sh` и `setup_skills.sh` больше не являются обязательным
bootstrap. Их `--install-personal` режим остаётся явной compatibility-опцией и
не перезаписывает существующие personal entries.

## Authentication

По решению владельца launcher authentication сохраняет текущий repository
contract. Existing machine-local `.env.codex` и login flow не изменяются этой
настройкой. Secret-bearing `.env` files нельзя создавать, менять, перемещать
или удалять без отдельного явного разрешения.

Поддерживаемые текущим launcher команды:

```bash
bash scripts/ai/codex/run-codex.sh login
bash scripts/ai/codex/run-codex.sh device-login
bash scripts/ai/codex/login-codex.sh
```

## Canonical launch modes

```bash
# Interactive
bash scripts/ai/codex/run-codex.sh
bash scripts/ai/codex/run-codex.sh "analyze the code"

# Auto-execute
bash scripts/ai/codex/run-codex.sh exec "fix the focused failure"

# Environment and setup
bash scripts/ai/codex/run-codex.sh check
bash scripts/ai/codex/run-codex.sh setup

# MCP: static configuration versus bounded live readiness
bash scripts/ai/codex/run-codex.sh mcp-static
bash scripts/ai/codex/run-codex.sh mcp-check --profile stable
bash scripts/ai/codex/run-codex.sh mcp-setup

# Diagnostics and performance evidence
bash scripts/ai/codex/run-codex.sh diagnose
bash scripts/ai/codex/run-codex.sh baseline --runs 3 \
  --output reports/quality/codex-efficiency-baseline.json
```

PowerShell uses the same behavior through
`scripts/ai/codex/run-codex.ps1`; CMD entrypoints live under `scripts/ops/`.

Maintained platform-specific helpers remain discoverable for their bounded
roles:

- `scripts/ai/codex/headless.ps1` — PowerShell transport for headless mode;
- `scripts/ai/codex/helper/diagnose-hang.ps1` — setup-hang diagnostics;
- `scripts/ai/codex/setup-windows-dns.ps1` — explicit Windows DNS repair;
- `scripts/ai/codex/setup-wsl-dns.sh` — explicit WSL DNS repair;
- `scripts/ops/install-codex-cmd.bat` — optional Windows CMD installation.

### Fast/headless

Headless mode intentionally skips the normal MCP synchronization path:

```bash
bash scripts/ai/codex/headless.sh exec "run a bounded task"
```

Use it only when the task does not need the repository MCP projection.

## MCP profiles and doctor

Tracked MCP manifests retain the full portable inventory. Local projection and
readiness use a selected profile:

| Profile | Live gate |
| --- | --- |
| `stable` | daily required local set |
| `shared` | `stable` required; heavy additions optional |
| `core` | `stable` plus Mermaid required |
| `ops` | `stable` plus Prometheus, Grafana, GitHub Actions required |
| `graph` | `stable` plus Neo4j Cypher/Memory required |
| `full` | complete explicitly selected inventory required |

`mcp-check` prints `FAIL` for unavailable required servers, `WARN` for optional
servers, and `SKIP` for remote/auth-managed endpoints. Every network probe has
a per-server and overall timeout. It never starts Docker Compose or the
monitoring stack. Static CI uses:

```bash
python3 scripts/ai/codex/mcp_profile_contract.py --check
python3 scripts/ai/codex/doctor.py static --no-write
python3 scripts/ai/codex/setup_mcp.py --check
```

## Runtime ownership

| Surface | Owner |
| --- | --- |
| `.codex/config.toml` | tracked portable trusted-project behavior |
| `.codex/agents/*.toml` | Codex-only native discovery metadata |
| `.codex/agents/*.md`, `.codex/skills/**` | canonical Codex behavior |
| `.agents/skills/**` | generated discovery projection |
| `~/.codex/config.toml` | user-owned preferences and generated local MCP block |
| `.junie/**` | equal-peer Junie runtime under the mirror contract |
| `.devin/**` | Devin-owned runtime behavior and tracked projections |

После изменений runtime surfaces выполнить:

```bash
python3 scripts/ai/codex/sync_native_skills.py --check
bash scripts/ai/junie/check_junie_mirror.sh --check
```

## Retired Root Shim Verification

Last verified: 2026-08-04 for root script hygiene issues #6152-#6158. This
retains the root hygiene issue #5994 decision: no Codex compatibility script is
restored at repository root.

Canonical owners remain:

- `scripts/ai/codex/run-codex.ps1` for PowerShell transport;
- `scripts/ops/codex.bat` for CMD transport;
- `scripts/ai/codex/setup-codex-wsl.bat` for Windows setup;
- `scripts/ai/codex/helper/setup-wsl-complete.sh` for Bash setup;
- `scripts/engineering/dev/bash/.wsl_proxy_env.sh` for shared proxy setup.

Any future root-script restoration requires an explicit owner decision plus
the root allowlist, hygiene registry, documentation, and surface tests in the
same change.

## Canonical references

- `AGENTS.md`
- `.codex/agents/CODEX-RUNTIME.md`
- `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`
- `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
