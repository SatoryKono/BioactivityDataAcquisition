---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-08'
---

# Neo4j Backend Startup Guide

> Статус: MCP регистрация завершена, требуется запуск Neo4j backend контейнера.

## Минимальный Запуск (Локально на машине)

### Шаг 1: Запустить Neo4j контейнер

```bash
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community
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
docker compose up -d neo4j
```

## Остановка Neo4j

```bash
# Остановить контейнер (сохранить данные)
docker stop bioetl-neo4j

# Полностью удалить контейнер
docker rm bioetl-neo4j

# Если удалять тома с данными (⚠️ потеря данных)
docker rm -v bioetl-neo4j
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
- **Password**: `bioetl_secure_password` (или ваша кастомная пароль)

## Переменные Окружения

Если нужно использовать кастомные учетные данные:

```bash
# Вариант 1: Через docker run
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-custom-password \
  neo4j:5.15-community

# Вариант 2: Через .env (если используется docker-compose)
# Создать или обновить .env:
NEO4J_AUTH=neo4j/your-custom-password
NEO4J_URI=bolt://localhost:7687
```

## Конфигурация MCP Wrapper

Скрипт `scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh` автоматически:

1. Загружает переменные из `.env`
2. Парсит `NEO4J_AUTH` в username/password
3. Устанавливает `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
4. Запускает MCP сервер @knowall-ai/mcp-neo4j-agent-memory

**Переменные окружения, которые использует wrapper:**

| Переменная | Источник | По умолчанию |
|------------|----------|--------------|
| `NEO4J_URI` | `.env` или переменная | `bolt://localhost:7687` |
| `NEO4J_USERNAME` | `NEO4J_AUTH` или `NEO4J_AUTH_USERNAME` | `neo4j` |
| `NEO4J_PASSWORD` | `NEO4J_AUTH` или `NEO4J_AUTH_PASSWORD` | `bioetl_secure_password` |
| `NEO4J_DATABASE` | `.env` | `neo4j` |

## Troubleshooting

### Ошибка: "Error: connect ECONNREFUSED 127.0.0.1:7687"

```bash
# Проверить статус контейнера
docker ps | grep bioetl-neo4j

# Если контейнер не запущен:
docker start bioetl-neo4j

# Если контейнера нет вообще, запустить заново
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community
```

### Ошибка: "port 7687 is already allocated"

```bash
# Найти процесс на порте 7687
docker ps | grep 7687

# Остановить конфликтующий контейнер или использовать другой порт
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7688:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community
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

1. ✅ Запустить Neo4j: `docker run -d --name bioetl-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/bioetl_secure_password neo4j:5.15-community`
2. ✅ Проверить статус: `codex mcp get neo4j-memory`
3. ✅ Запустить тест: `bash scripts/ai/mcp/check.sh`
4. ✅ Открыть Neo4j Browser: http://localhost:7474/browser/

## Связанные Документы

- [Neo4j Memory Configuration](./neo4j-memory-setup.md) - Детальная конфигурация памяти
- [MCP Configuration](./NEO4J-MCP-INDEX.md) - Обзор MCP конфигурации
- Neo4j Official: https://neo4j.com/docker/
