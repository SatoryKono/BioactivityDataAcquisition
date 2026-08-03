______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-08'

______________________________________________________________________

# Neo4j Backend Startup Guide

> Статус: MCP регистрация завершена, требуется запуск Neo4j backend контейнера.

## Минимальный Запуск (Локально на машине)

### Шаг 1: Запустить Neo4j контейнер

```bash
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait
```

**Параметры:**

- `-d`: Запуск в фоне (detached mode)
- `--name bioetl-neo4j`: Имя контейнера для идентификации
- `-p 7474:7474`: HTTP UI (Neo4j Browser)
- `-p 7687:7687`: Bolt протокол (для приложений и MCP)
- `-e NEO4J_AUTH`: Учетные данные (user/password)
- `neo4j:5.15-community`: Образ и версия

### Шаг 2: Проверить статус контейнера

```bash
# Проверить, что контейнер запущен
docker ps | grep bioetl-neo4j

# Просмотреть логи запуска
docker logs bioetl-neo4j

# Дождаться полного стартапа (сообщение "Started")
docker logs -f bioetl-neo4j
```

### Шаг 3: Проверить подключение портов

```bash
# Проверить доступность портов
netstat -an | grep 7687  # Bolt
netstat -an | grep 7474  # HTTP (если доступно)

# Или с помощью curl
curl -I http://localhost:7474/browser/ 2>&1 | head -5
```

## Запуск через Docker Compose (Альтернатива)

Если Docker Compose доступен в вашем окружении:

```bash
# Из корня проекта
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait
```

## Остановка Neo4j

```bash
# Остановить контейнер (сохранить данные)
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml down

# Полностью удалить контейнер
# Compose `down` removes project containers but preserves named volumes by default.

# Удаление томов с данными выполняется только отдельной процедурой из
# docker-compose-project-migration.md после проверенного backup/restore drill.
```

## Проверка MCP Подключения

После запуска Neo4j:

### 1. Проверить регистрацию MCP

```bash
codex mcp get neo4j-memory
```

**Ожидаемый результат:**

```
neo4j-memory: scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh
Status: registered
```

### 2. Запустить полную проверку

```bash
bash scripts/ai/mcp/check.sh
```

**Ожидаемые результаты:**

- ✅ Server 'neo4j-memory' is registered
- ✅ neo4j-memory is routed through the project wrapper
- Все остальные серверы также должны быть в статусе OK

### 3. Проверить подключение из скрипта

```bash
# Проверить, может ли MCP найти Neo4j
docker logs bioetl-neo4j | grep -E "Started|ERROR"
```

## Доступ к Neo4j Browser

После успешного запуска:

- **URL**: http://localhost:7474/browser/
- **Username**: `neo4j`
- **Password**: обязательное значение `NEO4J_PASSWORD`

## Переменные Окружения

Если нужно использовать кастомные учетные данные:

```bash
# Единственный владелец — Compose project bioetl-neo4j
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait

# Вариант 2: Через .env (если используется docker-compose)
# Создать или обновить .env:
NEO4J_AUTH=neo4j/your-custom-password
NEO4J_URI=bolt://localhost:7687
```

## Конфигурация MCP Wrapper

Скрипт `scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh` автоматически:

1. Загружает переменные из `.env`
1. Парсит `NEO4J_AUTH` в username/password
1. Устанавливает `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
1. Запускает MCP сервер @knowall-ai/mcp-neo4j-agent-memory

**Переменные окружения, которые использует wrapper:**

| Переменная       | Источник                               | По умолчанию             |
| ---------------- | -------------------------------------- | ------------------------ |
| `NEO4J_URI`      | `.env` или переменная                  | `bolt://localhost:7687`  |
| `NEO4J_USERNAME` | `NEO4J_AUTH` или `NEO4J_AUTH_USERNAME` | `neo4j`                  |
| `NEO4J_PASSWORD` | `NEO4J_AUTH` или `NEO4J_AUTH_PASSWORD` | обязательное локальное значение |
| `NEO4J_DATABASE` | `.env`                                 | `neo4j`                  |

## Troubleshooting

### Ошибка: "Error: connect ECONNREFUSED 127.0.0.1:7687"

```bash
# Проверить статус контейнера
docker ps | grep bioetl-neo4j

# Если контейнер не запущен:
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait

# Если сервиса нет, запустить его через единственного Compose-владельца
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait
```

### Ошибка: "port 7687 is already allocated"

```bash
# Найти процесс на порте 7687
docker ps | grep 7687

# Остановить конфликтующий процесс, затем повторить канонический запуск
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait
```

### Ошибка: "Invalid memory configuration"

Если используется docker-compose и видна ошибка памяти:

- Уменьшить значения в `NEO4J_HEAP_MAX`, `NEO4J_PAGECACHE`
- Проверить доступную память на хосте: `free -h` (Linux) или Task Manager (Windows)

## Мониторинг

```bash
# Реальное использование ресурсов
docker stats bioetl-neo4j

# История логов
docker logs -f bioetl-neo4j

# Информация о контейнере
docker inspect bioetl-neo4j
```

## Next Steps

1. ✅ Запустить Neo4j: `docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait`
1. ✅ Проверить статус: `codex mcp get neo4j-memory`
1. ✅ Запустить тест: `bash scripts/ai/mcp/check.sh`
1. ✅ Открыть Neo4j Browser: http://localhost:7474/browser/

## Связанные Документы

- [Neo4j Memory Configuration](./neo4j-memory-setup.md) - Детальная конфигурация памяти
- [MCP Configuration](./NEO4J-MCP-INDEX.md) - Обзор MCP конфигурации
- Neo4j Official: https://neo4j.com/docker/
