# Docker в проекте BioETL - Быстрый старт

Docker в BioETL остается optional local-only tooling surface. По
`ADR-010` проект не требует Docker для базового development/test runtime; Docker
compose файлы и helper-скрипты существуют только как добровольная локальная
обвязка для отдельных стеков (`Neo4j`, monitoring, MCP).

Reviewed extra compose files moved out of the repository root and now live
under `scripts/ops/runtime/docker/compose/`:
`scripts/ops/runtime/docker/compose/alertmanager.yml`,
`scripts/ops/runtime/docker/compose/minio.yml`,
`scripts/ops/runtime/docker/compose/redis.yml`, and
`scripts/ops/runtime/docker/compose/sonarqube.yml`. Legacy root filenames
(`docker-compose.alertmanager.yml`, `docker-compose.minio.yml`,
`docker-compose.redis.yml`, `docker-compose.sonarqube.yml`) remain only as
historical compatibility labels in governance docs, not as tracked root
entrypoints.

<!-- BIOETL_DOCKER_HELPER_ADR010_ADJUNCT -->

Governance anchor: `BIOETL_DOCKER_HELPER_ADR010_ADJUNCT`. Machine-readable
контракт reviewed helper stacks находится в
`configs/quality/docker_helper_contracts.yaml`. Этот контракт закрепляет, что
helper compose files остаются optional local-only adjunct tooling и MUST NOT
использоваться для storage, locking или orchestration semantics приложения.

The shared read-only gate is
`python scripts/ops/runtime/docker/docker_runtime_preflight.py`. The root
Compose files have isolated project names; migration from the former
`bioactivitydataacquisition2` namespace is documented in
`docs/05-operations/runbooks/docker-compose-project-migration.md`.

## ✅ Что настроено

- ✓ `.env.example` как шаблон переменных окружения; `.env` является local-only/secret-bearing файлом и не создается автоматически
- ✓ `docker-compose.yml` - isolated `bioetl-main` quarantine/Warp helper
- ✓ `docker-compose.neo4j.yml` - isolated `bioetl-neo4j` helper
- ✓ `docker-compose.monitoring.yml` - мониторинг (Prometheus, Grafana, Loki, Tempo)
- ✓ `docker-compose.codex.yml` - MCP серверы для Codex
- ✓ Dockerfile для BioETL (multi-stage build)
- ✓ Dockerfile для Warp VPN клиента under `scripts/ops/runtime/docker/images/warp/Dockerfile`
- ✓ Dockerfiles для MCP серверов (memory, filesystem, github, fetch) under `scripts/ops/runtime/docker/images/**/Dockerfile`
- ✓ `.dockerignore` оптимизирован

## 🚀 Как запустить

### 1. Убедитесь что Docker Desktop запущен

```powershell
# Проверить Docker
docker ps

# Если не работает, запустите Docker Desktop вручную
# или используйте Windows Search: Docker Desktop
```

### 2. Запустите optional helper stack

Если локального `.env` еще нет, создайте его вручную только после явного решения:

```powershell
Copy-Item .env.example .env
```

Docker helpers также поддерживают явный opt-in `-AllowEnvFileCreate`, но не создают `.env` silently.

```powershell
# PowerShell
.\scripts\ops\docker-setup.ps1 -Mode basic

# Или вручную
docker network create bioetl-monitoring
docker compose -p bioetl-main -f docker-compose.yml up -d
```

**Что запустится в optional helper stack:**
- BioETL quarantine/health helper surface на порту 8081

Neo4j starts separately with
`docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d`.

### 3. (Опционально) Запустите мониторинг

```powershell
# Через скрипт
.\scripts\ops\docker-setup.ps1 -Mode monitoring

# Или вручную
docker network create bioetl-monitoring
docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml up -d
```

**Что запустится:**
- Prometheus на порту 9090
- Grafana на порту 3000 (`admin`; пароль из `GF_SECURITY_ADMIN_PASSWORD`)
- Loki на порту 3100
- Tempo на порту 3200

### 4. (Опционально) Запустите MCP серверы для Codex

```powershell
# Через скрипт
.\scripts\ops\docker-setup.ps1 -Mode mcp

# Или вручную
docker network create warp-network
docker compose -p bioetl-codex -f docker-compose.codex.yml up -d
```

Canonical helper scripts now bootstrap the shared external Docker networks
(`bioetl-monitoring` and `warp-network`) automatically. If you start compose
files manually on a fresh machine, create the required network first.

## 📋 Основные команды

```powershell
# Запустить optional helper stack
docker compose -p bioetl-main -f docker-compose.yml up -d

# Остановить
docker compose -p bioetl-main -f docker-compose.yml down

# Перезагрузить
docker compose -p bioetl-main -f docker-compose.yml restart

# Посмотреть логи
docker compose -p bioetl-main -f docker-compose.yml logs -f

# Логи конкретного контейнера
docker compose -p bioetl-main -f docker-compose.yml logs -f bioetl
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml logs -f neo4j

# Статус контейнеров
docker compose -p bioetl-main -f docker-compose.yml ps

# Вход в контейнер
docker compose -p bioetl-main -f docker-compose.yml exec bioetl bash
docker exec -it bioetl-neo4j bash

# Очистка неиспользуемых образов
docker image prune

# Полная очистка (внимание!)
docker system prune -a
```

## 🔑 Учетные данные

### Neo4j
- Пользователь: задаётся через `NEO4J_USERNAME`
- Пароль: задаётся через `NEO4J_PASSWORD`
- HTTP: http://localhost:7474
- Bolt: bolt://localhost:7687

### Grafana
- Пользователь: `admin`
- Пароль: задаётся через `GF_SECURITY_ADMIN_PASSWORD`
- URL: http://localhost:3000

## 📁 Файлы конфигурации

| Файл | Описание |
|------|---------|
| `.env` | Machine-local переменные окружения (создается только вручную или через явный opt-in helper flag) |
| `docker-compose.yml` | Основной helper-стек BioETL/Warp; Neo4j принадлежит отдельному проекту `bioetl-neo4j` |
| `docker-compose.monitoring.yml` | Мониторинг (Prometheus, Grafana, Loki, Tempo) |
| `docker-compose.codex.yml` | MCP серверы для Codex |
| `scripts/ops/runtime/docker/compose/alertmanager.yml` | Optional adjunct Alertmanager helper stack; not part of baseline runtime; legacy root filename: `docker-compose.alertmanager.yml` |
| `scripts/ops/runtime/docker/compose/minio.yml` | Optional local MinIO helper stack; not part of ADR-010 runtime. Requires explicit `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`; binds to localhost only; legacy root filename: `docker-compose.minio.yml` |
| `scripts/ops/runtime/docker/compose/redis.yml` | Optional local Redis helper stack; not part of ADR-010 runtime. Requires explicit `REDIS_PASSWORD`; binds to localhost only; legacy root filename: `docker-compose.redis.yml` |
| `scripts/ops/runtime/docker/compose/sonarqube.yml` | Optional local SonarQube helper stack; not part of baseline runtime. Requires local-only `SONARQUBE_DB_PASSWORD` and `SONARQUBE_SYSTEM_PASSCODE`; binds to localhost only; legacy root filename: `docker-compose.sonarqube.yml` |
| `Dockerfile.bioetl` | Образ BioETL (multi-stage Python) |
| `scripts/ops/runtime/docker/images/warp/Dockerfile` | Warp VPN клиент; legacy root filename: `Dockerfile.warp` |
| `scripts/ops/runtime/docker/images/mcp-*/Dockerfile` | MCP серверы (Node.js); legacy root filenames: `Dockerfile.mcp-*` |
| `.dockerignore` | Файлы исключены из образа |

## 🐛 Решение проблем

### Docker не запускается
```powershell
# Перезапустить Docker Desktop штатной командой или через GUI;
# принудительное завершение процесса не является первым шагом восстановления.
docker desktop restart
```

### Порты уже заняты
```powershell
# Найти процесс на порту
Get-Process -Id (Get-NetTCPConnection -LocalPort 8081).OwningProcess

# Если контейнер уже запущен
docker compose -p bioetl-main -f docker-compose.yml restart

# Если нужно изменить порт, отредактируйте docker-compose.yml
```

### Neo4j не подключается
```powershell
# Проверить логи
docker logs bioetl-neo4j

# Проверить что порты открыты
docker port bioetl-neo4j

# Перезагрузить
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml restart neo4j
```

### Нет места на диске
```powershell
docker system df          # Показать использование

docker system prune -a    # Очистить (внимание!)
```

## 📊 Мониторинг

Все контейнеры имеют healthcheck:

```powershell
# Проверить здоровье контейнеров
docker ps --filter health=healthy
docker ps --filter health=unhealthy

# Детальная информация
docker compose -p bioetl-main -f docker-compose.yml ps bioetl
```

## 🔄 Обновление образов

```powershell
# Скачать новые версии
docker compose -p bioetl-main -f docker-compose.yml pull

# Пересобрать и запустить
docker compose -p bioetl-main -f docker-compose.yml up --build -d
```

## 📚 Документация

- Полное описание: `docs/DOCKER_SETUP.md`
- Codex launcher docs: `docs/05-operations/tooling/scripts-ops/CODEX_SETUP.md`
- WSL интеграция: `docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md`
- Root Docker helper relocation audit:
  `docs/05-operations/verification/docker-helper-root-relocation-audit.md`

## ✨ Что дальше

1. **Запустите optional helper stack**
   ```powershell
   docker compose -p bioetl-main -f docker-compose.yml up -d
   docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d
   ```

2. **Проверьте Neo4j Browser**
   ```
   http://localhost:7474
   ```

3. **Запустите Codex**
   ```powershell
   .\scripts\ai\codex\run-codex.ps1
   ```

---

**Автоматизированные скрипты:**
- `.\scripts\ops\docker-setup.ps1` - Canonical интерактивная настройка Docker для Windows; `.env` создается только с `-AllowEnvFileCreate` или `BIOETL_CREATE_LOCAL_ENV_FILES=1`
- `scripts/ops/docker-setup.sh` - Canonical Bash версия для WSL/Linux; `.env` создается только с `BIOETL_CREATE_LOCAL_ENV_FILES=1`
- Extra reviewed compose files for Alertmanager / MinIO / Redis / SonarQube
  остаются manual-only helper surfaces и не запускаются canonical helper script
  по умолчанию
- Manual-only helper compose files that join the monitoring network require
  `docker network create bioetl-monitoring` first on a fresh machine
- Redis, MinIO and SonarQube helper compose files require explicit local
  credential environment variables. `.env.example` keeps these values empty so
  copied local `.env` files fail closed until the operator fills machine-local
  secrets.
- Helper stack metrics posture is governed by
  `configs/quality/docker_helper_contracts.yaml`: Redis, MinIO and
  Alertmanager have Prometheus scrape contracts; SonarQube is healthcheck-only
  in repo-default Prometheus because its native metrics endpoint requires a
  runtime passcode.
- Before restoring any reviewed root Docker helper surface, consult
  `docs/05-operations/verification/docker-helper-root-relocation-audit.md`.

**Все готово к запуску!** 🚀
