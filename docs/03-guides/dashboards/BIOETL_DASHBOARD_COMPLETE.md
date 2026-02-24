# 📊 BioETL Dashboard — Полная подготовка завершена ✅

> **Path verification (required):** before applying this guide/prompt, locate the runtime observability modules with `rg -n "PrometheusMetrics|start_http_server|metrics_server_integration" src/bioetl`.
> Use these runtime paths:
> Metric definitions/registries — `src/bioetl/infrastructure/observability/metrics.py`, `src/bioetl/infrastructure/observability/prometheus_metrics.py`.
> Metrics server wiring/integration — `src/bioetl/infrastructure/observability/metrics_server_adapter.py`, `src/bioetl/interfaces/cli/commands/metrics_server_integration.py`.

**Дата:** 22 февраля 2026
**Время подготовки:** ~1 час
**Статус:** ✅ Готово к производству

______________________________________________________________________

## 📋 Что было подготовлено

### 📚 Документация (1,800+ строк)

| Документ                             | Размер    | Аудитория            | Содержание            |
| ------------------------------------ | --------- | -------------------- | --------------------- |
| **BIOETL_DASHBOARD_README.md**       | 264 строк | 🗺️ Все               | Навигация и индекс    |
| **BIOETL_DASHBOARD_QUICKSTART.md**   | 148 строк | 🚀 Разработчики      | За 5 минут на вход    |
| **BIOETL_DASHBOARD_SETUP.md**        | 572 строк | 📖 Полная инструкция | Все детали (60 минут) |
| **BIOETL_DASHBOARD_VISUAL_GUIDE.md** | 278 строк | 👁️ Визуалы           | Диаграммы и примеры   |
| **BIOETL_DASHBOARD_EXAMPLES.md**     | 529 строк | 💡 Кастомизация      | Примеры и расширение  |

**Итого:** ~1,800 строк документации

### 🛠️ Рабочие файлы

| Файл                                                              | Назначение                              | Статус        |
| ----------------------------------------------------------------- | --------------------------------------- | ------------- |
| **src/bioetl/infrastructure/observability/prometheus_metrics.py** | Prometheus metrics endpoint             | ✅ Работает   |
| **docker-compose.monitoring.yml**                                 | Docker контейнеры (Prometheus, Grafana) | ✅ Готов      |
| **grafana/prometheus.yml**                                        | Конфигурация Prometheus                 | ✅ Настроен   |
| **grafana/provisioning/**                                         | Auto-provisioning дашбордов             | ✅ 4 дашборда |

### 📊 Компоненты инфраструктуры

| Компонент          | Порт | Статус     | URL                           |
| ------------------ | ---- | ---------- | ----------------------------- |
| **BioETL Metrics** | 8000 | ✅ Запущен | http://localhost:8000/metrics |
| **Prometheus**     | 9090 | ✅ Запущен | http://localhost:9090         |
| **Grafana**        | 3000 | ✅ Запущен | http://localhost:3000         |
| **Neo4j** (опция)  | 7687 | ✅ Запущен | http://localhost:7474         |

### 📊 Дашборды (4 штуки)

| №   | Дашборд                   | UID                       | Панели | Назначение                   |
| --- | ------------------------- | ------------------------- | ------ | ---------------------------- |
| 1   | BioETL Simple             | bioetl-simple             | 5      | Основная статистика          |
| 2   | BioETL Data Quality v2    | bioetl-dq-v2              | 7      | Метрики качества данных      |
| 3   | BioETL Overview v2        | bioetl-overview-v2        | 7      | Общий обзор pipeline         |
| 4   | BioETL Provider Health v2 | bioetl-provider-health-v2 | 9      | Статус и latency provider'ов |

**Итого:** 4 полнофункциональных дашборда

______________________________________________________________________

## 🚀 Состояние готовности

### ✅ Установка

- [x] Docker Compose конфигурация
- [x] Prometheus настроен
- [x] Grafana подключена
- [x] Metrics сервер работает
- [x] Дашборды загружены

### ✅ Конфигурация

- [x] Prometheus scrape: 15 сек
- [x] Retention: 15 дней
- [x] Data source: http://host.docker.internal:9090
- [x] Provisioning: автоматическое
- [x] Переменные фильтров: Pipeline, Run Type, Execution

### ✅ Мониторинг

- [x] Метрики собираются ✅
- [x] Дашборды отображают данные ✅
- [x] Фильтры работают ✅
- [x] Обновление: каждые 15 сек ✅

### ✅ Документация

- [x] Быстрый старт (5 минут)
- [x] Полная инструкция (60 минут)
- [x] Визуальный гайд (диаграммы)
- [x] Примеры кастомизации
- [x] Troubleshooting guide

______________________________________________________________________

## 🎯 Как использовать

### Шаг 1: Быстрый старт (5 минут)

```bash
# Прочитать
cat BIOETL_DASHBOARD_QUICKSTART.md

# Запустить контейнеры
docker compose -f docker-compose.monitoring.yml up -d

# Запустить metrics сервер
python ./src/bioetl/infrastructure/observability/prometheus_metrics.py &

# Открыть
http://localhost:3000/d/bioetl-simple
```

### Шаг 2: Изучить документацию

```
1. README (навигация) — 5 минут
2. QUICKSTART (за 5 минут) — 10 минут
3. VISUAL_GUIDE (диаграммы) — 20 минут
4. SETUP (полная инструкция) — 60 минут
5. EXAMPLES (кастомизация) — 30 минут
```

### Шаг 3: Использовать дашборды

```
1. Открыть http://localhost:3000
2. Выбрать Dashboard → BioETL
3. Выбрать нужный дашборд
4. Использовать фильтры (Pipeline, Run Type)
5. Экспортировать данные при необходимости
```

### Шаг 4: Кастомизировать (опционально)

```
1. Добавить метрики в src/bioetl/infrastructure/observability/prometheus_metrics.py
2. Создать собственный дашборд
3. Настроить alerts
4. Интегрировать с Slack/Email
```

______________________________________________________________________

## 📊 Текущие метрики

### Доступные метрики:

```
✅ bioetl_records_processed_total
   - pipeline (uniprot, pubmed, pubchem, chembl)
   - run_type (incremental, backfill, rebuild)
   - stage (bronze, silver, gold)
   - status (success, error)

✅ bioetl_records_processed_created
   - pipeline, run_type
   - Timestamp создания метрики (для Execution Timestamp панели)

✅ bioetl_health_check_status
   - component
   - Статус health check (1=healthy)

✅ bioetl_health_check_latency_ms
   - provider (uniprot, pubmed, pubchem, chembl)
   - Histogram с buckets для P95 latency
```

### Типичные запросы (PromQL):

```promql
# Текущие значения
sum(bioetl_records_processed_total) by (stage)

# Скорость обработки (records/min)
sum(rate(bioetl_records_processed_total[1m])) by (pipeline)

# Quality ratio (Gold/Bronze)
sum(bioetl_records_processed_total{stage="gold"}) / sum(bioetl_records_processed_total{stage="bronze"})

# P95 latency provider'а
histogram_quantile(0.95, bioetl_health_check_latency_ms_bucket{provider="chembl"})
```

______________________________________________________________________

## 🔧 Кастомизация

### Добавить метрику:

1. Отредактировать `src/bioetl/infrastructure/observability/prometheus_metrics.py`
1. Добавить Counter/Gauge/Histogram
1. Перезапустить сервер
1. Использовать в Grafana

### Создать дашборд:

1. Открыть Grafana → Dashboards → New
1. Добавить панели
1. Настроить queries
1. Сохранить

### Настроить alert:

1. Dashboard → Alert rules
1. Create alert rule
1. Set condition (например, error_rate > 10%)
1. Выбрать notification channel

______________________________________________________________________

## 🐛 Troubleshooting

### Если не работает:

1. **Дашборд пуст (No data)**

   ```bash
   # Проверить metrics сервер
   curl http://localhost:8000/metrics

   # Если ошибка, перезапустить
   pkill -f src/bioetl/infrastructure/observability/prometheus_metrics.py
   python ./src/bioetl/infrastructure/observability/prometheus_metrics.py &
   ```

1. **Prometheus target DOWN**

   ```bash
   # Проверить логи
   docker logs bioetl-prometheus | tail -20

   # Перезапустить
   docker restart bioetl-prometheus
   ```

1. **Grafana не подключается**

   ```bash
   # Проверить URL в Data Sources
   # http://host.docker.internal:9090

   # Или для Linux:
   # http://prometheus:9090 (если в одной сети)
   ```

______________________________________________________________________

## 📈 Производительность

| Метрика          | Значение      |
| ---------------- | ------------- |
| Scrape interval  | 15 сек        |
| Query timeout    | 10 сек        |
| Retention        | 15 дней       |
| Prometheus RAM   | ~500 MB       |
| Grafana RAM      | ~300 MB       |
| Metrics endpoint | ~50 KB/запрос |

______________________________________________________________________

## 🎓 Обучение

### Для новичков (40 минут):

1. Прочитать VISUAL_GUIDE.md — 20 минут
1. Открыть BioETL Simple Dashboard — 10 минут
1. Поменять фильтры — 10 минут

### Для intermediate (1.5 часа):

1. Прочитать SETUP.md — 60 минут
1. Написать PromQL query — 20 минут
1. Добавить панель в дашборд — 10 минут

### Для advanced (2+ часа):

1. Прочитать EXAMPLES.md — 30 минут
1. Добавить свою метрику — 30 минут
1. Создать дашборд с JSON — 30 минут
1. Настроить alerts — 30 минут

______________________________________________________________________

## 📞 Справка

### Основные файлы

- `BIOETL_DASHBOARD_QUICKSTART.md` — Начните отсюда ⭐
- `BIOETL_DASHBOARD_README.md` — Индекс всей документации
- `BIOETL_DASHBOARD_SETUP.md` — Полная инструкция
- `BIOETL_DASHBOARD_VISUAL_GUIDE.md` — Диаграммы и примеры
- `BIOETL_DASHBOARD_EXAMPLES.md` — Кастомизация

### Основные URL

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Metrics: http://localhost:8000/metrics

### Основные команды

```bash
# Запустить
docker compose -f docker-compose.monitoring.yml up -d
python ./src/bioetl/infrastructure/observability/prometheus_metrics.py &

# Остановить
docker compose -f docker-compose.monitoring.yml down
pkill -f src/bioetl/infrastructure/observability/prometheus_metrics.py

# Диагностика
curl http://localhost:9090/-/healthy
curl http://localhost:8000/metrics
```

______________________________________________________________________

## ✨ Что дальше?

### Базовое (0-2 часа):

- [ ] Установить мониторинг (QUICKSTART.md)
- [ ] Открыть http://localhost:3000
- [ ] Исследовать дашборды

### Промежуточное (2-4 часа):

- [ ] Прочитать SETUP.md
- [ ] Понять архитектуру
- [ ] Написать PromQL query
- [ ] Добавить панель

### Продвинутое (4+ часа):

- [ ] Добавить собственные метрики
- [ ] Создать дашборд с JSON
- [ ] Настроить alerts
- [ ] Интегрировать с Slack

______________________________________________________________________

## 🎉 Итог

Вы получили:

✅ **Полнофункциональный мониторинг** — 3 компонента (Prometheus, Grafana, Metrics Server)

✅ **4 готовых дашборда** — с базовыми метриками и фильтрами

✅ **1800+ строк документации** — от быстрого старта до advanced кастомизации

✅ **Примеры и шаблоны** — для собственной кастомизации

✅ **Диаграммы и визуалы** — для понимания архитектуры

✅ **Troubleshooting гайд** — решение типичных проблем

______________________________________________________________________

## 🚀 Начните сейчас!

**Вариант 1: Быстрый старт (5 минут)**

```bash
cat BIOETL_DASHBOARD_QUICKSTART.md
docker compose -f docker-compose.monitoring.yml up -d
python ./src/bioetl/infrastructure/observability/prometheus_metrics.py &
open http://localhost:3000
```

**Вариант 2: Полная подготовка (2 часа)**

```bash
cat BIOETL_DASHBOARD_SETUP.md          # 60 минут
cat BIOETL_DASHBOARD_VISUAL_GUIDE.md   # 20 минут
# Следовать инструкциям                # 40 минут
open http://localhost:3000/d/bioetl-simple
```

______________________________________________________________________

## 📞 Контакты для вопросов

Все ответы в документации:

- **Установка** → QUICKSTART.md
- **Проблемы** → SETUP.md (Troubleshooting)
- **Как использовать** → VISUAL_GUIDE.md
- **Кастомизация** → EXAMPLES.md

______________________________________________________________________

**Статус:** ✅ Готово к использованию
**Версия документации:** 1.0
**Последнее обновление:** 22 февраля 2026

🎊 **Спасибо за использование BioETL Dashboard!** 🎊

Начните с [BIOETL_DASHBOARD_QUICKSTART.md](./BIOETL_DASHBOARD_QUICKSTART.md) прямо сейчас! ⏱️
