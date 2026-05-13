# MCP Codex Stable Startup Guide

## Статус конфигурации ✓

Система настроена и готова к работе.

### Запущенные сервисы MCP:

- **mcp-memory** (2026.1.26) — Knowledge Graph Memory Server
- **mcp-filesystem** (2026.1.14) — Secure Filesystem Server
- **mcp-github** (2025.4.8) — GitHub MCP Server
- **mcp-fetch** (2025.4.7) — HTTP Fetch Server
- **mcp-codex-config** (Caddy) — Dashboard на http://localhost:9100

### Главные изменения:

1. ✓ **Pinned версии** вместо `@latest` — предотвращает неожиданные обновления
2. ✓ **NPM_CONFIG_AUDIT: false** — отключены повторяющиеся предупреждения
3. ✓ **--no-fund флаг** — убирает сообщения про funding
4. ✓ **Volume caching** — node_modules и pip cache сохраняются в Docker volumes
5. ✓ **exec для процессов** — гарантирует корректное завершение
6. ✓ **on-failure restart** — рестартует только при ошибке
7. ✓ **Health checks** — мониторит состояние каждого сервера

---

## Запуск

### PowerShell (Windows):
```powershell
.\scripts\startup.ps1 -Environment dev
```

### Bash/WSL:
```bash
./scripts/startup.sh dev
```

### Docker Compose напрямую:
```bash
docker compose -f docker-compose.codex.yml up -d
```

---

## Остановка

### PowerShell:
```powershell
.\scripts\shutdown.ps1
```

### Bash:
```bash
./scripts/shutdown.sh
```

### Docker Compose:
```bash
docker compose -f docker-compose.codex.yml down
```

---

## Проверка статуса

```bash
docker compose -f docker-compose.codex.yml ps
```

Вывод должен показать:
```
NAME                      STATUS
bioetl-mcp-memory         Up (health: healthy)
bioetl-mcp-filesystem     Up (health: healthy)
bioetl-mcp-github         Up (health: healthy)
bioetl-mcp-fetch          Up (health: healthy)
bioetl-codex-config       Up (health: healthy)
```

---

## Просмотр логов

```bash
# Все сервисы
docker compose -f docker-compose.codex.yml logs -f

# Конкретный сервис
docker logs -f bioetl-mcp-github
docker logs -f bioetl-mcp-memory
```

---

## Инструменты Codex

### В WSL через bash (рекомендуется):
```bash
wsl -d Ubuntu bash -lc "codex"
```

### Через NPM глобально:
```bash
/home/fedor/.npm-global/bin/codex --version
```

### Обновление Codex:
```bash
npm install -g --prefix /home/fedor/.npm-global @openai/codex@0.130.0
```

---

## Troubleshooting

### Контейнеры не запускаются

1. Проверьте сеть:
```bash
docker network inspect warp-network
```

2. Пересоздайте сеть:
```bash
docker network rm warp-network
docker network create warp-network
```

3. Полный рестарт:
```bash
docker compose -f docker-compose.codex.yml down --remove-orphans
docker compose -f docker-compose.codex.yml up -d
```

### Memory Server перезагружается

Это нормально если видите `Exited (0)` — означает корректное завершение, `on-failure` означает что контейнер рестартует только при ошибке.

### npm warnings про funding

Уже отключены флагом `--no-fund`. Если видите, значит кеш не обновился:
```bash
docker compose -f docker-compose.codex.yml down
docker volume prune
docker compose -f docker-compose.codex.yml up -d
```

### Порт 9100 занят

Изменить в docker-compose.codex.yml:
```yaml
ports:
  - "9100:9100"  # Измените первый номер на другой
```

---

## Переменные окружения

Установите в `.env`:
```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx...
```

Загрузятся автоматически при `docker compose up`.

---

## Дополнительно

- Скрипты находятся в: `./scripts/startup.ps1`, `./scripts/startup.sh`
- Конфиг MCP: `.mcp.json` (основной конфиг для Codex)
- Docker конфиг: `docker-compose.codex.yml`
