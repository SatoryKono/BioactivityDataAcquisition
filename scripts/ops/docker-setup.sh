#!/bin/bash
# Canonical Docker setup entrypoint for BioETL.
# Запускает основной стек, мониторинг и MCP серверы.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "🐳 BioETL Docker Setup"
echo ""

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker не установлен"
    exit 1
fi

if ! docker ps >/dev/null 2>&1; then
    echo "❌ Docker не запущен или не доступен"
    exit 1
fi

echo "✓ Docker доступен"
echo ""

if [ ! -f .env ]; then
    if [ "${BIOETL_ALLOW_ENV_FILE_CREATE:-}" = "1" ]; then
        if [ ! -f .env.example ]; then
            echo "❌ .env.example не найден; .env не создан"
            exit 2
        fi
        echo "⚠ .env файл не найден; BIOETL_ALLOW_ENV_FILE_CREATE=1 разрешает создание из примера"
        cp .env.example .env
        echo "✓ Создан .env файл (отредактируйте перед запуском с секретами)"
    else
        echo "❌ .env файл не найден"
        echo "   Guardrail: Docker helper не создает .env автоматически."
        echo "   Создайте его вручную после явного решения: cp .env.example .env"
        echo "   Или запустите с явным opt-in: BIOETL_ALLOW_ENV_FILE_CREATE=1 scripts/ops/docker-setup.sh"
        exit 2
    fi
fi

echo ""
echo "=========================================="
echo "1️⃣  Основной стек (Neo4j + BioETL)"
echo "=========================================="
echo ""

if docker compose ps | grep -q "bioetl-neo4j\|bioetl-app"; then
    echo "⚠ Контейнеры уже запущены"
    docker compose ps
else
    echo "Запускаю основной стек..."
    docker compose up -d
    echo ""
    echo "✓ Основной стек запущен"
    echo ""
    echo "Сервисы:"
    echo "  • Neo4j Browser: http://localhost:7474"
    echo "  • BioETL: http://localhost:8081"
    echo ""
fi

echo ""
echo "=========================================="
echo "2️⃣  Мониторинг (Prometheus, Grafana, Loki)"
echo "=========================================="
echo ""

read -p "Запустить мониторинг? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Запускаю мониторинг..."
    docker compose -f docker-compose.monitoring.yml up -d
    echo ""
    echo "✓ Мониторинг запущен"
    echo ""
    echo "Сервисы:"
    echo "  • Grafana: http://localhost:3000 (admin/changeme)"
    echo "  • Prometheus: http://localhost:9090"
    echo "  • Loki: http://localhost:3100"
    echo "  • Tempo: http://localhost:3200"
else
    echo "Пропущен"
fi

echo ""
echo "=========================================="
echo "3️⃣  MCP Серверы для Codex"
echo "=========================================="
echo ""

read -p "Запустить MCP серверы? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Запускаю MCP серверы..."
    docker compose -f docker-compose.codex.yml up -d
    echo ""
    echo "✓ MCP серверы запущены"
    echo ""
    echo "Серверы:"
    echo "  • bioetl-mcp-memory"
    echo "  • bioetl-mcp-filesystem"
    echo "  • bioetl-mcp-github"
    echo "  • bioetl-mcp-fetch"
else
    echo "Пропущены"
fi

echo ""
echo "=========================================="
echo "✅ Статус контейнеров"
echo "=========================================="
echo ""

docker compose ps

echo ""
echo "Использование Docker:"
echo "  docker compose up -d              # Запустить основной стек"
echo "  docker compose down               # Остановить основной стек"
echo "  docker compose logs -f            # Просмотр логов"
echo "  docker compose ps                 # Статус контейнеров"
echo ""
echo "Документация: docs/DOCKER_SETUP.md"
echo ""
