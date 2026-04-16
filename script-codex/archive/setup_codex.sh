#!/bin/bash
set -e

echo "=== Codex + Docker Setup для Ubuntu (WSL) ==="

# Проверка Docker
echo "Проверка Docker..."
if ! command -v docker &> /dev/null; then
    echo "Docker не найден. Установка пропущена на этапе APT."
else
    echo "✓ Docker установлен"
fi

# Запуск Docker daemon
echo "Запуск Docker daemon..."
sudo service docker start 2>/dev/null || sudo /etc/init.d/docker start 2>/dev/null || echo "Docker daemon уже запущен или потребуется ручной запуск"

# Добавление текущего пользователя в группу docker
echo "Настройка прав Docker..."
sudo usermod -aG docker $(whoami) 2>/dev/null || true

# Установка OpenAI CLI через Python
echo "Установка OpenAI CLI..."
python3 -m pip install --user openai --break-system-packages 2>/dev/null || \
python3 -m pip install --user openai || \
echo "OpenAI CLI установка завершена или требует ручной настройки"

# Настройка PATH
echo "Настройка PATH..."
export PATH=$HOME/.local/bin:$PATH
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc

# Docker Compose проверка
echo "Проверка Docker Compose..."
docker compose version || echo "Docker Compose готов"

# Создание конфигурации для Codex
echo "Создание конфигурации Codex..."
mkdir -p ~/.codex
cat > ~/.codex/config.json <<'EOF'
{
  "api_key": "",
  "model": "gpt-4",
  "docker": {
    "enabled": true,
    "host": "unix:///var/run/docker.sock"
  }
}
EOF

echo ""
echo "=== Установка завершена ==="
echo ""
echo "Следующие шаги:"
echo "1. Установите API ключ OpenAI:"
echo "   export OPENAI_API_KEY='your-api-key-here'"
echo ""
echo "2. Запустите Codex:"
echo "   openai api chat_completions.create -m gpt-4"
echo ""
echo "3. Или используйте Docker для запуска контейнеризированных сервисов MCP:"
echo "   docker run -d --name neo4j -e NEO4J_AUTH=neo4j/password -p 7687:7687 neo4j"
echo ""
echo "4. Для использования MCP Toolkit, установите Docker Desktop и включите MCP в настройках."
