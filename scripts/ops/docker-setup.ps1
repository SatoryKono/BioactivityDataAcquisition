# Canonical Docker setup entrypoint for BioETL.
# Запускает основной стек, мониторинг и MCP серверы.

param(
    [string]$Mode = "full",  # full, basic, monitoring, mcp
    [switch]$AllowEnvFileCreate
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

Write-Host "🐳 BioETL Docker Setup" -ForegroundColor Green
Write-Host ""

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker не установлен" -ForegroundColor Red
    exit 1
}

try {
    $dockerPs = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker не запущен или не доступен" -ForegroundColor Red
        Write-Host "   Запустите Docker Desktop и повторите попытку" -ForegroundColor Yellow
        exit 1
    }
}
catch {
    Write-Host "❌ Docker не доступен: $_" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Docker доступен" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path ".env")) {
    if ($AllowEnvFileCreate -or $env:BIOETL_ALLOW_ENV_FILE_CREATE -eq "1") {
        if (-not (Test-Path ".env.example")) {
            Write-Host "❌ .env.example не найден; .env не создан" -ForegroundColor Red
            exit 2
        }
        Write-Host "⚠ .env файл не найден; явный opt-in разрешает создание из примера" -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "✓ Создан .env файл (отредактируйте перед запуском с секретами)" -ForegroundColor Green
    }
    else {
        Write-Host "❌ .env файл не найден" -ForegroundColor Red
        Write-Host "   Guardrail: Docker helper не создает .env автоматически." -ForegroundColor Yellow
        Write-Host "   Создайте его вручную после явного решения: Copy-Item .env.example .env" -ForegroundColor Yellow
        Write-Host "   Или запустите с явным opt-in: .\scripts\ops\docker-setup.ps1 -AllowEnvFileCreate" -ForegroundColor Yellow
        exit 2
    }
}

function Start-MainStack {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "1️⃣  Основной стек (Neo4j + BioETL)" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    $running = docker compose ps 2>&1 | Select-String "bioetl-neo4j|bioetl-app"
    if ($running) {
        Write-Host "⚠ Контейнеры уже запущены" -ForegroundColor Yellow
        docker compose ps
    }
    else {
        Write-Host "Запускаю основной стек..." -ForegroundColor Blue
        docker compose up -d
        Write-Host "✓ Основной стек запущен" -ForegroundColor Green
        Write-Host ""
        Write-Host "Сервисы:" -ForegroundColor Cyan
        Write-Host "  • Neo4j Browser: http://localhost:7474"
        Write-Host "  • BioETL: http://localhost:8081"
    }
}

function Start-Monitoring {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "2️⃣  Мониторинг (Prometheus, Grafana, Loki)" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "Запускаю мониторинг..." -ForegroundColor Blue
    docker compose -f docker-compose.monitoring.yml up -d
    Write-Host "✓ Мониторинг запущен" -ForegroundColor Green
    Write-Host ""
    Write-Host "Сервисы:" -ForegroundColor Cyan
    Write-Host "  • Grafana: http://localhost:3000 (admin/changeme)"
    Write-Host "  • Prometheus: http://localhost:9090"
    Write-Host "  • Loki: http://localhost:3100"
    Write-Host "  • Tempo: http://localhost:3200"
}

function Start-MCP {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "3️⃣  MCP Серверы для Codex" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "Запускаю MCP серверы..." -ForegroundColor Blue
    docker compose -f docker-compose.codex.yml up -d
    Write-Host "✓ MCP серверы запущены" -ForegroundColor Green
    Write-Host ""
    Write-Host "Серверы:" -ForegroundColor Cyan
    Write-Host "  • bioetl-mcp-memory"
    Write-Host "  • bioetl-mcp-filesystem"
    Write-Host "  • bioetl-mcp-github"
    Write-Host "  • bioetl-mcp-fetch"
}

function Show-Status {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "✅ Статус контейнеров" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""

    docker compose ps
}

function Show-Help {
    Write-Host ""
    Write-Host "Использование Docker:" -ForegroundColor Cyan
    Write-Host "  docker compose up -d              # Запустить основной стек"
    Write-Host "  docker compose down               # Остановить основной стек"
    Write-Host "  docker compose logs -f            # Просмотр логов"
    Write-Host "  docker compose ps                 # Статус контейнеров"
    Write-Host ""
    Write-Host "Документация: docs/DOCKER_SETUP.md"
    Write-Host ""
}

switch ($Mode) {
    "full" {
        Start-MainStack
        Start-Monitoring
        Start-MCP
    }
    "basic" {
        Start-MainStack
    }
    "monitoring" {
        Start-Monitoring
    }
    "mcp" {
        Start-MCP
    }
    default {
        Write-Host "Неизвестный режим: $Mode" -ForegroundColor Red
        exit 1
    }
}

Show-Status
Show-Help
