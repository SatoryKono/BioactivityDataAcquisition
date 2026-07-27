# Cursor runtime setup

Синхронизирует MCP и skills Cursor с каноническим Codex runtime в репозитории.

## Важно: local-only surfaces

`.cursor/**` and `.vscode/**` are **gitignored** machine-local deploy targets.
A plain `git clone` does **not** install Cursor MCP or project skills — run the
setup below after every fresh checkout (or when skills/MCP inventory changes).

Tracked sources of truth:

| Surface | Tracked SSOT | Local deploy |
| --- | --- | --- |
| Cursor rules | `docs/00-project/ai/rules/cursor/*.mdc` | `.cursor/rules/` |
| Skills | `.codex/skills/**` | `.cursor/skills/*` relative symlinks |
| MCP portable | `.mcp.json` (stdio, full inventory) | `.cursor/mcp.json` (profiled; default **stable**) |

Policy: `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`.

## Быстрый старт

```bash
bash scripts/ai/cursor/setup_cursor.sh
```

Скрипт:

1. Регенерирует `.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json`, `.codex/settings.json`
1. Обновляет `~/.codex/config.toml`
1. Создаёт **relative** symlink skills: `.cursor/skills/<name>` → `../../.codex/skills/<name>`
1. Prunes stale links (e.g. historical dangling `public`)

Daily MCP default is `--profile stable`. For multi-client heavy plane:

```bash
python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation
```

## Отдельные команды

```bash
python scripts/ai/codex/setup_mcp.py --root . --workspace-root . --skip-codex --skip-gemini-settings
bash scripts/ai/cursor/setup_skills.sh
bash scripts/ai/cursor/setup_skills.sh --project-only
```

## После настройки

Перезагрузите окно Cursor (`Developer: Reload Window`).

## Источник истины

- Skills: `.codex/skills/**`
- MCP: `scripts/ai/codex/setup_mcp.py`
- Cursor rules SSOT: `docs/00-project/ai/rules/cursor/**`
