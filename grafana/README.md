# BioETL Мониторинг: Prometheus + Grafana

**Версия документа:** 2.0.0
**Дата обновления:** 2026-02-22
**Статус:** Production Ready
**Совместимость:** BioETL v5.21+, Grafana 9+, Prometheus 2.40+

---

## Содержание

1. [Архитектура мониторинга](#1-архитектура-мониторинга)
2. [Цепочка данных: от кода до графика](#2-цепочка-данных-от-кода-до-графика)
3. [Быстрый запуск](#3-быстрый-запуск)
4. [Конфигурация инфраструктуры](#4-конфигурация-инфраструктуры)
5. [Полный каталог метрик BioETL](#5-полный-каталог-метрик-bioetl)
6. [Переменные фильтрации (Template Variables)](#6-переменные-фильтрации-template-variables)
7. [Дашборд: BioETL Simple](#7-дашборд-bioetl-simple)
8. [Дашборд: BioETL Overview v1](#8-дашборд-bioetl-overview-v1)
9. [Дашборд: BioETL Overview v2](#9-дашборд-bioetl-overview-v2)
10. [Дашборд: BioETL Data Quality v1](#10-дашборд-bioetl-data-quality-v1)
11. [Дашборд: BioETL Data Quality v2](#11-дашборд-bioetl-data-quality-v2)
12. [Дашборд: BioETL Provider Health v1](#12-дашборд-bioetl-provider-health-v1)
13. [Дашборд: BioETL Provider Health v2](#13-дашборд-bioetl-provider-health-v2)
14. [Справочник PromQL-паттернов](#14-справочник-promql-паттернов)
15. [Устранение неполадок](#15-устранение-неполадок)
16. [Архитектурные решения и обоснования](#16-архитектурные-решения-и-обоснования)
17. [Подробный разбор типов метрик Prometheus](#17-подробный-разбор-типов-метрик-prometheus)
18. [Medallion Architecture и метрики](#18-medallion-architecture-и-метрики)
19. [Circuit Breaker и мониторинг провайдеров](#19-circuit-breaker-и-мониторинг-провайдеров)
20. [Data Quality Monitor (DQMonitorPort)](#20-data-quality-monitor-dqmonitorport)
21. [Rate Limiting и его мониторинг](#21-rate-limiting-и-его-мониторинг)
22. [Рекомендации по созданию пользовательских дашбордов](#22-рекомендации-по-созданию-пользовательских-дашбордов)
23. [FAQ (Часто задаваемые вопросы)](#23-faq-часто-задаваемые-вопросы)
24. [Alerting (Настройка оповещений)](#24-alerting-настройка-оповещений)
25. [Глоссарий](#25-глоссарий)
26. [Сводная таблица дашбордов](#26-сводная-таблица-дашбордов)
27. [Жизненный цикл метрики: от кода до графика](#27-жизненный-цикл-метрики-от-кода-до-графика)
28. [Безопасность и production-конфигурация](#28-безопасность-и-production-конфигурация)
29. [Интеграция с CI/CD](#29-интеграция-с-cicd)

---

> Примечание: в репозитории сейчас поставляются только `bioetl-simple.json` и `*-v2.json` дашборды.
> Разделы про v1 ниже сохранены как историческая/справочная документация.

## 1. Архитектура мониторинга

### 1.1 Обзор

Система мониторинга BioETL построена по модели Pull (Prometheus scraping) и состоит из трёх компонентов, работающих в связке:

```
┌──────────────────────────────────────────────────────────────────┐
│                      BioETL Application                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Domain Layer (Ports)                                    │    │
│  │  ┌───────────┐  ┌────────────┐  ┌──────────────────┐   │    │
│  │  │MetricsPort│  │TracingPort │  │DQMonitorPort     │   │    │
│  │  │ (Protocol)│  │ (Protocol) │  │ (Protocol)       │   │    │
│  │  └─────┬─────┘  └──────┬─────┘  └────────┬─────────┘   │    │
│  └────────┼───────────────┼──────────────────┼─────────────┘    │
│           │               │                  │                   │
│  ┌────────┼───────────────┼──────────────────┼─────────────┐    │
│  │  Infrastructure Layer (Adapters)                         │    │
│  │  ┌─────┴──────────┐ ┌──┴──────────┐ ┌────┴───────────┐ │    │
│  │  │Prometheus      │ │NoOpTracing  │ │DataQuality     │ │    │
│  │  │Metrics         │ │             │ │Monitor         │ │    │
│  │  │(prometheus_    │ │(ADR-022)    │ │(anomaly.py)    │ │    │
│  │  │ client lib)    │ │             │ │                │ │    │
│  │  └─────┬──────────┘ └─────────────┘ └────────────────┘ │    │
│  └────────┼────────────────────────────────────────────────┘    │
│           │                                                      │
│  ┌────────┴────────────────────────────────────────────────┐    │
│  │  Metrics HTTP Server (server.py)                         │    │
│  │  prometheus_client.start_http_server(port=8000)          │    │
│  │  Формат: text/plain; version=0.0.4 (Prometheus exposition)│   │
│  └────────┬────────────────────────────────────────────────┘    │
└───────────┼──────────────────────────────────────────────────────┘
            │
            │  HTTP GET /metrics (каждые 15 секунд)
            │
┌───────────┴──────────────────────────────────────────────────────┐
│  Prometheus Server (порт 9090)                                   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  TSDB (Time-Series Database)                              │    │
│  │  - Хранит все time series с timestamps                    │    │
│  │  - Retention: по умолчанию 15 дней                        │    │
│  │  - Persistent volume: prometheus-data                     │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Конфигурация: grafana/prometheus.yml                            │
│  - scrape_interval: 15s                                          │
│  - target: host.docker.internal:8000                             │
└───────────┬──────────────────────────────────────────────────────┘
            │
            │  PromQL запросы (HTTP API)
            │
┌───────────┴──────────────────────────────────────────────────────┐
│  Grafana Server (порт 3000)                                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Provisioning (автоматическая загрузка)                    │    │
│  │  - Datasource: Prometheus (prometheus.yml)                │    │
│  │  - Dashboards: 4 JSON файлов (bioetl.yaml)               │    │
│  │  - Обновление каждые 30 секунд                            │    │
│  │  - allowUiUpdates: true                                   │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Дашборды (shipped):                                             │
│  - BioETL Simple (bioetl-simple)                                 │
│  - BioETL Overview v2 (bioetl-overview-v2)                       │
│  - BioETL Data Quality v2 (bioetl-dq-v2)                         │
│  - BioETL Provider Health v2 (bioetl-provider-health-v2)         │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Принципы проектирования

Observability-подсистема BioETL следует принципам Hexagonal Architecture (ADR-017):

- **MetricsPort** (Protocol) определён в domain-слое (`src/bioetl/domain/ports/observability.py`). Это контракт, не знающий о конкретной реализации. MetricsPort предоставляет три метода: `observe_histogram()`, `increment_counter()`, `set_gauge()`.

- **PrometheusMetrics** (Adapter) реализует MetricsPort в infrastructure-слое (`src/bioetl/infrastructure/observability/prometheus_metrics.py`). Использует библиотеку `prometheus_client` для создания и экспорта метрик.

- **NoOpMetrics** — Null Object реализация MetricsPort (`src/bioetl/infrastructure/observability/noop_metrics.py`). Используется когда метрики отключены (`BIOETL_METRICS_ENABLED=false`). Все вызовы становятся no-op без каких-либо побочных эффектов.

- **Composition Root** собирает зависимости в `src/bioetl/composition/bootstrap/runtime/observability.py`. Функция `bootstrap_metrics_port(settings)` создаёт PrometheusMetrics или NoOpMetrics в зависимости от настроек. Функция `maybe_start_metrics_server(settings)` запускает HTTP-сервер для экспорта метрик.

Такая архитектура обеспечивает:
- Application и Domain код не зависит от Prometheus.
- Переключение на другой бэкенд (StatsD, CloudWatch) требует только новый Adapter и изменение wiring в Composition Root.
- В тестах можно подставить NoOpMetrics или мок, не трогая бизнес-логику.

### 1.3 Файловая структура

```
grafana/
├── README.md                          # Этот документ
├── prometheus.yml                     # Конфигурация Prometheus scraper
├── provisioning/
│   ├── datasources/
│   │   └── prometheus.yml             # Datasource: Prometheus → Grafana
│   └── dashboards/
│       └── bioetl.yaml                # Dashboard provisioning config
└── dashboards/
    ├── bioetl-simple.json             # Минимальный live-дашборд
    ├── bioetl-overview-v2.json        # Обзор для последнего запуска (v2)
    ├── bioetl-dq-v2.json              # Data Quality для последнего запуска (v2)
    └── bioetl-provider-health-v2.json # Здоровье провайдеров (v2)

docker-compose.monitoring.yml          # Docker Compose для стека мониторинга

src/bioetl/
├── domain/ports/observability.py      # MetricsPort, TracingPort, LoggerPort (Protocols)
└── infrastructure/observability/
    ├── metrics.py                     # Определения всех Prometheus метрик (Counter, Histogram, Gauge)
    ├── prometheus_metrics.py          # PrometheusMetrics adapter (реализация MetricsPort)
    ├── server.py                      # HTTP-сервер для /metrics endpoint
    ├── noop_metrics.py                # NoOpMetrics (Null Object)
    └── anomaly.py                     # DataQualityMonitor (реализация DQMonitorPort)
```

---

## 2. Цепочка данных: от кода до графика

### 2.1 Шаг 1: Определение метрик в коде

Все метрики определены как глобальные объекты `prometheus_client` в файле `src/bioetl/infrastructure/observability/metrics.py`. Каждая метрика имеет:

- **Имя** (с префиксом `bioetl_`) — глобально уникальный идентификатор в формате Prometheus.
- **Описание** — человекочитаемое описание метрики.
- **Labels** (лейблы) — набор ключей для мультидименсиональной фильтрации.
- **Тип** — Counter (монотонно растёт), Histogram (распределение значений), Gauge (произвольное значение).

Пример определения Counter-метрики:

```python
# src/bioetl/infrastructure/observability/metrics.py

RECORDS_PROCESSED_TOTAL = Counter(
    "bioetl_records_processed_total",            # Имя в Prometheus
    "Total number of records processed",          # Описание
    ["pipeline", "stage", "run_type"],            # Labels
)
```

Пример определения Histogram-метрики с пользовательскими бакетами:

```python
ADAPTER_REQUEST_DURATION_SECONDS = Histogram(
    "bioetl_adapter_request_duration_seconds",
    "Duration of adapter API requests in seconds",
    ["provider", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)
```

### 2.2 Шаг 2: Запись значений через MetricsPort

Application-код использует MetricsPort (Protocol) для записи метрик. Вот как это выглядит в пайплайне:

```python
# Где-то в application-слое (упрощённо):

# Инкремент counter
self._metrics.increment_counter(
    "records_processed_total",
    value=batch_size,
    labels={"pipeline": "chembl", "stage": "bronze", "run_type": "incremental"},
)

# Запись длительности в histogram
self._metrics.observe_histogram(
    "pipeline_duration_seconds",
    value=elapsed_seconds,
    labels={"pipeline": "chembl", "stage": "fetch", "status": "success", "run_type": "incremental"},
)

# Установка gauge
self._metrics.set_gauge(
    "circuit_breaker_state",
    value=0,  # 0=closed
    labels={"adapter": "chembl"},
)
```

`PrometheusMetrics` (adapter) маппит строковое имя метрики на соответствующий Prometheus-объект через словари `HISTOGRAMS`, `COUNTERS`, `GAUGES`:

```python
# src/bioetl/infrastructure/observability/prometheus_metrics.py

class PrometheusMetrics(MetricsPort):
    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
        if name in COUNTERS:
            COUNTERS[name].labels(**labels).inc(value)
```

### 2.3 Шаг 3: Экспорт через HTTP-сервер

При запуске пайплайна `server.py` поднимает HTTP-сервер на порту 8000 (настраивается через `BIOETL_METRICS_PORT`):

```python
# src/bioetl/infrastructure/observability/server.py
from prometheus_client import start_http_server

def start_metrics_server(port: int = 8000, addr: str = "0.0.0.0", ...) -> bool:
    start_http_server(port, addr=addr)
```

Сервер отдаёт метрики в формате Prometheus exposition (`text/plain; version=0.0.4`). Пример ответа на `GET http://localhost:8000/metrics`:

```
# HELP bioetl_records_processed_total Total number of records processed by the pipeline
# TYPE bioetl_records_processed_total counter
bioetl_records_processed_total{pipeline="chembl",stage="bronze",run_type="incremental"} 15420.0
bioetl_records_processed_total{pipeline="chembl",stage="silver",run_type="incremental"} 15380.0
bioetl_records_processed_total{pipeline="chembl",stage="gold",run_type="incremental"} 15102.0
bioetl_records_processed_total{pipeline="chembl",stage="quarantined",run_type="incremental"} 278.0

# HELP bioetl_pipeline_duration_seconds Duration of pipeline runs in seconds
# TYPE bioetl_pipeline_duration_seconds histogram
bioetl_pipeline_duration_seconds_bucket{le="0.005",pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 0.0
bioetl_pipeline_duration_seconds_bucket{le="0.01",pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 0.0
...
bioetl_pipeline_duration_seconds_sum{pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 127.45
bioetl_pipeline_duration_seconds_count{pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 3.0
```

Особенности HTTP-сервера:
- Запускается в daemon-потоке (не блокирует основной процесс).
- Thread-safe: `prometheus_client` гарантирует потокобезопасность.
- Если порт занят (`EADDRINUSE`), поведение зависит от `fail_fast`: при `true` бросает `MetricsServerError`, при `false` тихо продолжает работу без метрик.
- Поддерживает retry с экспоненциальным backoff (до 3 попыток по умолчанию).
- Идемпотентный запуск: второй вызов `start_metrics_server()` — no-op.

### 2.4 Шаг 4: Prometheus scraping

Prometheus скрейпит endpoint `/metrics` каждые 15 секунд (настраивается в `grafana/prometheus.yml`):

```yaml
# grafana/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'bioetl'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: /metrics
```

`host.docker.internal` — специальный DNS, резолвящийся на хост-машину из Docker-контейнера. На Windows и macOS работает из коробки. На Linux может потребоваться `--add-host=host.docker.internal:host-gateway`.

Prometheus сохраняет каждый скрейп как набор time series (метрика + labels + timestamp + value) в локальную TSDB. Данные хранятся в Docker volume `prometheus-data` и переживают перезапуск контейнера.

### 2.5 Шаг 5: Grafana visualization

Grafana подключается к Prometheus как datasource и выполняет PromQL-запросы для визуализации данных:

```yaml
# grafana/provisioning/datasources/prometheus.yml
datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus
    access: proxy
    url: http://prometheus:9090    # Внутри Docker network
    isDefault: true
    editable: true
    jsonData:
      timeInterval: 15s
```

Дашборды провизионируются автоматически при старте Grafana:

```yaml
# grafana/provisioning/dashboards/bioetl.yaml
providers:
  - name: 'BioETL'
    orgId: 1
    folder: 'BioETL'
    folderUid: 'bioetl'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30       # Проверяет изменения каждые 30 сек
    allowUiUpdates: true            # Можно редактировать через UI
    options:
      path: /var/lib/grafana/dashboards   # Mount point из docker-compose
```

---

## 3. Быстрый запуск

### 3.1 Запуск стека мониторинга

```bash
# Запуск базового стека метрик
make monitoring-up

# Или напрямую:
docker compose -f docker-compose.monitoring.yml up -d

# Запуск расширенного профиля с трассировкой и лог-корреляцией
docker compose -f docker-compose.monitoring.yml --profile tracing up -d

# Проверка статуса контейнеров
docker compose -f docker-compose.monitoring.yml ps

# Просмотр логов
make monitoring-logs

# Остановка
make monitoring-down
```

### 3.2 Запуск пайплайна с метриками

```bash
# Убедитесь, что в .env:
# BIOETL_METRICS_ENABLED=true
# BIOETL_METRICS_PORT=8000
# BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED=true

# Запуск пайплайна
make run-local
# или: bioetl run --pipeline chembl-activity
```

### 3.3 Проверка работоспособности

```bash
# 1. Проверить метрики приложения
curl -s http://localhost:8000/metrics | grep bioetl_

# 2. Проверить Prometheus targets
# Открыть http://localhost:9090/targets — target должен быть "UP"

# 3. Открыть Grafana
# http://localhost:3000 (admin/admin)
# Перейти: Home → Dashboards → BioETL → выбрать дашборд
```

### 3.4 Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|---|---|---|
| `BIOETL_METRICS_ENABLED` | `true` | Включить/выключить сбор метрик |
| `BIOETL_METRICS_PORT` | `8000` | Порт HTTP-сервера метрик |
| `BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED` | `true` | Запускать ли HTTP-сервер |
| `BIOETL_OBSERVABILITY__METRICS_FAIL_FAST` | `false` | Падать при ошибке запуска сервера |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_COUNT` | `3` | Количество попыток запуска (1-10) |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_DELAY` | `1.0` | Задержка между попытками (0.1-10.0 с) |
| `GF_SECURITY_ADMIN_PASSWORD` | `admin` | Пароль администратора Grafana |
| `BIOETL_OBSERVABILITY__TRACING_ENABLED` | `false` | Включить OpenTelemetry spans и log-trace correlation |

---

## 4. Конфигурация инфраструктуры

### 4.1 Docker Compose (`docker-compose.monitoring.yml`)

Базовый стек состоит из трёх сервисов, объединённых в bridge-сеть `monitoring`:

**Prometheus:**
- Image: `prom/prometheus:latest`
- Container: `bioetl-prometheus`
- Порт: `9090:9090`
- Volumes:
  - `./grafana/prometheus.yml` → `/etc/prometheus/prometheus.yml` (конфигурация, read-only)
  - `prometheus-data` → `/prometheus` (persistent TSDB данные)
- Restart: `unless-stopped`

**Grafana:**
- Image: `grafana/grafana:latest`
- Container: `bioetl-grafana`
- Порт: `3000:3000`
- Volumes:
  - `grafana-data` → `/var/lib/grafana` (persistent данные Grafana)
  - `./grafana/provisioning/datasources` → `/etc/grafana/provisioning/datasources` (read-only)
  - `./grafana/provisioning/dashboards` → `/etc/grafana/provisioning/dashboards` (read-only)
  - `./grafana/dashboards` → `/var/lib/grafana/dashboards` (read-only, JSON-дашборды)
- Restart: `unless-stopped`

**Pushgateway:**
- Image: `prom/pushgateway:latest`
- Container: `bioetl-pushgateway`
- Порт: `9091:9091`
- Restart: `unless-stopped`

Опциональный профиль `tracing` добавляет:

- `Loki` на `:3100` для поиска по структурированным логам
- `Promtail` для ingestion локальных `logs/*.log` и `logs/*.jsonl`
- `Tempo` на `:3200` и OTLP gRPC `:4317` для trace storage
- дополнительные Grafana datasources `Loki` и `Tempo`

### 4.2 Сетевая топология

```
Host Machine (Windows/macOS/Linux)
├── BioETL App           → localhost:8000 (/metrics)
│
└── Docker
    └── Network: monitoring (bridge)
        ├── bioetl-prometheus → :9090  (scrapes host.docker.internal:8000)
        ├── bioetl-pushgateway → :9091
        ├── bioetl-grafana    → :3000  (queries prometheus:9090)
        ├── bioetl-loki       → :3100  (optional, tracing profile)
        ├── bioetl-promtail   → :9080  (optional, tracing profile)
        └── bioetl-tempo      → :3200/:4317 (optional, tracing profile)
```

Внутри Docker-сети Grafana обращается к Prometheus по имени сервиса `prometheus` (порт 9090). Prometheus скрейпит BioETL-приложение на хосте через `host.docker.internal:8000`.

### 4.3 URL и порты

| Компонент | URL | Порт | Назначение |
|---|---|---|---|
| BioETL Metrics | `http://localhost:8000/metrics` | 8000 | Prometheus exposition format |
| Prometheus UI | `http://localhost:9090` | 9090 | Query interface, target status |
| Prometheus Targets | `http://localhost:9090/targets` | 9090 | Статус scrape targets |
| Prometheus API | `http://localhost:9090/api/v1/...` | 9090 | HTTP API для PromQL |
| Pushgateway | `http://localhost:9091` | 9091 | Push endpoint для ad-hoc/ephemeral jobs |
| Grafana UI | `http://localhost:3000` | 3000 | Дашборды, логин: admin/admin |
| Grafana Explore | `http://localhost:3000/explore` | 3000 | Ad-hoc PromQL запросы |
| Grafana Dashboards | `http://localhost:3000/dashboards` | 3000 | Список дашбордов |
| Loki API | `http://localhost:3100` | 3100 | Log query/search backend |
| Tempo API | `http://localhost:3200` | 3200 | Trace query backend |
| Tempo OTLP gRPC | `localhost:4317` | 4317 | Trace ingestion endpoint |

---

## 5. Полный каталог метрик BioETL

Все метрики определены в `src/bioetl/infrastructure/observability/metrics.py`.

Каждая метрика автоматически получает префикс `bioetl_` от Prometheus. Для Histogram-метрик Prometheus автоматически создаёт суффиксы: `_bucket` (бакеты распределения), `_sum` (сумма всех наблюдений), `_count` (количество наблюдений), `_created` (timestamp создания). Для Counter-метрик автоматически создаётся `_total` суффикс и `_created` timestamp.

### 5.1 Pipeline Metrics (основные метрики пайплайна)

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_pipeline_duration_seconds` | Histogram | `pipeline`, `stage`, `status`, `run_type` | Длительность выполнения стадий пайплайна в секундах. Status: success/failure. |
| `bioetl_records_processed_total` | Counter | `pipeline`, `stage`, `run_type` | Суммарное количество обработанных записей. Stage: bronze, silver, gold, quarantined. |
| `bioetl_errors_total` | Counter | `pipeline`, `stage`, `error_code` | Суммарное количество ошибок. Error_code — машиночитаемый код ошибки. |
| `bioetl_batch_size_records` | Histogram | `pipeline`, `stage` | Распределение размеров батчей (количество записей). Buckets: 100, 500, 1K, 5K, 10K, 50K. |
| `bioetl_pipeline_runs_total` | Counter | `pipeline`, `run_type`, `status` | Количество запусков пайплайна. Run_type: incremental, backfill, rebuild. |
| `bioetl_phase_duration_seconds` | Histogram | `pipeline`, `phase`, `status` | Длительность фаз жизненного цикла пайплайна (fetch, transform, load). |

### 5.2 Input Filter Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_filter_ids_loaded_total` | Counter | `pipeline`, `source_file` | Количество уникальных ID, загруженных из фильтра. |
| `bioetl_filter_ids_duplicates_total` | Counter | `pipeline`, `source_file` | Количество дубликатов, найденных в фильтре. |
| `bioetl_filter_combinations_loaded_total` | Counter | `pipeline`, `source_file` | Количество загруженных комбинаций из мульти-фильтра. |

### 5.3 Data Quality Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_dq_records_quarantined_total` | Counter | `pipeline`, `error_type`, `run_type` | Количество записей, отправленных на карантин из-за проблем качества. |
| `bioetl_dq_validation_score` | Gauge | `pipeline`, `entity` | Оценка качества данных (0.0-1.0, где 1.0 = все записи валидны). |
| `bioetl_data_freshness_seconds` | Gauge | `pipeline`, `entity` | Секунды с момента последнего успешного ingestion для pipeline/entity. |
| `bioetl_dq_anomaly_detected` | Counter | `pipeline`, `metric`, `severity`, `anomaly_type` | Количество обнаруженных аномалий качества данных. |
| `bioetl_dq_check_duration_ms` | Histogram | `pipeline` | Длительность проверок качества данных в миллисекундах. |
| `bioetl_dq_baseline_updated` | Counter | `pipeline`, `metric` | Количество обновлений baseline для DQ монитора. |
| `bioetl_dq_baseline_samples` | Gauge | `pipeline`, `metric` | Текущее количество samples в baseline DQ. |
| `bioetl_dq_soft_threshold_exceeded` | Counter | `pipeline` | Количество превышений мягкого порога DQ. |

### 5.4 Circuit Breaker Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_circuit_breaker_state` | Gauge | `adapter` | Текущее состояние circuit breaker: 0=closed (здоров), 1=half-open (проверка), 2=open (отключён). |
| `bioetl_circuit_breaker_trips_total` | Counter | `adapter` | Количество срабатываний (переходов в open). |
| `bioetl_circuit_breaker_success_total` | Counter | `adapter` | Количество успешных вызовов через circuit breaker. |
| `bioetl_circuit_breaker_failure_total` | Counter | `adapter` | Количество неуспешных вызовов через circuit breaker. |

### 5.5 Health Check Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_pipeline_health_check_passed` | Gauge | `pipeline`, `component` | Статус health check компонента (1=passed, 0=failed). |
| `bioetl_infrastructure_validated` | Gauge | `pipeline`, `run_id` | Статус валидации инфраструктуры (1=validated, 0=not). |
| `bioetl_health_check_duration_seconds` | Histogram | `pipeline` | Длительность health check операций в секундах. |
| `bioetl_health_check_status` | Gauge | `component` | Статус здоровья компонента: 0=unknown, 1=healthy, 2=degraded. |
| `bioetl_health_check_latency_ms` | Histogram | `provider` | Латентность health check в миллисекундах. |
| `bioetl_health_check_latency_seconds` | Histogram | `provider` | Латентность health check в секундах. |
| `bioetl_health_check_success_total` | Counter | `provider` | Количество успешных health check. |
| `bioetl_health_check_failures_total` | Counter | `provider` | Количество неуспешных health check. |
| `bioetl_preflight_medallion_policy_valid` | Gauge | `pipeline`, `run_id` | Валидность medallion policy (1=valid, 0=invalid). |
| `bioetl_preflight_config_errors_total` | Gauge | `pipeline`, `run_id` | Количество ошибок конфигурации при preflight. |

### 5.6 Adapter / HTTP Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_adapter_request_duration_seconds` | Histogram | `provider`, `endpoint` | Длительность API-запросов адаптера в секундах. Buckets: 0.05-30s. |
| `bioetl_adapter_requests_total` | Counter | `provider`, `endpoint`, `status` | Количество API-запросов адаптера. |
| `bioetl_adapter_batch_size` | Histogram | `provider`, `endpoint` | Распределение размеров ответов адаптера. |
| `bioetl_adapter_dropped_duplicates_total` | Counter | `provider`, `entity_type` | Количество дубликатов, удалённых адаптером. |
| `bioetl_data_source_retries_total` | Counter | `provider`, `operation` | Количество retry-попыток для data source. |
| `bioetl_data_source_retry_exhausted_total` | Counter | `provider`, `operation` | Количество исчерпанных retry-попыток. |
| `bioetl_http_request_duration_seconds` | Histogram | `provider`, `method`, `status` | Длительность HTTP-запросов в секундах. |
| `bioetl_http_retries_total` | Counter | `provider`, `method` | Количество HTTP retry-попыток. |
| `bioetl_http_request_errors_total` | Counter | `provider`, `method`, `error_type` | Количество HTTP-ошибок. |
| `bioetl_provider_health_status` | Gauge | `provider` | Статус здоровья провайдера: 0=unknown, 1=healthy, 2=degraded. |
| `bioetl_rate_limiter_tokens_available` | Gauge | `provider` | Текущее количество доступных токенов в rate limiter. |
| `bioetl_rate_limiter_wait_seconds` | Histogram | `provider` | Время ожидания в rate limiter. |

### 5.7 Transformer Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_transform_duration_seconds` | Histogram | `provider`, `entity_type` | Длительность трансформации данных в секундах. |
| `bioetl_transform_errors_total` | Counter | `provider`, `entity_type`, `error_type` | Количество ошибок трансформации. |

### 5.8 Storage Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_vacuum_files_removed_total` | Counter | `table`, `layer` | Количество файлов, удалённых vacuum-операциями. |
| `bioetl_vacuum_duration_seconds` | Histogram | `table` | Длительность vacuum-операций. |
| `bioetl_archive_files_total` | Counter | `table`, `target` | Количество заархивированных файлов. |
| `bioetl_archive_duration_seconds` | Histogram | `table` | Длительность архивации. |
| `bioetl_storage_optimization_total` | Counter | `pipeline`, `status` | Количество операций оптимизации хранилища. |
| `bioetl_bronze_write_duration_seconds` | Histogram | `provider`, `entity` | Длительность записи в Bronze-слой. |
| `bioetl_bronze_records_written_total` | Counter | `provider`, `entity` | Количество записей, записанных в Bronze. |
| `bioetl_bronze_bytes_written_total` | Counter | `provider`, `entity` | Количество байт, записанных в Bronze (compressed). |
| `bioetl_policy_violations_total` | Counter | `layer`, `mode` | Количество нарушений write policy. |
| `bioetl_silver_validation_failures_total` | Counter | `table` | Количество ошибок валидации Silver schema. |

### 5.9 Shutdown Metrics

| Метрика | Тип | Labels | Описание |
|---|---|---|---|
| `bioetl_shutdown_initiated` | Counter | `reason` | Количество инициаций завершения. |
| `bioetl_shutdown_completed` | Counter | `reason` | Количество завершённых shutdown. |

---

## 6. Переменные фильтрации (Template Variables)

Все дашборды поддерживают две template variables для динамической фильтрации данных. Переменные отображаются как выпадающие списки в верхней части дашборда.

### 6.1 `$pipeline`

- **Определение:** `label_values(bioetl_records_processed_total, pipeline)`
- **Тип:** Query (автоматическое обнаружение значений)
- **Multi-select:** Да (можно выбрать несколько пайплайнов)
- **Include All:** Да (`.*` — все пайплайны)
- **Refresh:** При загрузке дашборда
- **Возможные значения:** `chembl`, `pubmed`, `pubchem`, `uniprot` и другие pipeline-идентификаторы, зарегистрированные в системе.
- **Применение:** Фильтрует метрики по имени пайплайна. Используется практически во всех PromQL-запросах.

### 6.2 `$run_type`

- **Определение:** `label_values(bioetl_records_processed_total{pipeline=~"$pipeline"}, run_type)`
- **Тип:** Query (каскадная зависимость от `$pipeline`)
- **Multi-select:** Да
- **Include All:** Да
- **Refresh:** При загрузке дашборда
- **Возможные значения:**
  - `incremental` — инкрементальное обновление данных (только новые записи).
  - `backfill` — ретроспективное заполнение данных за прошлые периоды.
  - `rebuild` — полная пересборка данных с нуля.
- **Применение:** Фильтрует метрики по типу запуска. Доступен только на метриках, имеющих label `run_type` (основные pipeline-метрики).

**Каскадная зависимость:** Значения `$run_type` зависят от выбранного `$pipeline`. При смене пайплайна список доступных run types автоматически обновляется.

**Какие метрики поддерживают `run_type`:**
- `bioetl_records_processed_total` (pipeline, stage, **run_type**)
- `bioetl_pipeline_duration_seconds` (pipeline, stage, status, **run_type**)
- `bioetl_dq_records_quarantined_total` (pipeline, error_type, **run_type**)
- `bioetl_pipeline_runs_total` (pipeline, **run_type**, status)

**Какие метрики НЕ поддерживают `run_type`:**
- `bioetl_errors_total` — фильтруется только по `pipeline`
- `bioetl_batch_size_records` — фильтруется только по `pipeline`
- `bioetl_data_freshness_seconds` — фильтруется только по `pipeline`
- `bioetl_filter_ids_*` — фильтруется только по `pipeline`
- `bioetl_adapter_request_duration_seconds` — фильтруется по `provider`
- `bioetl_http_request_errors_total` — фильтруется по `provider`

---

## 7. Дашборд: BioETL Simple

**Файл:** `grafana/dashboards/bioetl-simple.json`
**UID:** `bioetl-simple`
**Refresh:** 5 секунд (live)
**Time range:** Последний час
**Назначение:** Минимальный live-дашборд для быстрого мониторинга текущего запуска пайплайна. Показывает только основные счётчики записей по стадиям Medallion Architecture (Bronze → Silver → Gold).

### Панели

| ID | Название | Тип | PromQL | Описание |
|---|---|---|---|---|
| 1 | Bronze Records | Stat | `sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="bronze"})` | Общее количество записей в Bronze-слое (raw data). Зелёный цвет. |
| 2 | Silver Records | Stat | `sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="silver"})` | Количество записей после валидации и дедупликации (Silver). |
| 3 | Gold Records | Stat | `sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="gold"})` | Количество финальных чистых записей (Gold). |
| 4 | Quality Ratio | Gauge | `sum(...stage="gold") / sum(...stage="bronze")` | Соотношение Gold/Bronze. Пороги: <80% красный, 80-95% оранжевый, >95% зелёный. |
| 5 | Records by Stage (Live) | Timeseries | `bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}` | Временная серия по стадиям с легендой `{{stage}}`. |

**Используемые метрики:** Только `bioetl_records_processed_total`.

---

## 8. Дашборд: BioETL Overview v1

**Файл:** `grafana/dashboards/bioetl-overview.json`
**UID:** `bioetl-overview`
**Refresh:** 30 секунд
**Time range:** Последние 6 часов
**Назначение:** Полный обзор пайплайнов: производительность, ошибки, длительность, размеры батчей, свежесть данных, входные фильтры.

### Панели

| ID | Название | Тип | PromQL | Описание |
|---|---|---|---|---|
| 2 | Records Processed Rate | Timeseries | `rate(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}[5m])` | Скорость обработки записей (записей/сек) за скользящее 5-минутное окно. Группировка по `{{stage}}`. |
| 3 | Error Rate | Timeseries | `rate(bioetl_errors_total{pipeline=~"$pipeline"}[5m])` | Скорость возникновения ошибок за 5 минут. Фильтр `run_type` не применяется (метрика не имеет этого label). |
| 4 | Pipeline Duration (p50/p95/p99) | Timeseries | `histogram_quantile(0.50/0.95/0.99, rate(bioetl_pipeline_duration_seconds_bucket{pipeline=~"$pipeline", run_type=~"$run_type"}[5m]))` | Перцентили длительности пайплайна. Три линии: p50 (медиана), p95, p99. Единица: секунды. |
| 5 | Batch Size Percentiles | Timeseries | `histogram_quantile(0.50/0.95, rate(bioetl_batch_size_records_bucket{pipeline=~"$pipeline"}[5m]))` | Перцентили размеров батчей (p50, p95). Фильтр `run_type` не применяется. |
| 6 | Data Freshness | Timeseries | `time() - bioetl_data_freshness_seconds{pipeline=~"$pipeline"}` | Секунды с момента последнего ingestion. Чем меньше, тем свежее данные. |
| 7 | Filter IDs Loaded | Timeseries | `sum(bioetl_filter_ids_loaded_total{pipeline=~"$pipeline"}) by (pipeline)` | Количество загруженных ID из входных фильтров. |
| 8 | Filter IDs Duplicates | Timeseries | `sum(bioetl_filter_ids_duplicates_total{pipeline=~"$pipeline"}) by (pipeline)` | Количество обнаруженных дубликатов во входных фильтрах. |

**Используемые метрики:** `records_processed_total`, `errors_total`, `pipeline_duration_seconds`, `batch_size_records`, `data_freshness_seconds`, `filter_ids_loaded_total`, `filter_ids_duplicates_total`.

---

## 9. Дашборд: BioETL Overview v2

**Файл:** `grafana/dashboards/bioetl-overview-v2.json`
**UID:** `bioetl-overview-v2`
**Refresh:** 30 секунд
**Time range:** Последние 7 дней
**Назначение:** Обзор, оптимизированный для анализа конкретного запуска. Включает информационные панели (Pipeline, Run Type), круговые диаграммы распределения, и gauge качества.

### Панели

| ID | Название | Тип | PromQL | Описание |
|---|---|---|---|---|
| 99 | Pipeline | Stat | `max(label_values(bioetl_records_processed_total{...}, pipeline)) or vector(0)` | Информационная панель с именем текущего пайплайна. |
| 100 | Run Type | Stat | `max(label_values(bioetl_records_processed_total{..., run_type=~"$run_type"}, run_type)) or vector(0)` | Информационная панель с текущим типом запуска. |
| 1 | Processing Pipeline | Timeseries | `sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}) by (stage)` | Временная серия обработки по стадиям. |
| 2 | Stage Distribution | Piechart | `sum(...) by (stage)` | Круговая диаграмма: распределение записей по Bronze/Silver/Gold/Quarantined. |
| 3 | Pipeline Distribution | Piechart | `sum(...) by (pipeline)` | Круговая диаграмма: распределение записей по пайплайнам. |
| 4 | Overall Quality | Gauge | `sum(...stage="gold") / sum(...stage="bronze")` | Gauge качества с 4-уровневой шкалой: <50% красный, 50-80% оранжевый, 80-95% жёлтый, >95% зелёный. |
| 101 | Execution Timestamp | Stat | `min(bioetl_records_processed_created{pipeline=~"$pipeline", run_type=~"$run_type"})` | Timestamp начала выполнения (из автоматической метрики `_created`). |

**Используемые метрики:** `records_processed_total`, `records_processed_created`.

---

## 10. Дашборд: BioETL Data Quality v1

**Файл:** `grafana/dashboards/bioetl-dq.json`
**UID:** `bioetl-dq`
**Refresh:** 30 секунд
**Time range:** Последние 6 часов
**Назначение:** Детальный мониторинг качества данных: длительность пайплайна, скорость обработки, качественное соотношение Gold/Bronze, распределение батчей.

### Панели

| ID | Название | Тип | PromQL | Описание |
|---|---|---|---|---|
| 1 | Pipeline Duration (p50/p95/p99) | Timeseries | `histogram_quantile(0.50/0.95/0.99, rate(bioetl_pipeline_duration_seconds_bucket{pipeline=~"$pipeline", run_type=~"$run_type"}[5m]))` | Перцентили длительности. Три линии. Ось Y: секунды. |
| 2 | Processing Rate by Stage | Timeseries | `rate(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}[5m])` | Скорость обработки (записей/сек) с группировкой по `{{stage}}`. |
| 3 | Data Quality Ratio | Gauge | `sum(...stage="gold") / sum(...stage="bronze")` | Gauge соотношения Gold/Bronze. Пороги: <80% красный, 80-95% оранжевый, >95% зелёный. |
| 4 | Batch Size Percentiles | Timeseries | `histogram_quantile(0.50/0.95/0.99, bioetl_batch_size_records_bucket{pipeline=~"$pipeline"})` | Перцентили размеров батчей. Фильтр `run_type` не применяется. |

**Используемые метрики:** `pipeline_duration_seconds`, `records_processed_total`, `batch_size_records`.

---

## 11. Дашборд: BioETL Data Quality v2

**Файл:** `grafana/dashboards/bioetl-dq-v2.json`
**UID:** `bioetl-dq-v2`
**Refresh:** 30 секунд
**Time range:** Последние 7 дней
**Назначение:** Data Quality мониторинг, оптимизированный для анализа конкретного запуска. Включает информационные панели, gauge качества, счётчики Bronze/Gold, и timestamp выполнения.

### Панели

| ID | Название | Тип | PromQL | Описание |
|---|---|---|---|---|
| 99 | Pipeline | Stat | `max(label_values(..., pipeline)) or vector(0)` | Информационная панель пайплайна. |
| 100 | Run Type | Stat | `max(label_values(..., run_type)) or vector(0)` | Информационная панель типа запуска. |
| 1 | Data Flow | Timeseries | `bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}` | Полный поток данных: Bronze → Silver → Gold. Легенда: `{{pipeline}} / {{stage}}`. |
| 2 | Data Quality Score | Gauge | `sum(...stage="gold") / sum(...stage="bronze")` | 4-уровневый gauge качества: красный (<50%), оранжевый (50-80%), жёлтый (80-95%), зелёный (>95%). |
| 3 | Source Records (Bronze) | Stat | `sum(bioetl_records_processed_total{...stage="bronze"})` | Общее количество входных записей. |
| 4 | Clean Records (Gold) | Stat | `sum(bioetl_records_processed_total{...stage="gold"})` | Общее количество финальных чистых записей. |
| 101 | Execution Timestamp | Stat | `min(bioetl_records_processed_created{...})` | Timestamp начала выполнения. |

**Используемые метрики:** `records_processed_total`, `records_processed_created`.

---

## 12. Дашборд: BioETL Provider Health v1

**Файл:** `grafana/dashboards/bioetl-provider-health.json`
**UID:** `bioetl-provider-health`
**Refresh:** 30 секунд
**Time range:** Последние 6 часов
**Назначение:** Мониторинг здоровья внешних API-провайдеров. Показывает пропускную способность по стадиям Medallion и распределение батчей.

### Панели

| ID | Название | Тип | PromQL | Описание |
|---|---|---|---|---|
| 1 | Bronze Records | Stat | `sum(bioetl_records_processed_total{...stage="bronze"})` | Счётчик Bronze. |
| 2 | Silver Records | Stat | `sum(bioetl_records_processed_total{...stage="silver"})` | Счётчик Silver. |
| 3 | Gold Records | Stat | `sum(bioetl_records_processed_total{...stage="gold"})` | Счётчик Gold. |
| 4 | Quarantined Records | Stat | `sum(bioetl_records_processed_total{...stage="quarantined"})` | Счётчик карантинных записей. Пороги: >10 жёлтый, >100 красный. |
| 5 | Records by Stage Over Time | Timeseries | `bioetl_records_processed_total{...}` | Временная серия записей по стадиям. |
| 6 | Batch Size Distribution | Timeseries (bars) | `histogram_quantile(0.50/0.95, bioetl_batch_size_records_bucket{pipeline=~"$pipeline"})` | Гистограмма распределения размеров батчей (p50, p95). |

**Используемые метрики:** `records_processed_total`, `batch_size_records`.

---

## 13. Дашборд: BioETL Provider Health v2

**Файл:** `grafana/dashboards/bioetl-provider-health-v2.json`
**UID:** `bioetl-provider-health-v2`
**Refresh:** 30 секунд
**Time range:** Последние 7 дней
**Назначение:** Детальный мониторинг здоровья каждого API-провайдера: время отклика, процент ошибок, латентность по провайдерам (UniProt, PubMed, PubChem, ChemBL).

### Панели

| ID | Название | Тип | PromQL | Описание |
|---|---|---|---|---|
| 99 | Pipeline | Stat | `max(label_values(..., pipeline)) or vector(0)` | Информационная панель пайплайна. |
| 100 | Run Type | Stat | `max(label_values(..., run_type)) or vector(0)` | Информационная панель типа запуска. |
| 1 | Provider Response Time (P95) | Timeseries (bars, stacked) | `histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket{provider=~"$pipeline"}[5m])) by (provider)` | P95 времени отклика адаптера в секундах, сгруппированное по провайдеру. Показывает реальную задержку API-запросов. |
| 2 | Error Rate by Provider | Timeseries | `rate(bioetl_http_request_errors_total{provider=~"$pipeline"}[5m]) * 100` | Процент HTTP-ошибок за 5-минутное окно, сгруппированный по провайдеру. |
| 3 | UniProt Latency | Gauge | `histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket{provider="uniprot"}[5m]))` | P95 латентность UniProt API. Пороги: <0.5s зелёный, 0.5-1s жёлтый, 1-2s оранжевый, >2s красный. |
| 4 | PubMed Latency | Gauge | `histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket{provider="pubmed"}[5m]))` | P95 латентность PubMed API. Те же пороги. |
| 5 | PubChem Latency | Gauge | `histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket{provider="pubchem"}[5m]))` | P95 латентность PubChem API. |
| 6 | ChemBL Latency | Gauge | `histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket{provider="chembl"}[5m]))` | P95 латентность ChemBL API. |
| 101 | Execution Timestamp | Stat | `min(bioetl_records_processed_created{...})` | Timestamp начала выполнения. |

**Используемые метрики:** `adapter_request_duration_seconds`, `http_request_errors_total`, `records_processed_total`, `records_processed_created`.

**Источник данных для Provider Response Time:** Метрика `bioetl_adapter_request_duration_seconds` записывается HTTP-адаптерами при каждом API-запросе к внешним провайдерам (ChemBL, PubMed, PubChem, UniProt). Label `provider` содержит имя провайдера, `endpoint` — конкретный API endpoint. Histogram-бакеты: 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0 секунд.

**Источник данных для Error Rate:** Метрика `bioetl_http_request_errors_total` инкрементируется при каждой HTTP-ошибке. Labels: `provider` (имя провайдера), `method` (HTTP-метод), `error_type` (тип ошибки: timeout, connection_error, http_4xx, http_5xx).

---

## 14. Справочник PromQL-паттернов

### 14.1 Базовые запросы

```promql
# Текущее значение counter
bioetl_records_processed_total{pipeline="chembl", stage="gold"}

# Скорость изменения counter (записей/сек) за 5 минут
rate(bioetl_records_processed_total{pipeline="chembl"}[5m])

# Суммарное значение по всем пайплайнам
sum(bioetl_records_processed_total)

# Группировка по label
sum(bioetl_records_processed_total) by (pipeline)

# Топ-5 пайплайнов по количеству записей
topk(5, sum(bioetl_records_processed_total) by (pipeline))
```

### 14.2 Histogram-запросы

```promql
# P95 длительности пайплайна
histogram_quantile(0.95, rate(bioetl_pipeline_duration_seconds_bucket[5m]))

# P50 (медиана)
histogram_quantile(0.50, rate(bioetl_pipeline_duration_seconds_bucket[5m]))

# Средняя длительность (sum / count)
rate(bioetl_pipeline_duration_seconds_sum[5m]) / rate(bioetl_pipeline_duration_seconds_count[5m])

# P95 с группировкой по пайплайну
histogram_quantile(0.95, sum(rate(bioetl_pipeline_duration_seconds_bucket[5m])) by (le, pipeline))
```

### 14.3 Gauge-запросы

```promql
# Текущее состояние circuit breaker
bioetl_circuit_breaker_state{adapter="chembl"}

# Текущий DQ score
bioetl_dq_validation_score{pipeline="chembl"}

# Среднее время с последнего ingestion
avg(time() - bioetl_data_freshness_seconds) by (pipeline)
```

### 14.4 Ratio и Alert-паттерны

```promql
# Quality Ratio (Gold / Bronze)
sum(bioetl_records_processed_total{stage="gold"}) / sum(bioetl_records_processed_total{stage="bronze"})

# Error Rate (%)
rate(bioetl_errors_total[5m]) / rate(bioetl_records_processed_total[5m]) * 100

# Quarantine Rate
sum(bioetl_records_processed_total{stage="quarantined"}) / sum(bioetl_records_processed_total{stage="bronze"}) * 100

# Circuit breaker open alert
bioetl_circuit_breaker_state == 2

# Data freshness alert (>1 hour stale)
(time() - bioetl_data_freshness_seconds) > 3600
```

### 14.5 Adapter-паттерны

```promql
# P95 latency per provider
histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket[5m])) by (provider)

# Request rate per provider
sum(rate(bioetl_adapter_requests_total[5m])) by (provider)

# Error rate per provider
sum(rate(bioetl_http_request_errors_total[5m])) by (provider)

# Success ratio per provider
1 - (sum(rate(bioetl_http_request_errors_total[5m])) by (provider) /
     sum(rate(bioetl_adapter_requests_total[5m])) by (provider))
```

---

## 15. Устранение неполадок

### 15.1 Дашборды пустые (No Data)

**Причина 1: Пайплайн не запущен.**

```bash
# Проверить: метрики должны быть доступны
curl -s http://localhost:8000/metrics | head -20

# Если "Connection refused" — запустить пайплайн:
make run-local
```

**Причина 2: Prometheus не скрейпит.**

```bash
# Проверить target в Prometheus UI:
# http://localhost:9090/targets
# Target должен быть "UP"

# Если "DOWN" — проверить сеть:
# На Windows/macOS: host.docker.internal должен резолвиться
# На Linux: добавить --add-host=host.docker.internal:host-gateway
docker compose -f docker-compose.monitoring.yml restart prometheus
```

**Причина 3: Неправильный datasource в Grafana.**

```bash
# Проверить datasource:
# http://localhost:3000/connections/datasources
# Должен быть "Prometheus" с URL "http://prometheus:9090"
# Нажать "Test" — должен показать "Data source is working"
```

**Причина 4: Метрики отключены в приложении.**

```bash
# Проверить .env:
grep BIOETL_METRICS .env

# Должно быть:
# BIOETL_METRICS_ENABLED=true
# BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED=true
```

### 15.2 Prometheus Target DOWN

```bash
# Проверить, что BioETL слушает на нужном порту
curl http://localhost:8000/metrics

# Если порт другой, обновить grafana/prometheus.yml:
# targets: ['host.docker.internal:<правильный_порт>']

# Перезапустить Prometheus
docker compose -f docker-compose.monitoring.yml restart prometheus
```

### 15.3 Grafana не загружает дашборды

```bash
# Проверить provisioning логи
docker logs bioetl-grafana 2>&1 | grep -i "provision\|dashboard\|error"

# Проверить, что JSON-файлы смонтированы
docker exec bioetl-grafana ls /var/lib/grafana/dashboards/

# Проверить валидность JSON
for f in grafana/dashboards/*.json; do
    python -m json.tool "$f" > /dev/null 2>&1 && echo "OK: $f" || echo "FAIL: $f"
done
```

### 15.4 Метрический сервер не запускается (порт занят)

```bash
# Проверить, кто занимает порт
# Windows:
netstat -ano | findstr :8000

# Linux/macOS:
lsof -i :8000

# Решения:
# 1. Изменить порт в .env: BIOETL_METRICS_PORT=8001
# 2. Обновить prometheus.yml: targets: ['host.docker.internal:8001']
# 3. Или убить процесс, занимающий порт
```

### 15.5 Dropdown переменных пустой

Если выпадающий список `Pipeline` или `Run Type` не содержит значений:
- Убедитесь, что пайплайн выполнялся хотя бы один раз после запуска Prometheus.
- Проверьте в Prometheus UI: `http://localhost:9090/graph` → введите `bioetl_records_processed_total` → Execute. Должны появиться результаты.
- Подождите 15-30 секунд после запуска пайплайна (интервал скрейпинга Prometheus).

---

## 16. Архитектурные решения и обоснования

### 16.1 Почему Prometheus, а не Push-модель (StatsD, InfluxDB)

Prometheus выбран по следующим причинам:

- **Pull-модель** лучше подходит для batch ETL: приложение не нуждается в знании адреса сервера метрик. Prometheus сам обнаруживает и опрашивает targets.
- **PromQL** — мощный язык запросов для агрегации time series.
- **Prometheus client library** для Python интегрируется минимальным кодом. Метрики определяются как глобальные объекты, HTTP-сервер запускается одной строкой.
- **Grafana интеграция** — Prometheus является first-class datasource в Grafana с полной поддержкой template variables, ad-hoc queries и provisioning.

### 16.2 Почему `run_type` вместо `run_id` в label

Ранние версии дашбордов использовали `run_id` как label для фильтрации по конкретному запуску. Это было исправлено по следующим причинам:

- **High cardinality problem:** Каждый уникальный `run_id` создаёт новую time series в Prometheus. При частых запусках это приводит к экспоненциальному росту количества time series, увеличению потребления памяти и деградации производительности.
- **Prometheus best practices:** Prometheus documentation рекомендует использовать labels с ограниченным количеством возможных значений. `run_type` имеет всего 3 значения (incremental, backfill, rebuild), тогда как `run_id` — неограниченное количество.
- **Практическая достаточность:** Для мониторинга достаточно фильтрации по типу запуска. Для анализа конкретного запуска используются structured logs (JSON) через отдельные инструменты (Loki, ELK).

### 16.3 Разделение v1 и v2 дашбордов

Дашборды существуют в двух версиях для разных use cases:

- **v1 (Legacy):** Исторические тренды за длительные периоды. Используют `rate()` для нормализации counter-метрик. Подходят для анализа производительности за часы и дни.
- **v2 (Latest Run):** Оптимизированы для мониторинга текущего или последнего запуска. Включают информационные панели (Pipeline, Run Type, Timestamp), круговые диаграммы распределения, и более агрессивный time range (7 дней по умолчанию). Используют сырые counter-значения для абсолютных цифр.

### 16.4 MetricsPort vs. прямой prometheus_client

Использование Protocol-интерфейса (MetricsPort) вместо прямого импорта `prometheus_client` обеспечивает:

- **Тестируемость:** В unit-тестах подставляется NoOpMetrics без побочных эффектов.
- **Взаимозаменяемость:** Можно переключиться на StatsD, CloudWatch или любой другой бэкенд без изменения application-кода.
- **Соблюдение ARCH-001:** Domain и Application слои не зависят от infrastructure-библиотек.

Определение MetricsPort в `src/bioetl/domain/ports/observability.py`:

```python
@runtime_checkable
class MetricsPort(Protocol):
    def observe_histogram(self, name: str, value: float, labels: dict[str, str]) -> None: ...
    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None: ...
    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None: ...
    def close(self) -> None: ...
```

### 16.5 NoOp fallback стратегия

Когда метрики отключены или сервер не удаётся запустить, система продолжает работу без мониторинга. Это реализовано через:

- **NoOpMetrics:** Все методы — пустые no-op. Нулевой overhead.
- **Graceful degradation в server.py:** При `fail_fast=false` (по умолчанию) ошибка запуска сервера логируется, но не прерывает пайплайн.
- **Принцип:** Observability не должна блокировать бизнес-логику. Потеря метрик — допустимый tradeoff при сетевых проблемах.

---

---

## 17. Подробный разбор типов метрик Prometheus

### 17.1 Counter (Счётчик)

Counter — монотонно возрастающая метрика. Значение только увеличивается (или сбрасывается в 0 при перезапуске процесса). Используется для подсчёта событий: количество обработанных записей, количество ошибок, количество HTTP-запросов.

**Особенности Counter в BioETL:**

Prometheus client автоматически создаёт для каждого Counter дополнительную метрику `_created` с timestamp момента первого инкремента. Например, `bioetl_records_processed_total` порождает `bioetl_records_processed_created`. Эта метрика используется в v2-дашбордах для отображения времени начала выполнения пайплайна (панель "Execution Timestamp").

При работе с Counter в PromQL почти всегда используется функция `rate()` или `increase()`, поскольку сырое значение Counter (кумулятивная сумма) менее информативно, чем скорость изменения.

Пример: `rate(bioetl_records_processed_total{pipeline="chembl", stage="bronze"}[5m])` — показывает среднюю скорость загрузки записей в Bronze-слой за последние 5 минут (записей в секунду).

Пример: `increase(bioetl_records_processed_total{pipeline="chembl", stage="bronze"}[1h])` — показывает абсолютное увеличение количества записей за последний час.

В BioETL Counter-метрики применяются для:
- Подсчёта обработанных записей по стадиям Medallion Architecture (`records_processed_total`).
- Учёта ошибок по типам и стадиям (`errors_total`).
- Отслеживания HTTP-ошибок по провайдерам (`http_request_errors_total`).
- Подсчёта retry-попыток при сетевых сбоях (`data_source_retries_total`, `http_retries_total`).
- Учёта операций vacuum и архивации (`vacuum_files_removed_total`, `archive_files_total`).
- Мониторинга срабатываний circuit breaker (`circuit_breaker_trips_total`).

### 17.2 Histogram (Гистограмма)

Histogram собирает наблюдения (обычно длительности или размеры) и распределяет их по заранее определённым бакетам. Prometheus автоматически создаёт три time series для каждой гистограммы:

- `_bucket{le="X"}` — количество наблюдений, попавших в бакет с границей <= X.
- `_sum` — сумма всех наблюдённых значений.
- `_count` — общее количество наблюдений.
- `_created` — timestamp создания.

Бакеты определяются при создании метрики. Например, для `bioetl_adapter_request_duration_seconds` бакеты: `[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]` секунд. Это означает, что Prometheus будет считать отдельно количество запросов быстрее 50 мс, быстрее 100 мс, быстрее 250 мс, и так далее.

**Ключевая PromQL-функция: `histogram_quantile()`**

```promql
# P95 латентность API-запросов к ChemBL
histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket{provider="chembl"}[5m]))
```

Эта функция вычисляет значение, ниже которого попадает заданный процент наблюдений. P95 = значение, ниже которого 95% запросов. Чем выше перцентиль, тем больше "хвостовую" латентность он захватывает.

**Средняя длительность через sum/count:**

```promql
# Средняя длительность запросов за 5 минут
rate(bioetl_adapter_request_duration_seconds_sum{provider="chembl"}[5m])
  /
rate(bioetl_adapter_request_duration_seconds_count{provider="chembl"}[5m])
```

В BioETL Histogram-метрики применяются для:
- Измерения длительности пайплайнов (`pipeline_duration_seconds`).
- Измерения длительности отдельных фаз (`phase_duration_seconds`).
- Распределения размеров батчей (`batch_size_records`).
- Измерения латентности API-запросов (`adapter_request_duration_seconds`, `http_request_duration_seconds`).
- Мониторинга длительности операций хранилища (`vacuum_duration_seconds`, `archive_duration_seconds`, `bronze_write_duration_seconds`).
- Оценки длительности health check (`health_check_duration_seconds`, `health_check_latency_seconds`).
- Измерения времени ожидания rate limiter (`rate_limiter_wait_seconds`).
- Длительности трансформации данных (`transform_duration_seconds`).
- Длительности проверок качества данных (`dq_check_duration_ms`).

### 17.3 Gauge (Измеритель)

Gauge — метрика, значение которой может произвольно увеличиваться или уменьшаться. Представляет "текущее состояние" в момент времени. В отличие от Counter, сырые значения Gauge информативны сами по себе, без `rate()`.

**Примеры Gauge в BioETL:**

- `bioetl_circuit_breaker_state{adapter="chembl"}` — текущее состояние circuit breaker. Значения: 0 (closed — всё работает), 1 (half-open — пробная проверка), 2 (open — провайдер отключён). Этот gauge позволяет мгновенно увидеть, отключён ли какой-то провайдер из-за превышения порога ошибок.

- `bioetl_dq_validation_score{pipeline="chembl", entity="compound"}` — оценка качества данных от 0.0 до 1.0. Значение 0.98 означает, что 98% записей прошли валидацию. Этот gauge обновляется после каждой проверки качества.

- `bioetl_data_freshness_seconds{pipeline="chembl", entity="compound"}` — timestamp (epoch seconds) последнего успешного ingestion. Для вычисления "возраста" данных используется PromQL-выражение `time() - bioetl_data_freshness_seconds`.

- `bioetl_health_check_status{component="database"}` — статус здоровья компонента: 0=unknown, 1=healthy, 2=degraded. Позволяет создавать status pages.

- `bioetl_provider_health_status{provider="chembl"}` — интегральный статус здоровья провайдера.

- `bioetl_rate_limiter_tokens_available{provider="chembl"}` — текущее количество доступных токенов в rate limiter. Когда значение падает до 0, запросы к провайдеру блокируются до восстановления токенов.

---

## 18. Medallion Architecture и метрики

### 18.1 Обзор Medallion Architecture

BioETL использует трёхуровневую Medallion Architecture для организации данных. Каждый уровень (Bronze, Silver, Gold) имеет свои метрики, позволяющие отследить поток данных от raw input до чистых финальных таблиц.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL APIs                                │
│    ChemBL API    PubMed API    PubChem API    UniProt API           │
└──────┬────────────┬─────────────┬──────────────┬────────────────────┘
       │            │             │              │
       │  HTTP      │  HTTP       │  HTTP        │  HTTP
       │  requests  │  requests   │  requests    │  requests
       │            │             │              │
       │ Метрики: adapter_request_duration_seconds                    │
       │           http_request_errors_total                          │
       │           adapter_requests_total                             │
       │           rate_limiter_wait_seconds                          │
       ▼            ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BRONZE Layer (Raw Data)                                            │
│                                                                     │
│  Сырые данные с минимальной обработкой. Формат: Parquet.            │
│                                                                     │
│  Метрики:                                                           │
│  - records_processed_total{stage="bronze"} — количество записей     │
│  - bronze_write_duration_seconds — длительность записи               │
│  - bronze_records_written_total — записанные записи                  │
│  - bronze_bytes_written_total — записанные байты                     │
│  - batch_size_records — размеры батчей                               │
│                                                                     │
│  Пример: 15,420 записей из ChemBL API загружены в Bronze            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │  Transform + Validate
                               │
                               │  Метрики:
                               │  - transform_duration_seconds
                               │  - transform_errors_total
                               │  - dq_check_duration_ms
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SILVER Layer (Validated & Deduplicated)                             │
│                                                                     │
│  Данные после валидации, дедупликации, нормализации схемы.          │
│  Формат: Delta Lake (ACID-транзакции, версионирование).             │
│                                                                     │
│  Метрики:                                                           │
│  - records_processed_total{stage="silver"} — валидные записи        │
│  - dq_validation_score — оценка качества (0.0 — 1.0)               │
│  - silver_validation_failures_total — ошибки валидации схемы         │
│                                                                     │
│  Пример: 15,380 записей прошли валидацию (40 отсеяно)               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │  Enrich + Final Transform
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GOLD Layer (Business-Ready)                                        │
│                                                                     │
│  Финальные таблицы для аналитики и data science.                    │
│  Формат: Delta Lake.                                                │
│                                                                     │
│  Метрики:                                                           │
│  - records_processed_total{stage="gold"} — чистые записи            │
│  - records_processed_total{stage="quarantined"} — карантинные        │
│  - dq_records_quarantined_total — детальный карантин по типам         │
│  - data_freshness_seconds — свежесть данных                          │
│                                                                     │
│  Пример: 15,102 записей в Gold, 278 на карантине                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 18.2 Quality Ratio

Ключевой показатель качества пайплайна — соотношение Gold/Bronze:

```promql
sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="gold"})
  /
sum(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type", stage="bronze"})
```

Этот показатель используется в gauge-панелях дашбордов Simple, Overview, Data Quality с пороговыми значениями:

| Значение | Цвет | Интерпретация |
|---|---|---|
| < 50% | Красный | Критическая проблема: более половины записей теряется |
| 50-80% | Оранжевый | Предупреждение: значительная потеря данных, требует внимания |
| 80-95% | Жёлтый | Допустимо: небольшая потеря на валидации/дедупликации |
| > 95% | Зелёный | Нормально: высокое качество данных |

Типичное значение для здорового пайплайна: 95-99%. Потеря 1-5% обычно объясняется:
- Дублирующимися записями из API (дедупликация в Silver).
- Записями с невалидными полями (валидация по Pandera-схемам в Silver).
- Записями без обязательных полей (фильтрация при переходе в Gold).

### 18.3 Карантин (Quarantined Records)

Записи, не прошедшие валидацию, не удаляются, а перемещаются на карантин. Это отслеживается двумя метриками:

- `bioetl_records_processed_total{stage="quarantined"}` — общий счётчик карантинных записей (по пайплайну и типу запуска).
- `bioetl_dq_records_quarantined_total{pipeline, error_type, run_type}` — детализированный счётчик с указанием типа ошибки (`schema_violation`, `null_required_field`, `duplicate`, `type_mismatch` и др.).

---

## 19. Circuit Breaker и мониторинг провайдеров

### 19.1 Модель Circuit Breaker (ADR-007)

BioETL использует паттерн Circuit Breaker для защиты от каскадных сбоев при взаимодействии с внешними API. Каждый адаптер (ChemBL, PubMed, PubChem, UniProt) имеет собственный circuit breaker с тремя состояниями:

**Closed (0):** Нормальная работа. Все запросы проходят к провайдеру. Ошибки считаются, но не блокируют запросы.

**Open (2):** Провайдер временно отключён после превышения порога ошибок. Все запросы мгновенно отклоняются без обращения к API. Экономит ресурсы и предотвращает перегрузку нестабильного провайдера.

**Half-Open (1):** Пробное состояние. Допускается один тестовый запрос. Если успешен — переход в Closed. Если неуспешен — обратно в Open.

```promql
# Мониторинг состояния circuit breaker
bioetl_circuit_breaker_state{adapter="chembl"}
# 0 = closed (нормально), 1 = half-open (проверка), 2 = open (отключён)

# Количество срабатываний за последний час
increase(bioetl_circuit_breaker_trips_total{adapter="chembl"}[1h])

# Соотношение успешных/неуспешных вызовов
sum(rate(bioetl_circuit_breaker_success_total{adapter="chembl"}[5m]))
  /
(sum(rate(bioetl_circuit_breaker_success_total{adapter="chembl"}[5m]))
  +
 sum(rate(bioetl_circuit_breaker_failure_total{adapter="chembl"}[5m])))
```

### 19.2 Provider Health Dashboard: как читать

Дашборд Provider Health v2 предоставляет четыре gauge-панели для отдельных провайдеров (UniProt, PubMed, PubChem, ChemBL). Каждая панель показывает P95-латентность API-запросов в секундах за последние 5 минут.

Пороговые значения gauge:
- **< 0.5 сек (зелёный):** Нормальная латентность. API отвечает быстро.
- **0.5-1.0 сек (жёлтый):** Повышенная латентность. Может указывать на нагрузку на стороне провайдера.
- **1.0-2.0 сек (оранжевый):** Высокая латентность. Рекомендуется проверить rate limiting и сетевые условия.
- **> 2.0 сек (красный):** Критическая латентность. Провайдер деградирует. Возможно срабатывание circuit breaker.

Панель "Error Rate by Provider" показывает процент HTTP-ошибок. Нормальное значение — 0%. Любое ненулевое значение требует исследования. Источник данных — метрика `bioetl_http_request_errors_total`, которая инкрементируется при каждом неуспешном HTTP-запросе. Типы ошибок фиксируются в label `error_type`: timeout, connection_error, http_4xx, http_5xx.

---

## 20. Data Quality Monitor (DQMonitorPort)

### 20.1 Архитектура DQ мониторинга

Data Quality Monitor реализует статистическое обнаружение аномалий на основе Z-score анализа. Компонент определён через порт `DQMonitorPort` в domain-слое и реализован как `DataQualityMonitor` в infrastructure-слое.

Ключевые метрики DQ, отражающиеся в дашбордах:

**`bioetl_dq_validation_score`** — центральная метрика качества. Gauge от 0.0 до 1.0. Вычисляется как `valid_records / total_records` после каждой проверки. Значение 1.0 означает, что все записи прошли валидацию.

**`bioetl_dq_anomaly_detected`** — инкрементируется при обнаружении аномалии. Labels: `pipeline` (какой пайплайн), `metric` (какая метрика), `severity` (LOW, MEDIUM, HIGH, CRITICAL), `anomaly_type` (SPIKE, DROP, THRESHOLD_EXCEEDED).

**`bioetl_dq_baseline_samples`** — текущее количество исторических точек в baseline для каждой метрики. Чем больше samples, тем точнее Z-score анализ. Рекомендуется минимум 7 точек (недельный baseline).

**`bioetl_dq_baseline_updated`** — количество обновлений baseline. Baseline обновляется только после успешных запусков без критических аномалий. Это защищает от "отравления" baseline плохими данными.

### 20.2 Z-score анализ

DataQualityMonitor вычисляет Z-score для каждой метрики:

```
z_score = (current_value - baseline_mean) / baseline_stddev
```

Пороги severity:
- |z_score| > 2.0: MEDIUM
- |z_score| > 2.5: HIGH
- |z_score| > 3.0: CRITICAL

Пример: если baseline средний record_count = 15,000 с stddev = 500, и текущий record_count = 12,000:
- z_score = (12000 - 15000) / 500 = -6.0
- Severity = CRITICAL (|z_score| > 3.0)
- Anomaly type = DROP (текущее значение ниже baseline)

---

## 21. Rate Limiting и его мониторинг

### 21.1 Метрики Rate Limiter

BioETL реализует rate limiting для предотвращения превышения лимитов API провайдеров. Мониторинг осуществляется двумя метриками:

**`bioetl_rate_limiter_tokens_available{provider}`** (Gauge) — текущее количество доступных токенов. При значении 0 все запросы блокируются до восстановления токенов. Мониторинг этой метрики позволяет предсказать, когда пайплайн начнёт замедляться из-за rate limiting.

**`bioetl_rate_limiter_wait_seconds{provider}`** (Histogram) — время ожидания в rate limiter. Бакеты: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0 секунд. Рост P95 ожидания указывает на приближение к лимитам API.

```promql
# Текущие доступные токены по провайдерам
bioetl_rate_limiter_tokens_available

# P95 ожидание в rate limiter
histogram_quantile(0.95, rate(bioetl_rate_limiter_wait_seconds_bucket[5m])) by (provider)

# Среднее время ожидания за последний час
rate(bioetl_rate_limiter_wait_seconds_sum[1h]) / rate(bioetl_rate_limiter_wait_seconds_count[1h])
```

---

## 22. Рекомендации по созданию пользовательских дашбордов

### 22.1 Создание через Grafana UI

1. Открыть `http://localhost:3000`.
2. Перейти: Dashboards → New → New Dashboard → Add visualization.
3. Выбрать datasource: Prometheus.
4. Ввести PromQL-запрос, например: `bioetl_records_processed_total{pipeline="chembl"}`.
5. Настроить визуализацию (panel type, thresholds, legend).
6. Сохранить дашборд.

### 22.2 Создание JSON-дашборда для provisioning

Для автоматического provisioning создайте JSON-файл в `grafana/dashboards/`. Структура:

```json
{
    "annotations": { "list": [] },
    "editable": true,
    "panels": [
        {
            "datasource": "Prometheus",
            "targets": [
                {
                    "expr": "bioetl_records_processed_total{pipeline=~\"$pipeline\"}",
                    "legendFormat": "{{stage}}",
                    "refId": "A"
                }
            ],
            "title": "My Panel",
            "type": "timeseries",
            "gridPos": { "h": 8, "w": 24, "x": 0, "y": 0 },
            "id": 1
        }
    ],
    "templating": {
        "list": [
            {
                "datasource": "Prometheus",
                "definition": "label_values(bioetl_records_processed_total, pipeline)",
                "name": "pipeline",
                "label": "Pipeline",
                "type": "query",
                "includeAll": true,
                "multi": true,
                "refresh": 1
            }
        ]
    },
    "title": "My Custom Dashboard",
    "uid": "my-custom-dashboard",
    "version": 1
}
```

Grafana автоматически обнаружит новый файл в течение 30 секунд (настраивается в `bioetl.yaml` → `updateIntervalSeconds`).

### 22.3 Рекомендуемые визуализации по типу метрик

| Тип метрики | Рекомендуемая визуализация | Функция PromQL |
|---|---|---|
| Counter (total) | Timeseries с `rate()` | `rate(metric[5m])` |
| Counter (total) | Stat (суммарное значение) | `sum(metric)` |
| Histogram (duration) | Timeseries с перцентилями | `histogram_quantile(0.95, rate(metric_bucket[5m]))` |
| Histogram (size) | Bar chart | `histogram_quantile(0.50, metric_bucket)` |
| Gauge (state) | Stat с color mapping | `metric` (сырое значение) |
| Gauge (score) | Gauge с thresholds | `metric` (значение 0-1) |
| Gauge (freshness) | Stat с unit "seconds" | `time() - metric` |
| Counter ratio | Gauge (0-100%) | `sum(a) / sum(b)` |

### 22.4 Рекомендуемые интервалы rate()

| Сценарий | Интервал | Обоснование |
|---|---|---|
| Live мониторинг (Simple дашборд) | `[1m]` | Максимальная отзывчивость |
| Стандартный мониторинг | `[5m]` | Баланс отзывчивости и сглаживания |
| Trend-анализ | `[15m]` или `[30m]` | Сглаженные тренды без шума |
| Долгосрочный анализ | `[1h]` | Дневные и недельные паттерны |

Правило: интервал rate() должен быть как минимум в 4 раза больше scrape_interval Prometheus (15s × 4 = 60s = 1m).

---

## 23. FAQ (Часто задаваемые вопросы)

### Как узнать, какие метрики экспортирует BioETL?

```bash
curl -s http://localhost:8000/metrics | grep "^bioetl_" | awk '{print $1}' | sort -u
```

Или в Prometheus UI: введите `{__name__=~"bioetl_.*"}` и нажмите Execute.

### Почему дашборд Simple обновляется каждые 5 секунд, а остальные — каждые 30?

Simple предназначен для live-мониторинга текущего запуска. Частое обновление (5 сек) позволяет наблюдать за процессом в реальном времени. Остальные дашборды используют 30-секундный refresh для снижения нагрузки на Prometheus, так как их запросы более тяжёлые (histogram_quantile, rate, by clauses).

### Почему v1 и v2 дашборды сосуществуют?

v1 дашборды оптимизированы для исторического анализа (rate, percentiles, trends). v2 дашборды оптимизированы для мониторинга конкретного запуска (абсолютные значения, pie charts, info panels). Оба варианта полезны в разных сценариях: v1 — для команды SRE/DevOps, v2 — для data engineers и data scientists.

### Как добавить новую метрику?

1. Определите метрику в `src/bioetl/infrastructure/observability/metrics.py`:
   ```python
   MY_NEW_METRIC = Counter("bioetl_my_new_metric", "Description", ["label1", "label2"])
   ```
2. Добавьте в словарь `COUNTERS`, `HISTOGRAMS` или `GAUGES` в `prometheus_metrics.py`.
3. Вызывайте через MetricsPort в application-коде:
   ```python
   self._metrics.increment_counter("my_new_metric", value=1, labels={"label1": "val"})
   ```
4. Добавьте панель в JSON-дашборд или через Grafana UI.

### Как метрики переживают перезапуск приложения?

При перезапуске BioETL все Counter-метрики сбрасываются в 0 (это стандартное поведение Prometheus client). Prometheus обрабатывает это корректно: функция `rate()` и `increase()` автоматически учитывают сброс счётчика (counter reset), вычисляя дельту с учётом последнего известного значения перед перезапуском. Gauge-метрики также сбрасываются, но будут установлены заново при первом измерении после запуска.

Исторические данные в Prometheus TSDB не теряются при перезапуске приложения. Prometheus хранит все собранные данные в персистентном volume `prometheus-data`.

### Как работает формат Prometheus exposition?

Метрики экспортируются в текстовом формате. Каждая строка — одна time series:
```
metric_name{label1="value1", label2="value2"} numeric_value timestamp
```

Специальные строки начинаются с `#`:
- `# HELP metric_name Description` — описание метрики.
- `# TYPE metric_name counter|gauge|histogram|summary` — тип метрики.

Prometheus парсит этот формат при каждом scrape и сохраняет в TSDB.

### Сколько места занимают метрики в Prometheus?

Зависит от количества уникальных time series (комбинаций метрик и labels). BioETL с 4 провайдерами и 3 типами запуска генерирует приблизительно 200-500 уникальных time series. При scrape_interval=15s и retention=15 дней это занимает около 50-100 МБ. Для production с десятками пайплайнов рекомендуется мониторить `prometheus_tsdb_head_series` (текущее количество active series) и увеличивать storage при необходимости.

### Можно ли использовать Grafana без Docker?

Да. Установите Prometheus и Grafana нативно, затем:
1. Запустите Prometheus с конфигом `grafana/prometheus.yml`. Измените target на `localhost:8000`.
2. Запустите Grafana. Добавьте Prometheus как datasource (`http://localhost:9090`).
3. Импортируйте JSON-файлы из `grafana/dashboards/` через UI: Dashboards → Import → Upload JSON file.

Или настройте provisioning, скопировав содержимое `grafana/provisioning/` в директорию provisioning Grafana и обновив `path` в `bioetl.yaml` на абсолютный путь к `grafana/dashboards/`.

---

---

## 24. Alerting (Настройка оповещений)

### 24.1 Grafana Alerting

Grafana поддерживает встроенные алерты на основе PromQL-условий. Для настройки:

1. Откройте панель дашборда → Edit.
2. Перейдите на вкладку "Alert" (доступна для Timeseries и Stat панелей).
3. Определите условие: например, `WHEN avg() OF query(A, 5m, now) IS ABOVE 2` (средняя латентность > 2 секунд).
4. Настройте notification channel (Email, Slack, PagerDuty, Webhook).
5. Сохраните дашборд.

### 24.2 Рекомендуемые алерты для BioETL

**Критические алерты (требуют немедленного внимания):**

| Алерт | Условие PromQL | Severity | Описание |
|---|---|---|---|
| Circuit Breaker Open | `bioetl_circuit_breaker_state == 2` | CRITICAL | Провайдер полностью отключён. Пайплайн не может получать данные. |
| Quality Ratio Drop | `sum(records_processed{stage="gold"}) / sum(records_processed{stage="bronze"}) < 0.5` | CRITICAL | Более 50% данных теряется. Возможна проблема с источником или схемой. |
| Zero Records | `increase(bioetl_records_processed_total{stage="bronze"}[1h]) == 0` | CRITICAL | За последний час не загружено ни одной записи. Пайплайн может быть остановлен. |
| Health Check Failed | `bioetl_health_check_status == 0` | CRITICAL | Компонент инфраструктуры недоступен. |

**Предупреждающие алерты (требуют внимания в рабочее время):**

| Алерт | Условие PromQL | Severity | Описание |
|---|---|---|---|
| High Latency | `histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket[5m])) > 5` | WARNING | P95 латентность API > 5 секунд. Провайдер может деградировать. |
| Error Rate Spike | `rate(bioetl_http_request_errors_total[5m]) > 0.1` | WARNING | Более 10% запросов завершаются ошибкой. |
| Data Staleness | `(time() - bioetl_data_freshness_seconds) > 86400` | WARNING | Данные старше 24 часов. Пайплайн не выполнялся. |
| Retry Exhaustion | `increase(bioetl_data_source_retry_exhausted_total[1h]) > 0` | WARNING | Retry-попытки исчерпаны. Запросы к провайдеру не проходят. |
| DQ Anomaly | `increase(bioetl_dq_anomaly_detected{severity="critical"}[1h]) > 0` | WARNING | Обнаружена критическая аномалия качества данных. |
| High Quarantine Rate | `sum(records_processed{stage="quarantined"}) / sum(records_processed{stage="bronze"}) > 0.1` | WARNING | Более 10% записей на карантине. |

### 24.3 Prometheus Alerting Rules

Для production-деплоя рекомендуется использовать Alertmanager. Пример правил алертинга:

```yaml
# prometheus/alerts.yml (примерная конфигурация)
groups:
  - name: bioetl_alerts
    rules:
      - alert: CircuitBreakerOpen
        expr: bioetl_circuit_breaker_state == 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.adapter }}"
          description: "Circuit breaker for adapter {{ $labels.adapter }} has been open for 5 minutes."

      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(bioetl_adapter_request_duration_seconds_bucket[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High API latency for {{ $labels.provider }}"
          description: "P95 latency for {{ $labels.provider }} is {{ $value }}s (threshold: 5s)"

      - alert: DataQualityDrop
        expr: >
          sum(bioetl_records_processed_total{stage="gold"})
            /
          sum(bioetl_records_processed_total{stage="bronze"})
            < 0.8
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Data quality ratio below 80%"
```

### 24.4 Встроенные правила наблюдения для `chembl_assay`

В репозитории добавлен файл правил:

`grafana/prometheus-rules/bioetl_observability.yml`

Правила покрывают:

- деградацию health-check провайдера ChEMBL;
- падение preflight data source проверки;
- `infrastructure_validated=0` для `chembl_assay`;
- неуспешные запуски `chembl_assay`;
- исчерпание retry для провайдера `chembl`.

Эти rules автоматически загружаются через:

- `grafana/prometheus.yml` (`rule_files: /etc/prometheus/rules/*.yml`);
- volume mount в `docker-compose.monitoring.yml`:
  `./grafana/prometheus-rules:/etc/prometheus/rules:ro`.

Проверка после применения:

```bash
docker compose -f docker-compose.monitoring.yml restart prometheus
# Rules:
open http://localhost:9090/rules
# Active alerts:
open http://localhost:9090/alerts
```

---

## 25. Глоссарий

| Термин | Определение |
|---|---|
| **Bronze** | Первый слой Medallion Architecture. Содержит сырые данные из внешних API без обработки. Формат: Parquet. |
| **Silver** | Второй слой. Данные после валидации, дедупликации и нормализации. Формат: Delta Lake с ACID-гарантиями. |
| **Gold** | Третий слой. Финальные бизнес-готовые таблицы для аналитики. Формат: Delta Lake. |
| **Quarantined** | Записи, не прошедшие валидацию в Silver/Gold. Сохраняются отдельно для ручного анализа. |
| **Circuit Breaker** | Паттерн, защищающий от каскадных сбоев. Автоматически отключает провайдер при превышении порога ошибок (ADR-007). |
| **Counter** | Тип метрики Prometheus. Монотонно возрастающее значение. Сбрасывается при перезапуске процесса. |
| **Gauge** | Тип метрики Prometheus. Произвольное значение, может расти и уменьшаться. Представляет текущее состояние. |
| **Histogram** | Тип метрики Prometheus. Распределение значений по бакетам. Позволяет вычислять перцентили. |
| **PromQL** | Prometheus Query Language. Функциональный язык запросов для агрегации и анализа time series. |
| **Scrape** | Процесс сбора метрик. Prometheus выполняет HTTP GET к targets каждые `scrape_interval` секунд. |
| **Target** | Endpoint, с которого Prometheus собирает метрики. В BioETL: `host.docker.internal:8000`. |
| **Time Series** | Уникальная комбинация имени метрики и набора labels. Каждая time series хранит набор пар (timestamp, value). |
| **Label** | Ключ-значение пара, добавляющая измерение к метрике. Позволяет фильтровать и группировать данные. |
| **Template Variable** | Переменная Grafana, значения которой определяются PromQL-запросом. Используется для динамической фильтрации дашбордов. |
| **Provisioning** | Механизм автоматической загрузки конфигурации (datasources, dashboards) при старте Grafana. |
| **MetricsPort** | Protocol-интерфейс в domain-слое BioETL. Абстрагирует запись метрик от конкретной реализации (Prometheus, NoOp). |
| **NoOpMetrics** | Null Object реализация MetricsPort. Все методы — пустые no-op. Используется когда метрики отключены. |
| **Rate Limiter** | Механизм ограничения скорости запросов к внешним API для соблюдения лимитов провайдера. |
| **Run Type** | Тип запуска пайплайна: incremental (только новые данные), backfill (ретроспективное заполнение), rebuild (полная пересборка). |
| **TSDB** | Time Series Database. Хранилище Prometheus для time series данных. Оптимизировано для append и range queries. |
| **Adapter** | В контексте Hexagonal Architecture: реализация порта для конкретной технологии (ChemBLClient, PrometheusMetrics). |
| **Exposition Format** | Текстовый формат экспорта метрик Prometheus: `metric{labels} value timestamp`. |
| **Retention** | Период хранения данных в Prometheus TSDB. По умолчанию 15 дней. Настраивается через `--storage.tsdb.retention.time`. |
| **DQ Monitor** | Data Quality Monitor. Компонент обнаружения аномалий на основе Z-score анализа baseline метрик. |
| **Z-score** | Статистическая мера, показывающая, на сколько стандартных отклонений значение отклоняется от среднего. |
| **Medallion Architecture** | Паттерн организации данных в три слоя (Bronze → Silver → Gold) с повышением качества на каждом уровне. |

---

## 26. Сводная таблица дашбордов

| Дашборд | UID | Версия | Panels | Refresh | Time Range | Метрики | Назначение |
|---|---|---|---|---|---|---|---|
| BioETL Simple | `bioetl-simple` | 1 | 5 | 5s | 1h | `records_processed_total` | Live-мониторинг текущего запуска |
| BioETL Overview | `bioetl-overview` | 1 | 8 | 30s | 6h | `records_processed_total`, `errors_total`, `pipeline_duration_seconds`, `batch_size_records`, `data_freshness_seconds`, `filter_ids_*` | Полный обзор пайплайнов |
| BioETL Overview v2 | `bioetl-overview-v2` | 2 | 7 | 30s | 7d | `records_processed_total`, `records_processed_created` | Обзор конкретного запуска |
| BioETL Data Quality | `bioetl-dq` | 1 | 4 | 30s | 6h | `pipeline_duration_seconds`, `records_processed_total`, `batch_size_records` | DQ мониторинг с перцентилями |
| BioETL Data Quality v2 | `bioetl-dq-v2` | 2 | 7 | 30s | 7d | `records_processed_total`, `records_processed_created` | DQ для конкретного запуска |
| BioETL Provider Health | `bioetl-provider-health` | 1 | 6 | 30s | 6h | `records_processed_total`, `batch_size_records` | Пропускная способность по стадиям |
| BioETL Provider Health v2 | `bioetl-provider-health-v2` | 2 | 9 | 30s | 7d | `adapter_request_duration_seconds`, `http_request_errors_total`, `records_processed_total`, `records_processed_created` | Латентность и ошибки по провайдерам |

---

## 27. Жизненный цикл метрики: от кода до графика

### 27.1 Шаг 1: Определение метрики в коде

Каждая метрика BioETL определяется в модуле `src/bioetl/infrastructure/observability/metrics.py` как глобальный объект `prometheus_client`. При импорте модуля объект метрики регистрируется в глобальном реестре Prometheus (`REGISTRY`). Это происходит однократно при загрузке модуля. Повторная регистрация метрики с тем же именем вызывает исключение `ValueError`, поэтому metrics.py импортируется только один раз через composition root.

```python
# metrics.py — определение метрики
from prometheus_client import Counter

RECORDS_PROCESSED_TOTAL = Counter(
    "bioetl_records_processed_total",          # Имя метрики (prefix bioetl_)
    "Total number of records processed",        # HELP-строка (описание)
    ["pipeline", "stage", "run_type"],           # Labels (измерения)
)
```

Имена метрик следуют конвенциям Prometheus: prefix `bioetl_` для namespace, snake_case, суффикс `_total` для Counter, суффикс `_seconds` для Histogram с длительностями, суффикс `_bytes` для Histogram с размерами.

### 27.2 Шаг 2: Маппинг в PrometheusMetrics adapter

Класс `PrometheusMetrics` реализует `MetricsPort` и содержит три словаря (`COUNTERS`, `HISTOGRAMS`, `GAUGES`), маппящие строковые имена на объекты метрик. Это позволяет application-коду обращаться к метрикам по строковому имени, не импортируя infrastructure-модули:

```python
# prometheus_metrics.py
COUNTERS = {
    "records_processed_total": RECORDS_PROCESSED_TOTAL,
    "errors_total": ERRORS_TOTAL,
    # ...
}

def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
    counter = self.COUNTERS.get(name)
    if counter:
        counter.labels(**labels).inc(value)
```

Этот маппинг обеспечивает decoupling: application-код работает с абстрактным `MetricsPort`, а конкретная реализация (Prometheus, StatsD, NoOp) определяется в composition root при сборке зависимостей.

### 27.3 Шаг 3: Инструментация в application-коде

Application-код вызывает методы `MetricsPort` в ключевых точках пайплайна. Пример инструментации Bronze-стадии:

```python
# В PipelineRunner (application layer)
async def _process_bronze(self, records: list[dict]) -> int:
    count = len(records)
    await self._bronze_writer.write(records)
    self._metrics.increment_counter(
        "records_processed_total",
        value=count,
        labels={"pipeline": self._pipeline_name, "stage": "bronze", "run_type": self._run_type},
    )
    return count
```

Каждый вызов `increment_counter` увеличивает значение Counter на указанную величину для конкретной комбинации labels. Таким образом, одна метрика `records_processed_total` хранит независимые time series для каждого пайплайна, стадии и типа запуска.

### 27.4 Шаг 4: HTTP-экспорт

Метрический сервер (реализованный в `server.py`) запускает HTTP-сервер на порту 8000 в daemon-потоке. При получении GET-запроса на `/metrics` Prometheus client library автоматически сериализует все зарегистрированные метрики в текстовый формат exposition:

```
# HELP bioetl_records_processed_total Total number of records processed
# TYPE bioetl_records_processed_total counter
bioetl_records_processed_total{pipeline="chembl",stage="bronze",run_type="incremental"} 15420.0
bioetl_records_processed_total{pipeline="chembl",stage="silver",run_type="incremental"} 15380.0
bioetl_records_processed_total{pipeline="chembl",stage="gold",run_type="incremental"} 15102.0
bioetl_records_processed_total{pipeline="chembl",stage="quarantined",run_type="incremental"} 278.0
bioetl_records_processed_total_created{pipeline="chembl",stage="bronze",run_type="incremental"} 1.7087e+09
```

Сервер поддерживает idempotent startup: повторный вызов `start_metrics_server()` не запускает второй HTTP-сервер. При занятости порта выполняется retry с увеличением номера порта. При невозможности запуска (все порты заняты) применяется graceful degradation: пайплайн продолжает работу без экспорта метрик, если `fail_fast=false`.

### 27.5 Шаг 5: Prometheus scraping

Prometheus каждые 15 секунд (настраивается в `grafana/prometheus.yml` через `scrape_interval`) выполняет HTTP GET к BioETL metrics endpoint. Полученные данные парсятся и сохраняются в TSDB (Time Series Database) с текущим timestamp. Каждая уникальная комбинация метрики и labels образует отдельную time series.

Prometheus использует pull-модель: приложение не знает о существовании Prometheus. Оно просто экспортирует текущее состояние метрик по HTTP. Prometheus сам приходит и забирает данные. Эта модель имеет несколько преимуществ перед push-моделью:

- **Независимость:** Приложение работает даже если Prometheus недоступен. Метрики просто не собираются, но пайплайн не затрагивается.
- **Обнаружение проблем:** Если target перестаёт отвечать, Prometheus автоматически помечает его как DOWN и может генерировать алерт.
- **Контроль нагрузки:** Частота scrape контролируется на стороне Prometheus, а не приложения. Можно уменьшить `scrape_interval` без изменения кода приложения.

### 27.6 Шаг 6: PromQL-запрос в Grafana

Когда пользователь открывает дашборд, Grafana отправляет PromQL-запросы к Prometheus HTTP API. Prometheus выполняет запрос над сохранёнными time series и возвращает результат в JSON-формате. Grafana рендерит результат в виде графиков, stat-панелей, gauge, piechart и других визуализаций.

Цепочка данных для одной панели выглядит так:

```
Application code → increment_counter("records_processed_total", ...) →
→ In-memory Counter object → HTTP /metrics (text format) →
→ Prometheus scrape (каждые 15 сек) → TSDB storage →
→ Grafana PromQL query → HTTP API response (JSON) →
→ Panel render (SVG/Canvas) → Browser display
```

Задержка от момента инструментации до отображения на дашборде складывается из:
- Интервал scrape: до 15 секунд
- Обработка Prometheus: <1 секунда
- Refresh дашборда: до 5 секунд (Simple) или до 30 секунд (остальные)
- Итого: максимальная задержка ~50 секунд для обычных дашбордов, ~20 секунд для Simple

---

## 28. Безопасность и production-конфигурация

### 28.1 Ограничение доступа к Grafana

По умолчанию Grafana доступна без аутентификации (`GF_AUTH_ANONYMOUS_ENABLED=true`). Это подходит для локальной разработки, но в production необходимо включить аутентификацию:

```yaml
# docker-compose.monitoring.yml — production конфигурация
environment:
  GF_AUTH_ANONYMOUS_ENABLED: "false"
  GF_SECURITY_ADMIN_USER: "admin"
  GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_ADMIN_PASSWORD}"  # Из .env файла
  GF_USERS_ALLOW_SIGN_UP: "false"
```

Для организаций с SSO рекомендуется настроить OAuth2-интеграцию (поддерживаются Google, GitHub, LDAP, SAML).

### 28.2 Защита metrics endpoint

Metrics endpoint (`/metrics` на порту 8000) по умолчанию открыт без аутентификации. В production рекомендуется:

1. **Network isolation:** Ограничить доступ к порту 8000 через firewall rules. Только Prometheus должен иметь доступ.
2. **Reverse proxy:** Поставить nginx/Envoy перед metrics endpoint с basic auth.
3. **Prometheus basic auth:** Настроить аутентификацию в `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'bioetl'
    basic_auth:
      username: 'prometheus'
      password_file: '/etc/prometheus/password'
    static_configs:
      - targets: ['host.docker.internal:8000']
```

### 28.3 Label cardinality контроль

Высокая cardinality labels — главная угроза производительности Prometheus. Правила BioETL:

- **Запрещено** использовать уникальные ID (run_id, request_id, user_id) в labels. Каждое уникальное значение создаёт новую time series.
- **Допустимо:** pipeline (4-6 значений), stage (4 значения), run_type (3 значения), error_type (5-10 значений).
- **Мониторинг cardinality:** `prometheus_tsdb_head_series` показывает текущее количество active time series. Порог предупреждения: >10,000. Критический: >100,000.

Пример вычисления cardinality для `records_processed_total`:
- 4 пайплайна × 4 стадии × 3 типа запуска = 48 time series
- Плюс автоматически созданные `_created`: ещё 48
- Итого: 96 time series от одной метрики

Для всех 58+ метрик BioETL общая cardinality составляет 200-500 time series, что находится в безопасных пределах.

### 28.4 Retention и storage sizing

Prometheus хранит данные в локальной TSDB. Параметры по умолчанию:

- `--storage.tsdb.retention.time=15d` — хранение 15 дней
- `--storage.tsdb.retention.size` — не ограничено (по умолчанию)

Для production рекомендуется:
- Установить обе опции: `--storage.tsdb.retention.time=30d --storage.tsdb.retention.size=5GB`
- Использовать persistent volume для данных Prometheus (уже настроено в docker-compose.monitoring.yml: volume `prometheus-data`)
- Для долгосрочного хранения (месяцы/годы) использовать remote write в Thanos, Cortex или VictoriaMetrics

### 28.5 Horizontal scaling

При увеличении количества пайплайнов и провайдеров может потребоваться горизонтальное масштабирование мониторинга:

1. **Sharded Prometheus:** Несколько инстансов Prometheus, каждый скрейпит подмножество targets. Grafana использует datasource с type `prometheus` и настройкой `exemplarTraceIdDestinations` для корреляции.

2. **Federation:** Центральный Prometheus агрегирует данные из дочерних инстансов через `federation` endpoint.

3. **VictoriaMetrics:** Совместимая с Prometheus TSDB с более эффективным storage и встроенной поддержкой кластеризации. Замена datasource URL в Grafana на VictoriaMetrics endpoint (полностью совместим с PromQL).

---

## 29. Интеграция с CI/CD

### 29.1 Валидация дашбордов в CI

Для предотвращения поломки дашбордов при изменении метрик рекомендуется добавить в CI/CD pipeline:

```bash
# Валидация JSON-формата всех дашбордов
for f in grafana/dashboards/*.json; do
    python -m json.tool "$f" > /dev/null || { echo "FAIL: $f"; exit 1; }
done

# Проверка отсутствия phantom-метрик (метрик, не определённых в коде)
# Извлечение имён метрик из дашбордов:
grep -ohP 'bioetl_[a-z_]+' grafana/dashboards/*.json | sort -u > /tmp/dashboard_metrics.txt

# Извлечение определённых метрик из кода:
grep -ohP '"bioetl_[a-z_]+"' src/bioetl/infrastructure/observability/metrics.py | tr -d '"' | sort -u > /tmp/code_metrics.txt

# Поиск расхождений:
diff /tmp/dashboard_metrics.txt /tmp/code_metrics.txt
```

### 29.2 Smoke-тест мониторинга

После деплоя новой версии BioETL рекомендуется выполнить smoke-тест:

```bash
# 1. Проверить доступность metrics endpoint
curl -sf http://localhost:8000/metrics | grep -q "bioetl_" || echo "FAIL: metrics not available"

# 2. Проверить Prometheus target status
curl -sf http://localhost:9090/api/v1/targets | python -c "
import json, sys
data = json.load(sys.stdin)
targets = data['data']['activeTargets']
for t in targets:
    if 'bioetl' in t['labels'].get('job', ''):
        print(f\"{t['labels']['job']}: {t['health']}\")
        if t['health'] != 'up':
            sys.exit(1)
"

# 3. Проверить наличие данных в Prometheus
curl -sf 'http://localhost:9090/api/v1/query?query=bioetl_records_processed_total' | python -c "
import json, sys
data = json.load(sys.stdin)
if data['data']['result']:
    print(f\"Found {len(data['data']['result'])} time series\")
else:
    print('WARNING: No data yet (pipeline may not have run)')
"

# 4. Проверить доступность Grafana
curl -sf http://localhost:3000/api/health | python -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Grafana: {data['database']}\" )
"
```

### 29.3 Обновление дашбордов при изменении метрик

При переименовании или удалении метрик в коде необходимо синхронно обновить все дашборды. Рекомендуемый workflow:

1. Найти все использования метрики в дашбордах:
   ```bash
   grep -rn "old_metric_name" grafana/dashboards/
   ```
2. Обновить PromQL-запросы в соответствующих JSON-файлах.
3. Обновить каталог метрик в документации (раздел 5 этого документа).
4. Запустить CI-валидацию (раздел 29.1).
5. Выполнить smoke-тест (раздел 29.2).

---

**Конец документа.**

*Версия 2.0.0. Обновлена 2026-02-22. Синхронизирована с RULES.md v5.24 и текущим состоянием дашбордов.*
