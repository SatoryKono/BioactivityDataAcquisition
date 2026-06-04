# Cursor runtime setup

Синхронизирует MCP и skills Cursor с каноническим Codex runtime в репозитории.

## Быстрый старт

```bash
bash scripts/ai/cursor/setup_cursor.sh
```

Скрипт:

1. Регенерирует `.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json`, `.codex/settings.json`
1. Обновляет `~/.codex/config.toml` (как `ensure-mcp.sh` для Codex)
1. Создаёт symlink skills: `.codex/skills/*` → `.cursor/skills/*` и `~/.cursor/skills/*`

## Отдельные команды

```bash
# Только MCP
python3 scripts/ai/codex/setup_mcp.py --root . --workspace-root . --skip-codex --skip-gemini-settings

# Только skills
bash scripts/ai/cursor/setup_skills.sh
bash scripts/ai/cursor/setup_skills.sh --project-only   # без ~/.cursor/skills
```

## После настройки

Перезагрузите окно Cursor (`Developer: Reload Window`), чтобы подхватить MCP servers и project skills.

## Источник истины

- Skills: `.codex/skills/**`
- MCP servers: `scripts/ai/codex/setup_mcp.py`
