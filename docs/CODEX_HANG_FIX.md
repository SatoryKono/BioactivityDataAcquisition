# Почему Codex зависает и как это исправить

## Проблема

Когда запускаете `launch-codex-wsl.ps1 start`, Codex зависает потому что:

1. **WSL stdin блокируется** - Codex пытается читать интерактивные вводы через stdin
2. **npm update prompt** - интерактивное меню обновления npm зависает
3. **Codex CLI ждет ввода** - ожидает подтверждений или команд пользователя

## Решение

Codex **не предназначен для запуска через WSL в терминале**. Вместо этого:

### ✓ Правильный способ использования Codex

1. **Откройте Anthropic Codex Desktop приложение** (установленное на Windows)
2. **Убедитесь, что MCP серверы запущены:**
   ```powershell
   .\scripts\codex-start-wsl.ps1
   ```
3. **Сконфигурируйте MCP серверы в Codex** через Settings > MCP Servers
4. **Используйте Codex через GUI**, не через CLI

### Конфигурация MCP в Codex

В `.codex/settings.json` или через UI добавьте:

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory@2026.1.26"],
      "env": {
        "MEMORY_FILE_PATH": "/path/to/memory.json"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem@2026.1.14", "/workspace"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github@latest"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"
      }
    },
    "fetch": {
      "command": "uvx",
      "args": ["--from", "mcp-server-fetch==2025.4.7", "mcp-server-fetch"]
    }
  }
}
```

## Диагностика

Если Codex всё ещё зависает:

```powershell
# Проверьте статус MCP серверов
docker compose -f docker-compose.codex.yml ps

# Посмотрите логи
docker compose -f docker-compose.codex.yml logs -f bioetl-mcp-memory

# Убейте зависшие процессы
Get-Process wsl -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Команды

```powershell
# Запустить MCP серверы
.\scripts\codex-start-wsl.ps1

# Остановить серверы
docker compose -f docker-compose.codex.yml down

# Проверить статус
.\scripts\codex-launcher.ps1 server

# Посмотреть конфигурацию
.\scripts\codex-launcher.ps1 config
```

## Альтернатива: Headless режим

Если вам нужен CLI режим без GUI, используйте:

```bash
# В WSL (Ubuntu)
cd /path/to/bioetl-checkout
# Используйте claude CLI или другие инструменты вместо Codex CLI
```

## Резюме

| Способ | Статус | Рекомендация |
|--------|--------|-------------|
| Codex GUI Desktop | ✓ Работает | **Используйте это** |
| Codex CLI через WSL | ✗ Зависает | Избегайте |
| Docker MCP серверы | ✓ Работают | Поддерживает GUI |

**Главное:** Codex GUI приложение автоматически найдёт запущенные MCP серверы. Вам просто нужно убедиться, что контейнеры запущены через `docker compose`.
