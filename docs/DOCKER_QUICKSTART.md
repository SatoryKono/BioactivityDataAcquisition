# Docker в проекте BioETL - Быстрый старт

Docker в BioETL остается optional local-only tooling surface. По
`ADR-010` проект не требует Docker для базового development/test runtime; Docker
compose файлы и helper-скрипты существуют только как добровольная локальная
обвязка для отдельных стеков (`Neo4j`, monitoring, MCP).

Reviewed extra compose files в корне (`docker-compose.alertmanager.yml`,
`docker-compose.minio.yml`, `docker-compose.redis.yml`,
`docker-compose.sonarqube.yml`) сохраняются только как optional adjunct helper
stacks для локальной диагностики или точечных интеграционных экспериментов.
Они не входят в canonical helper flow и не являются обязательной частью
Local-Only runtime.

<!-- BIOETL_DOCKER_HELPER_ADR010_ADJUNCT -->

Governance anchor: `BIOETL_DOCKER_HELPER_ADR010_ADJUNCT`. Machine-readable
контракт reviewed helper stacks находится в
`configs/quality/docker_helper_contracts.yaml`. Этот контракт закрепляет, что
helper compose files остаются optional local-only adjunct tooling и MUST NOT
использоваться для storage, locking или orchestration semantics приложения.

## ✅ Что настроено

- ✓ `.env.example` как шаблон переменных окружения; `.env` является local-only/secret-bearing файлом и не создается автоматически
- ✓ `docker-compose.yml` - основной стек (Neo4j + BioETL)
- ✓ `docker-compose.monitoring.yml` - мониторинг (Prometheus, Grafana, Loki, Tempo)
- ✓ `docker-compose.codex.yml` - MCP серверы для Codex
- ✓ Dockerfile для BioETL (multi-stage build)
- ✓ Dockerfile для Warp VPN клиента
- ✓ Dockerfiles для MCP серверов (memory, filesystem, github, fetch)
- ✓ `.dockerignore` оптимизирован

## 🚀 Как запустить

### 1. Убедитесь что Docker Desktop запущен

```powershell
# Проверить Docker
docker ps

# Если не работает, запустите Docker Desktop вручную
# или используйте Windows Search: Docker Desktop
```

### 2. Запустите основной стек

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
docker compose up -d
```

**Что запустится:**
- Neo4j База данных на порту 7687 (bolt)
- Neo4j Browser на порту 7474
- BioETL приложение на порту 8081

### 3. (Опционально) Запустите мониторинг

```powershell
# Через скрипт
.\scripts\ops\docker-setup.ps1 -Mode monitoring

# Или вручную
docker network create bioetl-monitoring
docker compose -f docker-compose.monitoring.yml up -d
```

**Что запустится:**
- Prometheus на порту 9090
- Grafana на порту 3000 (admin/changeme)
- Loki на порту 3100
- Tempo на порту 3200

### 4. (Опционально) Запустите MCP серверы для Codex

```powershell
# Через скрипт
.\scripts\ops\docker-setup.ps1 -Mode mcp

# Или вручную
docker network create warp-network
docker compose -f docker-compose.codex.yml up -d
```

Canonical helper scripts now bootstrap the shared external Docker networks
(`bioetl-monitoring` and `warp-network`) automatically. If you start compose
files manually on a fresh machine, create the required network first.

## 📋 Основные команды

```powershell
# Запустить все (основной стек)
docker compose up -d

# Остановить
docker compose down

# Перезагрузить
docker compose restart

# Посмотреть логи
docker compose logs -f

# Логи конкретного контейнера
docker compose logs -f bioetl-app
docker compose logs -f bioetl-neo4j

# Статус контейнеров
docker compose ps

# Вход в контейнер
docker exec -it bioetl-app bash
docker exec -it bioetl-neo4j bash

# Очистка неиспользуемых образов
docker image prune

# Полная очистка (внимание!)
docker system prune -a
```

## 🔑 Учетные данные

### Neo4j
- Пользователь: `neo4j`
- Пароль: `bioetl_secure_password`
- HTTP: http://localhost:7474
- Bolt: bolt://localhost:7687

### Grafana
- Пользователь: `admin`
- Пароль: `changeme` (измените после входа!)
- URL: http://localhost:3000

## 📁 Файлы конфигурации

| Файл | Описание |
|------|---------|
| `.env` | Machine-local переменные окружения (создается только вручную или через явный opt-in helper flag) |
| `docker-compose.yml` | Основной стек (Neo4j + BioETL) |
| `docker-compose.monitoring.yml` | Мониторинг (Prometheus, Grafana, Loki, Tempo) |
| `docker-compose.codex.yml` | MCP серверы для Codex |
| `docker-compose.alertmanager.yml` | Optional adjunct Alertmanager helper stack; not part of baseline runtime |
| `docker-compose.minio.yml` | Optional local MinIO helper stack; not part of ADR-010 runtime. Requires explicit `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`; binds to localhost only |
| `docker-compose.redis.yml` | Optional local Redis helper stack; not part of ADR-010 runtime. Requires explicit `REDIS_PASSWORD`; binds to localhost only |
| `docker-compose.sonarqube.yml` | Optional local SonarQube helper stack; not part of baseline runtime. Requires local-only `SONARQUBE_DB_PASSWORD` and `SONARQUBE_SYSTEM_PASSCODE`; binds to localhost only |
| `Dockerfile.bioetl` | Образ BioETL (multi-stage Python) |
| `Dockerfile.warp` | Warp VPN клиент |
| `Dockerfile.mcp-*` | MCP серверы (Node.js) |
| `.dockerignore` | Файлы исключены из образа |

## 🐛 Решение проблем

### Docker не запускается
```powershell
# Перезагрузить Docker Desktop
taskkill /F /IM Docker.exe  # Убить процесс
# Запустить Docker Desktop вручную
```

### Порты уже заняты
```powershell
# Найти процесс на порту
Get-Process -Id (Get-NetTCPConnection -LocalPort 8081).OwningProcess

# Если контейнер уже запущен
docker compose restart

# Если нужно изменить порт, отредактируйте docker-compose.yml
```

### Neo4j не подключается
```powershell
# Проверить логи
docker logs bioetl-neo4j

# Проверить что порты открыты
docker port bioetl-neo4j

# Перезагрузить
docker compose restart bioetl-neo4j
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
docker inspect bioetl-app | findstr -i health
```

## 🔄 Обновление образов

```powershell
# Скачать новые версии
docker compose pull

# Пересобрать и запустить
docker compose up --build -d
```

## 📚 Документация

- Полное описание: `docs/DOCKER_SETUP.md`
- Codex MCP: `docs/CODEX_QUICK_START.md`
- WSL интеграция: `docs/CODEX_WSL_SETUP.md`

## ✨ Что дальше

1. **Запустите основной стек**
   ```powershell
   docker compose up -d
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

**Все готово к запуску!** 🚀
