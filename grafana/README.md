# Grafana-дашборды для BioETL

Локальный мониторинг пайплайнов BioETL через Prometheus + Grafana.

## Обзор

BioETL экспортирует 40+ Prometheus-метрик на `http://localhost:8000/metrics`.
Три дашборда визуализируют ключевые аспекты:

| Дашборд | Файл | Что показывает |
|---------|------|----------------|
| **Overview** | `bioetl-overview.json` | Скорость обработки, ошибки, статус пайплайнов |
| **Provider Health** | `bioetl-provider-health.json` | Здоровье провайдеров, состояние Circuit Breaker |
| **Data Quality** | `bioetl-dq.json` | DQ-метрики, карантин, аномалии, длительность проверок |

---

## 1. Предварительные требования

- **BioETL** запущен с метриками (по умолчанию включены)
- Метрики доступны на `http://localhost:8000/metrics`
- Порт настраивается через переменную `BIOETL_METRICS_PORT`

Проверка:

```bash
curl http://localhost:8000/metrics
# Должны появиться строки вида: bioetl_records_processed_total{...}
```

---

## 2. Установка Prometheus

### Windows

1. Скачать последний релиз: https://github.com/prometheus/prometheus/releases
   - Файл `prometheus-*-windows-amd64.zip`
2. Распаковать в удобную директорию (например, `C:\tools\prometheus\`)
3. Запустить с конфигом BioETL:

```cmd
cd C:\tools\prometheus
prometheus.exe --config.file=<путь-к-репозиторию>\grafana\prometheus.yml
```

4. Открыть http://localhost:9090 — интерфейс Prometheus
5. Перейти в **Status > Targets** — target `bioetl` должен быть в состоянии **UP**

### Linux / macOS

```bash
# Linux (apt)
sudo apt install prometheus

# macOS (brew)
brew install prometheus

# Запуск
prometheus --config.file=grafana/prometheus.yml
```

---

## 3. Установка Grafana

### Windows

1. Скачать: https://grafana.com/grafana/download?platform=windows
   - ZIP-архив или MSI-установщик
2. Запустить `grafana-server.exe` (из `bin/`)
3. Открыть http://localhost:3000 (логин: `admin` / пароль: `admin`)

### Linux / macOS

```bash
# Linux (apt)
sudo apt install grafana
sudo systemctl start grafana-server

# macOS (brew)
brew install grafana
brew services start grafana
```

---

## 4. Настройка Datasource

1. Открыть Grafana: http://localhost:3000
2. Перейти в **Connections > Data sources > Add data source**
3. Выбрать **Prometheus**
4. Указать URL: `http://localhost:9090`
5. Нажать **Save & Test** — должно быть "Successfully queried the Prometheus API"

---

## 5. Импорт дашбордов

### Вариант A: Ручной импорт (рекомендуется)

1. Перейти в **Dashboards > New > Import**
2. Нажать **Upload JSON file**
3. Загрузить файлы из `grafana/dashboards/`:
   - `bioetl-overview.json`
   - `bioetl-provider-health.json`
   - `bioetl-dq.json`
4. Выбрать datasource **Prometheus** при импорте

### Вариант B: Автопровизионирование

Скопировать содержимое `grafana/provisioning/` в директорию провизионирования Grafana:

```cmd
:: Windows (путь зависит от способа установки)
xcopy /E grafana\provisioning C:\tools\grafana\conf\provisioning\
xcopy /E grafana\dashboards C:\tools\grafana\dashboards\bioetl\
```

Отредактировать `grafana/provisioning/dashboards/bioetl.yaml` — указать
абсолютный путь к папке `grafana/dashboards/` в поле `options.path`.

Перезапустить Grafana — дашборды появятся автоматически в папке "BioETL".

---

## 6. Проверка работоспособности

| Шаг | URL | Ожидание |
|-----|-----|----------|
| Метрики BioETL | http://localhost:8000/metrics | Строки `bioetl_*` |
| Prometheus targets | http://localhost:9090/targets | Target `bioetl` = UP |
| Grafana | http://localhost:3000 | Дашборды с данными |

---

## Описание дашбордов

### 1. BioETL Overview (`bioetl-overview.json`)

Высокоуровневый обзор работы пайплайнов:
- **Records Processed** — скорость обработки записей (`rate(bioetl_records_processed_total[5m])`)
- **Error Rates** — частота ошибок по типам (`rate(bioetl_errors_total[5m])`)

### 2. Provider Health (`bioetl-provider-health.json`)

Мониторинг внешних провайдеров данных:
- **Health Status** — таблица состояний: Healthy / Degraded / Unhealthy
- **Circuit Breakers** — состояние circuit breaker (Closed / Open / Half-Open)

### 3. Data Quality (`bioetl-dq.json`)

Качество данных (10 панелей):
- **DQ Validation Score** — общая оценка качества (0.0 — 1.0)
- **Data Freshness** — время с последнего обновления
- **Quarantine Records** — количество записей в карантине
- **DQ Score Over Time** — динамика оценки качества
- **Quarantine Rate** — скорость попадания в карантин
- **Anomalies** — обнаруженные аномалии
- **DQ Check Duration** — длительность проверок (p50/p95/p99)
- **Quarantine by Error Type** — распределение ошибок по типам
- **DQ Baseline Samples** — количество baseline-сэмплов
- **Quarantine Details** — таблица карантинных записей
