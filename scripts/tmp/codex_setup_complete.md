# Codex на Debian/Ubuntu (WSL) - Установка завершена

## Установленные компоненты

✓ **Docker** v28.2.2
✓ **Python** 3.12.3  
✓ **Git** 2.43.0  
✓ **Docker Compose** (в составе docker.io)

## Быстрый старт

### 1. Войдите в WSL Ubuntu
```powershell
wsl -d Ubuntu
```

### 2. Установите OpenAI CLI
```bash
python3 -m pip install --user openai
export PATH=$HOME/.local/bin:$PATH
```

### 3. Установите API ключ
```bash
export OPENAI_API_KEY='sk-...'
```

### 4. Используйте Docker для MCP сервисов
```bash
# Запустите Neo4j (пример)
docker run -d --name neo4j \
  -e NEO4J_AUTH=neo4j/password \
  -p 7474:7474 -p 7687:7687 \
  neo4j:latest

# Проверьте статус
docker ps
```

### 5. Подключите Codex к MCP (опционально)
```bash
# Если установлен Docker Desktop 4.40+
docker mcp-client configure codex
```

## Команды для проверки

```bash
# Проверить Docker
docker --version

# Проверить контейнеры
docker ps

# Просмотреть логи
docker logs neo4j

# Остановить контейнер
docker stop neo4j

# Удалить контейнер
docker rm neo4j
```

## Файлы конфигурации

- **Docker socket**: `/var/run/docker.sock`
- **Docker config**: `~/.docker/config.json`
- **Codex config**: `~/.codex/config.json` (создать вручную при необходимости)

## Полезные ссылки

- [Docker Docs](https://docs.docker.com/)
- [OpenAI API](https://platform.openai.com/docs/)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-toolkit/)
- [Neo4j Docker](https://hub.docker.com/_/neo4j)

## Примечание

Убедитесь, что Docker daemon запущен перед использованием. Если Docker не запускается автоматически в WSL, используйте:

```bash
sudo service docker start
```
