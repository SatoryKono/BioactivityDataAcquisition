# BioETL Codex runtime

Единая точка входа для project-scoped Codex runtime в BioETL. Команды
выполняются из корня репозитория; Windows transport делегирует в canonical
WSL/Bash launcher.

## Fresh checkout

После того как checkout отмечен trusted в Codex, project runtime обнаруживается
без копирования файлов в пользовательский home:

- `.codex/config.toml` — portable project policy;
- `.codex/agents/py-*.toml` — шесть native custom-agent descriptors;
- `.codex/agents/py-*.md` — подробные behavioral profiles;
- `.codex/skills/**` — единственная project-local skill discovery и canonical
  behavior surface.

Статическая проверка не требует login, сети, Docker или live MCP:

```bash
python3 scripts/ai/codex/doctor.py static --no-write
bash scripts/ai/codex/setup_agents.sh --check
bash scripts/ai/codex/setup_skills.sh --check
```

`setup_agents.sh` и `setup_skills.sh` больше не являются обязательным
bootstrap. Их `--install-personal` режим остаётся явной compatibility-опцией и
не перезаписывает существующие personal entries.

### Concurrency compatibility

Tracked project policy сохраняет `agents.max_threads = 3`. В актуальном
[Codex Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)
это legacy alias для `agents.max_concurrent_threads_per_session`; оба ключа
задают максимальное число одновременно открытых spawned-agent threads без
primary thread. Переход на другое имя ключа или значение требует versioned CLI
check и отдельного concurrency benchmark. Последняя локальная проверка
выполнена на Codex CLI `0.147.0`.

Legacy alias из tracked config и canonical key можно проверить без изменения
user config, скопировав project policy в изолированный temporary `CODEX_HOME`:

```bash
issue8219_project_home=$(mktemp -d /tmp/bioetl-codex-project.XXXXXX)
issue8219_canonical_home=$(mktemp -d /tmp/bioetl-codex-canonical.XXXXXX)
cp .codex/config.toml "$issue8219_project_home/config.toml"

CODEX_HOME="$issue8219_project_home" codex doctor --json 2>/dev/null \
  | jq '{
      codexVersion,
      configLoad: .checks["config.load"].status,
      configParse: .checks["config.load"].details["config.toml parse"]
    }'
CODEX_HOME="$issue8219_canonical_home" codex doctor \
  -c agents.max_concurrent_threads_per_session=3 --json 2>/dev/null \
  | jq '{codexVersion, configLoad: .checks["config.load"].status}'
```

Ожидаемый результат для обеих форм — `configLoad: "ok"`; для скопированного
tracked config также `configParse: "ok"`. Общий `codex doctor` в таком
изолированном home может завершиться ненулевым кодом из-за отсутствующих auth,
network или TTY checks; это не является ошибкой разбора concurrency config.

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

# After setup, the managed PATH command uses the same launcher
codex

# MCP: static configuration versus bounded live readiness
bash scripts/ai/codex/run-codex.sh mcp-static
bash scripts/ai/codex/run-codex.sh mcp-check --profile stable \
  --timeout 1 --overall-timeout 10 --no-write
bash scripts/ai/codex/run-codex.sh mcp-setup

# Diagnostics and performance evidence
bash scripts/ai/codex/run-codex.sh diagnose
bash scripts/ai/codex/run-codex.sh baseline --runs 3 \
  --output reports/quality/codex-efficiency-baseline.json
bash scripts/ai/codex/run-codex.sh local-audit \
  --output reports/quality/codex-local-state-audit.json
```

`setup` installs a managed, secret-free command shim at
`~/.local/bin/codex`. The shim preserves native Codex CLI arguments and uses
the same focused launcher helper that loads only `REF_TOOL_API_KEY` from the
repository `.env` into the Codex parent process. Before direct execution, the
shim also runs the canonical MCP ensure path so a persisted shared-transport
profile is reconciled after a WSL or host restart. Set `CODEX_SKIP_MCP_SETUP=1`
only for an explicit config-free launch. An existing non-BioETL command at that
path is never overwritten. Restart an already running Codex process after
adding or rotating the Ref key.

`local-audit` reports only aggregate counts: unsafe mode categories, approval
rule dispositions, retention classes, SQLite integrity/index counts, and PATH
selection. It never emits rule/session bodies, credentials, or user paths.
Remediation is a separate explicit command in `local_state_audit.py`; it
requires `--apply` and a restricted backup directory under the local Codex
home. Retention remains dry-run and performs no archive/delete operation.

### Model profiles and benchmark

The reproducible benchmark uses five secret-free fixtures, ephemeral sessions,
a read-only sandbox, disabled plugins/apps, and a 60/40
correctness/validation rubric:

```bash
python3 scripts/ai/codex/profile_benchmark.py \
  --output reports/quality/codex-profile-benchmark.json
```

| Profile | Model / effort | Intended use |
| --- | --- | --- |
| `fast` | `gpt-5.6-luna` / `low` | navigation and low-risk iteration |
| `balanced` | `gpt-5.6-sol` / `high` | default focused implementation and review |
| `deep` | `gpt-5.6-sol` / `max` | V4 architecture and difficult diagnosis |

Quality equivalence uses a versioned five-point non-inferiority margin. The
selector compares quality first, then median wall time, then the billable-token
proxy. `fast` is always explicit opt-in, and the benchmark never changes
`agents.max_threads = 3`.

Machine-local application is separate from measurement. The following command
audits only allowlisted model fields. `apply` requires an explicit private
backup below the local Codex backup directory; `restore` verifies checksums.
Neither operation reads or modifies `.env` files.

```bash
python3 scripts/ai/codex/profile_config.py audit
python3 scripts/ai/codex/profile_config.py apply --confirm \
  --backup-dir ~/.codex/backups/profile-YYYYMMDD
python3 scripts/ai/codex/profile_config.py restore --confirm \
  --backup-dir ~/.codex/backups/profile-YYYYMMDD
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
| `stable` | daily required local set plus Ref; no credentialed DeepWiki |
| `shared` | `stable` required; DeepWiki and heavy additions optional |
| `core` | `stable` plus Mermaid required |
| `ops` | `stable` plus Prometheus, Grafana, GitHub Actions required |
| `graph` | `stable` plus Neo4j Cypher/Memory required |
| `full` | complete explicitly selected inventory required |

`mcp-check` prints `FAIL` for unavailable required servers, `WARN` for optional
servers, and `SKIP` for remote/auth-managed endpoints. Every network probe has
a per-server and overall timeout. It never starts Docker Compose or the
monitoring stack and is read-only by default. Persist evidence only by passing
an explicit `.json` path under `reports/quality`, for example
`--output reports/quality/codex-mcp-health.json`. Static CI uses:

```bash
python3 scripts/ai/codex/mcp_profile_contract.py --check
python3 scripts/ai/codex/doctor.py static --no-write
python3 scripts/ai/codex/setup_mcp.py --check
python3 scripts/ai/codex/setup_mcp.py --check-local
```

`setup_mcp.py --check` validates the full tracked portable/Devin inventory;
`--check-local` validates generated local surfaces against the persisted
profile without starting services. The daily recovery sequence is:

```bash
python3 scripts/ai/codex/setup_mcp.py \
  --profile stable --transport-mode shared \
  --persist-local-profile --skip-codex-validation
bash scripts/ai/codex/run-codex.sh mcp-setup
# Restart MCP clients that were already running.
bash scripts/ai/codex/run-codex.sh mcp-static
bash scripts/ai/codex/run-codex.sh mcp-check --profile stable \
  --timeout 1 --overall-timeout 10 --no-write
```

The shared-plane start is bounded by `CODEX_MCP_SHARED_START_TIMEOUT` inside
the MCP ensure helper; setup does not impose a smaller outer timeout.

## Runtime ownership

| Surface | Owner |
| --- | --- |
| `.codex/config.toml` | tracked portable trusted-project behavior |
| `.codex/agents/*.toml` | Codex-only native discovery metadata |
| `.codex/agents/*.md`, `.codex/skills/**` | canonical Codex discovery and behavior |
| `~/.codex/config.toml` | user-owned preferences and generated local MCP block |
| `.junie/**` | equal-peer Junie runtime under the mirror contract |
| `.devin/**` | Devin-owned runtime behavior and tracked projections |

После изменений runtime surfaces выполнить:

```bash
bash scripts/ai/codex/setup_skills.sh --check
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
