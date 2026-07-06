# Docker Setup for BioETL Project

Docker остается optional local-only runtime surface. Скрипты настройки не
создают и не перезаписывают `.env` автоматически: `.env` считается
machine-local/secret-bearing файлом. Если файл нужен для локального Docker
запуска, создайте его вручную из `.env.example` после явного решения или
используйте opt-in флаг helper-скрипта.

Reviewed extra compose files moved out of the repository root and now live
under `scripts/ops/runtime/docker/compose/`:
`scripts/ops/runtime/docker/compose/alertmanager.yml`,
`scripts/ops/runtime/docker/compose/minio.yml`,
`scripts/ops/runtime/docker/compose/redis.yml`, and
`scripts/ops/runtime/docker/compose/sonarqube.yml`. Legacy root filenames
(`docker-compose.alertmanager.yml`, `docker-compose.minio.yml`,
`docker-compose.redis.yml`, `docker-compose.sonarqube.yml`) are retained only
as historical compatibility labels in governance docs, not as tracked root
entrypoints.

<!-- BIOETL_DOCKER_HELPER_ADR010_ADJUNCT -->

Governance anchor: `BIOETL_DOCKER_HELPER_ADR010_ADJUNCT`. Reviewed helper stack
contract source: `configs/quality/docker_helper_contracts.yaml`. Redis, MinIO,
SonarQube and Alertmanager helper compose files MUST remain optional
local-only adjunct tooling and MUST NOT become application storage, locking, or
orchestration dependencies.
Relocation audit source:
`docs/05-operations/verification/docker-helper-root-relocation-audit.md`.

## ✓ Проверка Docker

```powershell
docker --version
docker compose --version
```

## 1️⃣ Запуск optional helper stack (Neo4j + BioETL)

```powershell
# Запустить основные контейнеры
docker network create bioetl-monitoring
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f bioetl-app
```

**Сервисы:**
- BioETL: http://localhost:8081 (quarantine serve)
- Neo4j Browser: http://localhost:7474
- Neo4j Bolt: bolt://localhost:7687

**Учетные данные Neo4j:**
- Пользователь: `neo4j`
- Пароль: `bioetl_secure_password`

## 2️⃣ Запуск Monitoring стека (Prometheus, Grafana, Loki, Tempo)

```powershell
# Запустить мониторинг
docker network create bioetl-monitoring
docker compose -f docker-compose.monitoring.yml up -d

# Проверить статус
docker compose -f docker-compose.monitoring.yml ps
```

**Сервисы мониторинга:**
- Grafana: http://localhost:3000 (admin/changeme)
- Prometheus: http://localhost:9090
- Loki: http://localhost:3100
- Tempo: http://localhost:3200

## 3️⃣ Запуск MCP серверов для Codex

```powershell
# Запустить MCP серверы
docker network create warp-network
docker compose -f docker-compose.codex.yml up -d

# Проверить статус
docker compose -f docker-compose.codex.yml ps
```

Canonical helper scripts `scripts/ops/docker-setup.ps1` and
`scripts/ops/docker-setup.sh` automatically ensure these shared external
networks before starting compose stacks. Manual `docker compose ... up` on a
fresh machine must create them first.

**MCP Серверы:**
- bioetl-mcp-memory
- bioetl-mcp-filesystem
- bioetl-mcp-github
- bioetl-mcp-fetch

## 📋 Полезные команды

### Основной стек
```powershell
# Запустить
docker compose up -d

# Остановить
docker compose down

# Перестартовать
docker compose restart

# Посмотреть логи
docker compose logs -f
docker compose logs -f bioetl-app
docker compose logs -f bioetl-neo4j

# Проверить статус
docker compose ps
```

### Мониторинг
```powershell
docker compose -f docker-compose.monitoring.yml up -d
docker compose -f docker-compose.monitoring.yml down
docker compose -f docker-compose.monitoring.yml logs -f
```

### MCP Серверы
```powershell
docker compose -f docker-compose.codex.yml up -d
docker compose -f docker-compose.codex.yml down
docker compose -f docker-compose.codex.yml logs -f
```

### Общие команды
```powershell
# Просмотр всех контейнеров
docker ps -a

# Просмотр образов
docker images

# Очистка неиспользуемых образов
docker image prune

# Очистка неиспользуемых томов
docker volume prune

# Полная очистка (внимание!)
docker system prune -a

# Используемое место
docker system df
```

## 🔧 Конфигурация

Основной файл конфигурации: `.env`

Важные переменные:
```
NEO4J_AUTH_USERNAME=neo4j
NEO4J_AUTH_PASSWORD=bioetl_secure_password
LOG_LEVEL=INFO
GRAFANA_ADMIN_PASSWORD=changeme
```

Optional adjunct helper compose files require explicit local credentials rather
than runnable defaults:

```powershell
# Redis helper
$env:REDIS_PASSWORD = "<local-redis-password>"

# MinIO helper
$env:MINIO_ROOT_USER = "<local-minio-user>"
$env:MINIO_ROOT_PASSWORD = "<local-minio-password>"

# SonarQube helper
$env:SONARQUBE_DB_PASSWORD = "<local-sonarqube-db-password>"
$env:SONARQUBE_SYSTEM_PASSCODE = "<local-sonarqube-system-passcode>"
```

These variables may be stored in a machine-local `.env` after explicit operator
approval. The tracked `.env.example` intentionally keeps secret-bearing helper
values empty.

## 🐛 Диагностика

### Контейнер не запускается
```powershell
docker logs container_name
docker inspect container_name
```

### Проблемы с портами
```powershell
# Проверить какие порты используются
netstat -ano | findstr :8081

# Если порт занят, найти процесс
Get-Process -Id (Get-NetTCPConnection -LocalPort 8081).OwningProcess
```

### Проблемы с сетью
```powershell
# Проверить сеть
docker network ls
docker network inspect warp-network
docker network inspect bioetl-monitoring

# Если shared external network ещё не создан
docker network create warp-network
docker network create bioetl-monitoring
```

### Пересборка контейнеров
```powershell
# Пересобрать и запустить
docker compose up --build -d

# Пересобрать конкретный сервис
docker compose build bioetl
```

## 📊 Проверка здоровья

```powershell
# Все контейнеры должны быть "Up"
docker compose ps

# Проверить healthcheck
docker ps --filter health=healthy
docker ps --filter health=unhealthy

# Детально проверить контейнер
docker inspect bioetl-app | findstr -i health
```

## 🚀 Полное включение проекта

```powershell
# 1. Основной стек
docker compose up -d

# 2. Мониторинг (опционально)
docker compose -f docker-compose.monitoring.yml up -d

# 3. MCP серверы для Codex
docker compose -f docker-compose.codex.yml up -d

# 4. Проверить все контейнеры
docker ps | Select-String bioetl

# 5. Запустить Codex
.\scripts\ai\codex\run-codex.ps1 mcp-setup
.\scripts\ai\codex\run-codex.ps1
```

## 📝 Примечания

- Neo4j по умолчанию использует 512MB heap, можно увеличить если нужно
- Grafana пароль `changeme` — измените после первого входа
- MCP серверы автоматически подключаются к Codex
- Docker Desktop должен быть запущен перед использованием
- WSL2 интеграция должна быть включена в Docker Desktop Settings

---

Вся конфигурация хранится в файлах:
- `docker-compose.yml` — optional local helper stack
- `docker-compose.monitoring.yml` — мониторинг
- `docker-compose.codex.yml` — MCP серверы
- `scripts/ops/runtime/docker/compose/alertmanager.yml` — optional local Alertmanager helper stack; legacy root filename: `docker-compose.alertmanager.yml`
- `scripts/ops/runtime/docker/compose/minio.yml` — optional local MinIO helper stack; requires explicit `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`; binds to localhost only; legacy root filename: `docker-compose.minio.yml`
- `scripts/ops/runtime/docker/compose/redis.yml` — optional local Redis helper stack; requires explicit `REDIS_PASSWORD`; binds to localhost only; legacy root filename: `docker-compose.redis.yml`
- `scripts/ops/runtime/docker/compose/sonarqube.yml` — optional local SonarQube helper stack; requires local-only `SONARQUBE_DB_PASSWORD` and `SONARQUBE_SYSTEM_PASSCODE`; binds to localhost only; legacy root filename: `docker-compose.sonarqube.yml`
- Reviewed adjunct helper compose files that attach to `bioetl-monitoring`
  require `docker network create bioetl-monitoring` before first manual start
- Helper stack observability posture is governed by
  `configs/quality/docker_helper_contracts.yaml`: Redis, MinIO and
  Alertmanager have Prometheus scrape contracts; SonarQube remains
  healthcheck-only in repo-default Prometheus because its native metrics
  endpoint requires runtime passcode authentication.
- `.env` — переменные окружения
- `Dockerfile.bioetl` — optional local BioETL helper image
- `scripts/ops/runtime/docker/images/**/Dockerfile` — optional helper image definitions
