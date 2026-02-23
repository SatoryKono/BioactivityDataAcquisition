# BioETL Мониторинг: Полный индекс документации

**Дата:** 22 февраля 2026  
**Версия:** 1.0  
**Статус:** Complete

---

## 📚 Документация по мониторингу

### 🚀 Быстрый старт (5 минут)

**[grafana/README.md](../../../grafana/README.md)**
- Запуск через Docker Compose: `make monitoring-up`
- Проверка статуса контейнеров
- Основные URL (Prometheus, Grafana)
- Быстрое устранение проблем

### 📊 Извлечение данных и создание дашбордов

**[docs/03-guides/BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md](../BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md)** ⭐ НОВОЕ!
- Как запустить пайплайн с метриками
- Полная архитектура: BioETL → Prometheus → Grafana
- Создание дашбордов (UI, JSON, Provisioning)
- Примеры PromQL запросов
- Переменные фильтрации
- Troubleshooting гайд

### 📖 Использование дашбордов

**[docs/05-operations/01-monitoring-guide.md](../../../docs/05-operations/01-monitoring-guide.md)**
- Архитектура наблюдаемости (Pull model)
- Как использовать дашборды
- Динамическая фильтрация (Pipeline, Run Type)
- 4 основных дашборда
- Runbook для типичных проблем

### 📋 Каталог метрик

**[docs/03-guides/metrics-monitoring.md](../metrics-monitoring.md)**
- 90+ метрик BioETL
- Pipeline, Data Quality, Health, Adapter метрики
- Structured Logging (JSON schema)
- OpenTelemetry Tracing
- Health Checks endpoints
- AlertManager правила

### 💡 Документация по дашбордам

**[docs/03-guides/dashbords/](../dashbords/)**

| Файл | Содержит |
|------|----------|
| **README.md** | Навигация и индекс всей документации |
| **BIOETL_DASHBOARD_SETUP.md** | Полная пошаговая инструкция (60 минут) |
| **BIOETL_DASHBOARD_VISUAL_GUIDE.md** | Диаграммы архитектуры, как читать графики |
| **BIOETL_DASHBOARD_QUICKSTART.md** | За 5 минут на вход |
| **VARIABLES_GUIDE.md** | Переменные Pipeline и Run Type |
| **TIMESTAMP_WITH_VARIABLES_FIX.md** | Исправление временных меток |
| **INFO_PANELS_ADDED.md** | Информационные панели |
| **DASHBOARD_V2_USAGE.md** | Как использовать v2 дашборды |

---

## 🔄 Полный цикл работы

```
1. Запустить мониторинг
   docker compose -f docker-compose.monitoring.yml up -d
   
2. Запустить пайплайн
   bioetl run --pipeline chembl-activity
   
3. Prometheus собирает метрики (каждые 15 сек)
   из http://localhost:8000/metrics
   
4. Открыть Grafana
   http://localhost:3000 (admin/admin)
   
5. Выбрать дашборд
   Home → Dashboards → BioETL → выбрать
```

---

## 📍 Где находятся метрики

```
┌─ BioETL Application ─────────────────┐
│                                      │
│  При запуске пайплайна               │
│  экспортирует метрики                │
│                                      │
└──────────────┬───────────────────────┘
               │
               ↓ HTTP GET (8000/metrics)
               │ Каждые 15 секунд
               │
┌──────────────┴───────────────────────┐
│  Prometheus Server (9090)            │
│                                      │
│  TSDB (Time-Series Database)         │
│  Хранит все метрики                  │
│                                      │
└──────────────┬───────────────────────┘
               │
               ↓ PromQL запросы
               │
┌──────────────┴───────────────────────┐
│  Grafana (3000)                      │
│                                      │
│  Визуализирует дашборды              │
│  Использует переменные фильтрации    │
│                                      │
└──────────────┬───────────────────────┘
               │
               ↓
        Web Browser
```

---

## 🎯 Типичные задачи

| Задача | Где найти |
|--------|----------|
| Как запустить мониторинг? | grafana/README.md |
| Как запустить пайплайн с метриками? | BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md |
| Как создать новый дашборд? | BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md |
| Какие метрики доступны? | metrics-monitoring.md |
| Как использовать фильтры? | VARIABLES_GUIDE.md |
| Как написать PromQL запрос? | BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md |
| Что делать если дашборд пуст? | BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md (Troubleshooting) |
| Как настроить алерты? | metrics-monitoring.md |
| Как читать графики? | BIOETL_DASHBOARD_VISUAL_GUIDE.md |

---

## 🔧 Конфигурационные файлы

| Файл | Назначение |
|------|-----------|
| **grafana/prometheus.yml** | Conфиг Prometheus (targets, scrape interval) |
| **docker-compose.monitoring.yml** | Запуск Prometheus и Grafana |
| **grafana/dashboards/** | JSON дашборды |
| **grafana/provisioning/** | Provisioning (auto-import dashboards) |
| **.env** | Переменные окружения (BIOETL_METRICS_*) |

---

## 📊 Метрики, используемые в дашбордах

**Pipeline Metrics (Simple, DQ v2, Overview v2):**
- `bioetl_records_processed_total` — обработанные записи (labels: pipeline, run_type, stage, status)
- `bioetl_records_processed_created` — timestamp создания метрики

**Health Metrics (Provider Health v2):**
- `bioetl_health_check_status` — статус health check (label: component)
- `bioetl_health_check_latency_ms` — latency provider'а (histogram, label: provider)
- `bioetl_health_check_latency_ms_created` — timestamp метрики latency

---

## 🎓 Уровни сложности

### 🟢 Новичок (15 минут)
1. Прочитать: grafana/README.md
2. Запустить: `make monitoring-up`
3. Открыть: http://localhost:3000
4. Выбрать дашборд

### 🟡 Intermediate (1 час)
1. Прочитать: BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md
2. Запустить пайплайн: `bioetl run --pipeline chembl-activity`
3. Проверить метрики в Prometheus
4. Создать простой дашборд через UI

### 🔴 Advanced (2+ часа)
1. Прочитать: metrics-monitoring.md (каталог метрик)
2. Прочитать: VARIABLES_GUIDE.md (переменные фильтрации)
3. Создать JSON дашборд с provisioning
4. Написать PromQL запросы с aggregation
5. Настроить AlertManager правила

---

## 🔗 Быстрые ссылки

**Сервисы:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- BioETL Metrics: http://localhost:8000/metrics

**Prometheus UI:**
- Status → Targets: http://localhost:9090/targets
- Explore: http://localhost:9090/graph

**Grafana UI:**
- Explore: http://localhost:3000/explore
- Dashboards: http://localhost:3000/dashboards
- Data Sources: http://localhost:3000/connections/datasources

---

## ✅ Чек-лист для получения данных

- [ ] Метрики включены в .env: `BIOETL_METRICS_ENABLED=true`
- [ ] Prometheus запущен: `docker ps | grep prometheus`
- [ ] Grafana запущена: `docker ps | grep grafana`
- [ ] Пайплайн запущен: `bioetl run --pipeline <name>`
- [ ] Метрики доступны: `curl http://localhost:8000/metrics`
- [ ] Target UP в Prometheus: http://localhost:9090/targets
- [ ] Дашборд загружен: http://localhost:3000/dashboards
- [ ] Данные видны на графиках

---

## 📝 Последние обновления

✅ Создана новая документация: **BIOETL_DATA_EXTRACTION_AND_DASHBOARDS.md**
- Полный цикл: запуск пайплайна → метрики → дашборды
- Примеры PromQL запросов
- Шаблоны JSON дашбордов
- Troubleshooting гайд

✅ Дашборды v2 с переменными:
- BioETL Data Quality v2
- BioETL Overview v2
- BioETL Provider Health v2

---

**Версия:** 1.0  
**Дата:** 22 февраля 2026  
**Статус:** Production Ready
