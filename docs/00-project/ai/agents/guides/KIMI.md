# KIMI.md: Context & Instructions for BioETL (Kimi Code CLI)

*Статус: internal-published (Internal / Extended) | Проверено: 2026-09-27*

## 0. Canonical runtime entry

Read first, in this order:

1. `AGENTS.md`
1. `.codex/agents/CODEX-RUNTIME.md` and `.junie/agents/JUNIE-RUNTIME.md` (equal peers; plus `.junie/guidelines.md`)
1. `docs/00-project/NORMATIVE_SOURCES.md`

This guide is a navigation mirror. It does not override those contracts and
does not define new runtime behavior (see `policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`).
There is no tracked `.kimi-code/agents/**` or `.kimi-code/skills/**` tree on
`main`; Kimi sessions reuse the Codex canonical sources above. Kimi Code CLI
подхватывает корневой `AGENTS.md` автоматически — отдельный root-файл
(типа `KIMI.md` в корне) не создаётся: root-allowlist остаётся неизменным.

Kimi остаётся зеркальным рантаймом уровня Muse: runtime behavior SSOT —
`.codex/**` / `.junie/**`, а `.kimi-code/**` — machine-local поверхность
(аналог `.gemini/`, см. `policy/MCP_LOCAL_RUNTIME_CONFIG.md`).

## 1. Session guardrails

- **Response language:** by default answer in Russian when the user writes in
  Russian. GitHub review bodies and inline comments via `gh pr review` (or an
  equivalent API) MUST be written in Russian. Keep code, commands, paths,
  identifiers, and API field names in their original form.
- **Technical debt:** increasing debt budgets is FORBIDDEN
  (scorecards, exemptions, hotspot thresholds and family caps).
- **Local-only default:** do not introduce Docker, Redis, or external
  orchestration unless the task explicitly requires it (ADR-010).
- **Env files:** any `.env` / `.env.*` file is secret-bearing and
  machine-local. Do NOT create, edit, rename, move, overwrite, or delete it
  without explicit per-task user approval. Reading is permitted.
- **Secrets:** never commit credentials to tracked YAML, docs, tests, or logs.
  Runtime config carries secret *names* only (env var names); values are
  supplied by the user locally.
- **Task classes:** follow the `AGENTS.md` context-tier table (hash-only
  rebind skips RULES/ADR with `BIOETL_AI_MEMORY_MODE=off`; V2 loads one
  matching role/skill; V3/V4 keep the full package with `pre-task`).
- **Root hygiene:** do not create root-level scratch files; prefer
  `scripts/**` or `reports/**`.

## 2. Конфигурация Kimi Code

Kimi Code CLI хранит настройки в TOML/JSON вне репозитория:

- **User-level:** `~/.kimi-code/config.toml` (runtime settings) и
  `tui.toml` (TUI preferences); каталог переопределяется `KIMI_CODE_HOME`.
  Содержит `default_model`, `[providers]` с `api_key_env` / `api_key`,
  `default_permission_mode` (`manual` — дневной дефолт; `yolo`/`auto` —
  только по явному решению оператора), `[[permission.rules]]`, `[hooks]`,
  `[identity]`. Провайдер-ключ читается из env-переменной через
  `api_key_env` (например, `KIMI_API_KEY`); значение ключа в репозиторий не
  коммитится.
- **Project-local:** `.kimi-code/local.toml` — только `[workspace]`
  (`additional_dir`), пишется автоматически (`/add-dir`), gated доверием
  workspace. Machine-local, в `.gitignore`.
- **В репозитории tracked-поверхностей Kimi нет.** `.kimi-code/**`
  gitignored целиком (как `.gemini/`); локальные файлы могут содержать
  machine-local absolute paths.

## 3. Skills

`.codex/skills/` is the canonical project skill source (see
`.codex/skills/SKILLS-CATALOG.md`). Do NOT duplicate skills under
`.kimi-code/skills/`. Подключение — по аналогии с Muse, без копирования:

1. Рекомендуется: `extra_skill_dirs = ["/absolute/path/to/repo/.codex/skills"]`
   в user-level `~/.kimi-code/config.toml` (абсолютный machine-local путь).
1. Альтернатива: установить отдельные навыки в `~/.kimi-code/skills/` и
   использовать только под задачу (как `muse skills install` для Muse).

Перед массовым подключением проверить совместимость frontmatter одного
`SKILL.md` (`name`, `description` обязательны в directory-form). Слот
`.agents/skills/` в репозитории — зарезервированный SSOT, остаётся пустым;
Kimi сканирует его как project-level skills dir, поэтому пустота важна и для
Kimi. External skills (CodeRabbit/Qodo) — opt-in, не часть базовой установки.

## 4. MCP

Портативный tracked entrypoint — `.mcp.json` (генерируется
`scripts/ai/codex/setup_mcp.py`; stdio-обёртки `scripts/ai/mcp/*_wrapper.sh`).
Kimi-конфигурация — machine-local: user-level `~/.kimi-code/mcp.json`
(при необходимости project `.kimi-code/mcp.json` переопределяет user-level,
project entry побеждает при совпадении имён). Значения токенов не встраиваются;
для remote `ref` — только имя переменной `REF_TOOL_API_KEY`.

Рекомендуемый дневной вариант — общая HTTP-плоскость (shared localhost plane,
см. `policy/MCP_SHARED_RUNTIME.md`): те же endpoint'ы, что в локальной
`.codex/settings.json` (порты `8813`–`8828`):

| Server | URL |
| --- | --- |
| `adr-analysis` | `http://127.0.0.1:8813/mcp` |
| `deja` | `http://127.0.0.1:8814/mcp` |
| `context7` | `http://127.0.0.1:8815/mcp` |
| `ast-grep` | `http://127.0.0.1:8816/mcp` |
| `github` | `http://127.0.0.1:8820/mcp` |
| `fetch` | `http://127.0.0.1:8821/mcp` |
| `memory` | `http://127.0.0.1:8826/mcp` |
| `filesystem` | `http://127.0.0.1:8827/mcp` |
| `code-analyzer` | `http://127.0.0.1:8828/mcp` |
| `ref` | `https://api.ref.tools/mcp` (remote, key-free base URL) |

Это избегает stdio/Docker-перезапуска процессов на каждую клиентскую сессию
(см. «Why Docker MCP multiplies containers» в `MCP_LOCAL_RUNTIME_CONFIG.md`).
stdio-вариант через обёртки `.mcp.json` — допустимый fallback для одного
клиента; XOR с HTTP-эндпоинтом того же сервера (правило `#10299` для github
актуально и для Kimi: один live endpoint на сессию).

## 5. Memory

Use the canonical memory workflow, not ad-hoc notes. Repository memory
(`docs/00-project/ai/memory/*.md`) is runtime-agnostic and needs no
migration. Identify the Kimi actor explicitly:

```bash
BIOETL_AI_RUNTIME=kimi \
BIOETL_AI_AGENT=<active-profile-or-kimi> \
python -m memory.tooling.workflow pre-task ...
python -m memory.tooling.workflow post-task ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when the runtime exposes a stable model identifier; otherwise
omit it rather than guessing. Валидации allowlist для runtime-значения нет —
свободные значения допустимы (см. `src/memory/tooling/workflow.py`,
`src/memory/proof_gate.py`).

Details: `guides/MEMORY_USAGE.md`, `src/memory/DAILY_WORKFLOW.md`.

## 6. Validation

Risk tiers V1–V4 and minimum checks follow `.codex/agents/CODEX-RUNTIME.md`.
For write-capable tasks follow
`policy/POST_CHANGE_VALIDATION.md` and report checks run, skipped checks with
reasons, mirror-sync status, and debt outcome. Useful entry points:

```bash
python scripts/ai/codex/doctor.py static --no-write
python scripts/ai/codex/setup_mcp.py --check
python scripts/ai/codex/setup_mcp.py --check-local
```

MCP changes apply on the next Kimi launch (или через watcher `KIMI_CODE_WATCH`,
по умолчанию выключен); re-read the file after editing.

## Related files

- `AGENTS.md` — root runtime contract and precedence
- `.codex/agents/CODEX-RUNTIME.md` — runtime map and task routing
- `.codex/skills/SKILLS-CATALOG.md` — canonical skill registry
- `.mcp.json` — portable workspace MCP entrypoint
- `docs/00-project/ai/agents/guides/MUSE.md` — ближайший прецедент
  зеркального рантайма (тот же уровень интеграции)
- `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md` — config classification
- `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md` — mirror ownership
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` — post-change gates
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` — memory policy
- `docs/00-project/ai/memory/agent-memory.md` — runtime-agnostic memory sheet
- `docs/00-project/RULES.md` — project rules (RFC 2119)
- `docs/00-project/NORMATIVE_SOURCES.md` — normative stack index

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
