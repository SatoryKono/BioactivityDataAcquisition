# BioETL Dashboard — Подробная инструкция по настройке

**Дата:** 22 февраля 2026  
**Версия:** 1.0  
**Автор:** Docker Assistant  

## Содержание
1. [Быстрый старт (5 минут)](#быстрый-старт)
2. [Архитектура мониторинга](#архитектура-мониторинга)
3. [Пошаговая установка](#пошаговая-установка)
4. [Конфигурация компонентов](#конфигурация-компонентов)
5. [Использование дашбордов](#использование-дашбордов)
6. [Кастомизация и расширение](#кастомизация-и-расширение)
7. [Troubleshooting](#troubleshooting)

---

## Быстрый старт

### Требования
- Docker & Docker Compose
- Python 3.11+ (для BioETL metrics сервера)
- 2GB свободной памяти
- Порты: 3000 (Grafana), 9090 (Prometheus), 8000 (BioETL metrics)

### За 5 минут

```bash
# 1. Запустить контейнеры мониторинга
docker compose -f docker-compose.monitoring.yml up -d

# 2. Запустить Prometheus metrics сервер (в фоне)
python ./metrics_server.py &

# 3. Открыть Grafana
# Браузер: http://localhost:3000
# Логин: admin
# Пароль: admin
```

✅ **Готово!** Дашборды доступны на http://localhost:3000/d/bioetl-simple

---

## Архитектура мониторинга

```
┌─────────────────────────────────────────────────────────┐
│                    BioETL Pipeline                      │
│           Генерирует метрики в Prometheus               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓ HTTP GET /metrics
┌─────────────────────────────────────────────────────────┐
│         Prometheus Metrics Endpoint (8000)              │
│  - bioetl_records_processed_total                       │
│  - bioetl_processing_duration_seconds                   │
│  - bioetl_error_rate                                    │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ↓ Scrape каждые 15 сек    ↓ Query для графиков
┌──────────────────────┐   ┌─────────────────────────┐
│   Prometheus 9090    │   │   Grafana 3000          │
│  - Хранилище TSDB    │   │  - 4 дашборда            │
│  - Retention: 15 дней│   │  - Переменные фильтры   │
│  - Scrape interval: 15s │  - Alerts & Annotations │
└──────────┬───────────┘   └──────────┬──────────────┘
           │                          │
           └──────────────┬───────────┘
                          │
                   ↓ Визуализация
            Панели с графиками, таблицы,
            калибраторы, статистика
```

### Компоненты

| Компонент | Порт | Назначение | URL |
|-----------|------|-----------|-----|
| **BioETL App** | 8000 | Генерирует метрики (Prometheus format) | http://localhost:8000/metrics |
| **Prometheus** | 9090 | Собирает и хранит метрики TSDB | http://localhost:9090 |
| **Grafana** | 3000 | Визуализирует метрики в дашборды | http://localhost:3000 |
| **Neo4j** | 7687 | База данных графов (опционально) | http://localhost:7474 |

---

## Пошаговая установка

### Шаг 1: Подготовка окружения

```bash
# Перейти в папку проекта
cd /path/to/BioactivityDataAcquisition2

# Проверить Python версию
python --version
# Output: Python 3.13.x

# Установить зависимости BioETL
pip install -e .

# Проверить, что prometheus-client установлен
python -c "import prometheus_client; print('OK')"
```

### Шаг 2: Запустить контейнеры мониторинга

```bash
# Запустить Prometheus и Grafana в docker-compose
docker compose -f docker-compose.monitoring.yml up -d

# Проверить статус
docker compose -f docker-compose.monitoring.yml ps

# Output:
# NAME                 STATUS              PORTS
# bioetl-prometheus    Up 2 minutes        0.0.0.0:9090->9090/tcp
# bioetl-grafana       Up 2 minutes        3000/tcp
# bioetl-neo4j         Up 2 minutes        7687/tcp
```

### Шаг 3: Запустить BioETL Metrics сервер

**Вариант A: Запустить в фоне (рекомендуется для разработки)**

```bash
# Запустить metrics сервер в фоне
python ./metrics_server.py &

# Проверить, что работает
curl http://localhost:8000/metrics | head -20
```

**Вариант B: Запустить через systemd (для production)**

```bash
# Создать systemd service
sudo tee /etc/systemd/system/bioetl-metrics.service > /dev/null << 'EOF'
[Unit]
Description=BioETL Prometheus Metrics Server
After=network.target

[Service]
Type=simple
User=bioetl
WorkingDirectory=/opt/bioetl
ExecStart=/usr/bin/python3 /opt/bioetl/metrics_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Загрузить и запустить
sudo systemctl daemon-reload
sudo systemctl enable bioetl-metrics
sudo systemctl start bioetl-metrics
```

**Вариант C: Запустить через Docker контейнер**

```bash
# Создать Dockerfile для metrics сервера
cat > Dockerfile.metrics << 'EOF'
FROM python:3.13-slim
WORKDIR /app
RUN pip install prometheus-client
COPY metrics_server.py .
EXPOSE 8000
CMD ["python", "metrics_server.py"]
EOF

# Собрать и запустить
docker build -f Dockerfile.metrics -t bioetl-metrics:latest .
docker run -d --name bioetl-metrics \
  -p 8000:8000 \
  bioetl-metrics:latest
```

### Шаг 4: Проверить подключение Prometheus

1. Открыть http://localhost:9090/targets
2. Проверить статус target `bioetl`:
   - ✅ **UP** — всё работает
   - ❌ **DOWN** — проверить Шаг 3

### Шаг 5: Подключить Grafana к Prometheus

1. Открыть http://localhost:3000
2. Войти (admin/admin)
3. Перейти: **Configuration → Data Sources**
4. Проверить, что Prometheus уже добавлен:
   - **Name:** Prometheus
   - **URL:** http://host.docker.internal:9090
   - **Status:** ✅ Green (ready)

Если не добавлен:
- Кликнуть **Add data source**
- Выбрать **Prometheus**
- Заполнить URL: `http://host.docker.internal:9090`
- Кликнуть **Save & test**

### Шаг 6: Проверить дашборды

1. Перейти: http://localhost:3000/dashboards
2. Нажать **Browse**
3. Выбрать папку **BioETL**
4. Открыть **BioETL Simple Dashboard**

✅ Дашборд должен показывать данные (графики, статистика)

---

## Конфигурация компонентов

### Prometheus (prometheus.yml)

```yaml
global:
  scrape_interval: 15s       # Как часто собирать метрики
  evaluation_interval: 15s   # Как часто вычислять правила
  external_labels:
    monitor: 'bioetl-monitor'

scrape_configs:
  - job_name: 'bioetl'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: /metrics
    scrape_interval: 15s
    scrape_timeout: 10s
```

**Параметры:**
- `scrape_interval`: Интервал сбора метрик (15s = каждые 15 секунд)
- `metrics_path`: Путь к метрикам (/metrics)
- `targets`: Адреса приложений для мониторинга

**Если изменить:**
```bash
# Отредактировать
nano ./grafana/prometheus.yml

# Перезагрузить Prometheus (он автоматически перечитает конфиг)
# Или перезапустить контейнер
docker restart bioetl-prometheus
```

### Grafana (docker-compose.monitoring.yml)

```yaml
grafana:
  image: grafana/grafana:latest
  container_name: bioetl-grafana
  ports:
    - "3000:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: admin    # Измени на production!
    GF_USERS_ALLOW_SIGN_UP: 'false'
    GF_INSTALL_PLUGINS: 'grafana-piechart-panel'
  volumes:
    - grafana_storage:/var/lib/grafana
    - ./grafana/provisioning:/etc/grafana/provisioning
  networks:
    - monitoring
```

**Важные переменные:**
- `GF_SECURITY_ADMIN_PASSWORD` — пароль admin
- `GF_USERS_ALLOW_SIGN_UP` — разрешить регистрацию пользователей

**Изменить пароль в production:**
```bash
# В docker-compose.monitoring.yml
environment:
  GF_SECURITY_ADMIN_PASSWORD: your_secure_password_here

# Перезапустить
docker compose -f docker-compose.monitoring.yml up -d
```

### BioETL Metrics Server (metrics_server.py)

```python
# Порт и адрес
HOST = '0.0.0.0'  # Слушать на всех интерфейсах
PORT = 8000       # Порт для метрик

# Метрики
RECORDS_PROCESSED = Counter(
    'bioetl_records_processed_total',
    'Total records processed',
    ['pipeline', 'run_id', 'stage', 'status']  # Labels
)
```

**Добавить собственную метрику:**
```python
from prometheus_client import Gauge

MY_METRIC = Gauge(
    'bioetl_my_metric',
    'My custom metric',
    ['pipeline', 'stage']
)

# В коде приложения:
MY_METRIC.labels(pipeline='uniprot', stage='bronze').set(value)
```

---

## Использование дашбордов

### Доступные дашборды

1. **BioETL Simple Dashboard** (`bioetl-simple`)
   - Bronze/Silver/Gold Records (текущие значения)
   - Quality Ratio (процент качества)
   - Live график по стадиям обработки

2. **BioETL Overview** (`bioetl-overview`)
   - Общая статистика по всем pipeline
   - Тренды обработки данных
   - Error rate по компонентам

3. **BioETL Data Quality v2** (`bioetl-dq-v2`)
   - Метрики качества данных
   - Аномалии и отклонения
   - Исторические данные

4. **BioETL Provider Health** (`bioetl-provider-health`)
   - Статус каждого provider (UniProt, PubMed, PubChem, ChemBL)
   - Response time
   - Error rate

5. **BioETL Overview v2** (`bioetl-overview-v2`)
   - Advanced обзор
   - Custom фильтры
   - Drill-down аналитика

### Работа с фильтрами

Все дашборды имеют переменные для фильтрации:

**Pipeline** — выбрать pipeline
```
Доступные: uniprot, pubmed, pubchem, chembl, All
```

**Run Type** — выбрать тип запуска
```
Доступные: incremental, backfill, rebuild, All
```

**Пример использования:**
```
1. Открыть BioETL Simple Dashboard
2. В левой панели: Pipeline = "uniprot"
3. Run Type = "incremental"
4. График обновится и покажет только данные для uniprot
```

### Экспорт и обмен

**Экспортировать дашборд как JSON:**
```
Dashboard → Dashboard settings (⚙️) → JSON Model
→ Copy to clipboard → Сохранить в файл
```

**Импортировать дашборд:**
```
Home → Dashboards → New → Import
→ Paste JSON или загрузить файл
→ Select Prometheus data source
→ Import
```

**Поделиться ссылкой:**
```
Dashboard → Share (🔗)
→ Copy dashboard URL
→ Отправить коллеге
```

---

## Кастомизация и расширение

### Добавить новую метрику в Prometheus

**1. В BioETL приложении (например, в src/bioetl/interfaces/observability.py):**

```python
from prometheus_client import Counter, Gauge, Histogram

# Определить метрику
API_REQUESTS = Counter(
    'bioetl_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

RESPONSE_TIME = Histogram(
    'bioetl_api_response_time_seconds',
    'API response time',
    ['endpoint']
)

# В коде API:
API_REQUESTS.labels(
    endpoint='/fetch',
    method='GET',
    status='200'
).inc()

RESPONSE_TIME.labels(endpoint='/fetch').observe(duration)
```

**2. Prometheus автоматически подберёт новую метрику**

**3. Использовать в Grafana:**
```
Query: bioetl_api_requests_total
Legend: {{endpoint}} - {{status}}
```

### Создать собственный дашборд

**Вариант A: Через UI (простой)**

```
1. Home → Dashboards → New → Create New Dashboard
2. Add new panel → Choose visualization
3. Set query (Prometheus PromQL)
4. Customize display
5. Save dashboard
```

**Вариант B: Через JSON (advanced)**

```bash
# Создать dashboard JSON
cat > custom-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "My Custom Dashboard",
    "panels": [
      {
        "title": "Records Processed",
        "targets": [
          {
            "expr": "sum(bioetl_records_processed_total) by (pipeline)"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
EOF

# Импортировать в Grafana
# Home → Dashboards → Import
# Загрузить custom-dashboard.json
```

### Добавить Alert

```
1. Dashboard → Alert rules
2. Create new alert rule
3. Set condition: "if sum(bioetl_error_rate) > 0.1"
4. Set notification channel (Email, Slack, PagerDuty)
5. Save
```

### Provisioning (автоматическая загрузка дашбордов)

Grafana может автоматически загружать дашборды при старте.

**Текущая конфигурация в grafana/provisioning/dashboards/bioetl.yaml:**

```yaml
apiVersion: 1

providers:
  - name: 'BioETL'
    orgId: 1
    folder: 'BioETL'
    folderUid: 'bioetl'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

**Добавить свой дашборд в provisioning:**

```bash
# 1. Сохранить JSON дашборда
cp your-dashboard.json ./grafana/dashboards/

# 2. Перезапустить Grafana
docker restart bioetl-grafana

# 3. Дашборд автоматически загрузится и появится в папке BioETL
```

---

## Troubleshooting

### Проблема: Prometheus не подключается к метрикам

**Симптом:** Targets → bioetl = DOWN

**Решение:**
```bash
# 1. Проверить, работает ли metrics сервер
curl http://localhost:8000/metrics

# 2. Если curl не работает:
# a) Перезапустить metrics сервер
pkill -f metrics_server.py
python ./metrics_server.py &

# b) Проверить в логах контейнера Prometheus
docker logs bioetl-prometheus | tail -20

# 3. Проверить адрес в prometheus.yml
# Убедиться, что targets правильный:
# targets: ['host.docker.internal:8000']  # Для Docker на Windows/Mac
# targets: ['localhost:8000']  # Для Linux
```

### Проблема: Дашборд показывает "No data"

**Симптом:** График пуст, нет данных

**Решение:**
```bash
# 1. Проверить Prometheus query
# Home → Explore
# Query: bioetl_records_processed_total
# Если результат пуст → метрики не собираются

# 2. Проверить, генерируется ли метрика
curl http://localhost:8000/metrics | grep bioetl_records_processed

# 3. Если метрик нет → перезапустить metrics сервер
python ./metrics_server.py

# 4. Дождаться 15 сек (интервал scrape)
# затем обновить дашборд (F5)
```

### Проблема: Grafana не подключается к Prometheus

**Симптом:** Data source → Prometheus = Red (failed)

**Решение:**
```bash
# 1. Проверить, доступен ли Prometheus
curl http://localhost:9090/-/healthy

# 2. Проверить URL в Grafana
# Configuration → Data Sources → Prometheus
# Должно быть: http://host.docker.internal:9090 (или http://prometheus:9090)

# 3. Если контейнеры в разных сетях:
# Убедиться, что bioetl-grafana и bioetl-prometheus в одной сети
docker inspect bioetl-grafana | grep -A 5 "Networks"
docker inspect bioetl-prometheus | grep -A 5 "Networks"

# 4. Если в разных сетях → подключить к monitoring сети
docker network connect monitoring bioetl-grafana

# 5. В URL использовать имя сервиса (если в одной сети)
# http://bioetl-prometheus:9090
```

### Проблема: Много ошибок в логах Prometheus

```bash
# Посмотреть логи
docker logs bioetl-prometheus -f

# Типичные ошибки:
# "error reading Prometheus config"
# → Проверить синтаксис prometheus.yml (YAML)

# "error loading config"
# → Убедиться, что prometheus.yml существует и доступен

# Перезагрузить конфиг без перезапуска:
# POST http://localhost:9090/-/reload
```

### Проблема: Дашборд зависает при загрузке

**Решение:**
```bash
# 1. Открыть DevTools (F12 → Console)
# Проверить ошибки в консоли браузера

# 2. Очистить кэш Grafana
# Перейти в browser DevTools → Application → Clear site data

# 3. Если проблема в запросе Prometheus:
# Home → Explore
# Query: bioetl_records_processed_total
# Если запрос долго выполняется → увеличить retention в Prometheus
# или уменьшить временной диапазон (1h вместо 7d)

# 4. Перезапустить Grafana
docker restart bioetl-grafana
```

### Проблема: Забыл пароль Grafana

```bash
# Способ 1: Через CLI
docker exec bioetl-grafana grafana-cli admin reset-admin-password new_password

# Способ 2: Через конфиг
# Отредактировать docker-compose.monitoring.yml:
environment:
  GF_SECURITY_ADMIN_PASSWORD: new_password

docker compose -f docker-compose.monitoring.yml up -d --force-recreate
```

### Проблема: Prometheus занимает много памяти

```bash
# Проверить размер БД
du -sh /var/lib/docker/volumes/bioetl_prometheus_data/_data

# Решения:
# 1. Уменьшить retention в prometheus.yml
# global:
#   retention: 7d  # Вместо 15d

# 2. Или через CLI флаг:
# docker run ... --storage.tsdb.retention.time=7d

# 3. Очистить старые данные (осторожно!)
# docker exec bioetl-prometheus rm -rf /prometheus/wal/*
# docker restart bioetl-prometheus
```

---

## Быстрая справка (шпаргалка)

### Команды Docker

```bash
# Запустить контейнеры
docker compose -f docker-compose.monitoring.yml up -d

# Остановить
docker compose -f docker-compose.monitoring.yml down

# Просмотреть логи
docker logs bioetl-prometheus -f
docker logs bioetl-grafana -f

# Перезапустить конкретный контейнер
docker restart bioetl-prometheus

# Подключиться к контейнеру
docker exec -it bioetl-prometheus sh
```

### PromQL запросы (примеры)

```promql
# Все метрики BioETL
{__name__=~"bioetl_.*"}

# Текущее значение обработанных записей
sum(bioetl_records_processed_total)

# По стадиям
sum(bioetl_records_processed_total) by (stage)

# По pipeline
sum(bioetl_records_processed_total) by (pipeline)

# Error rate за последний час
rate(bioetl_records_processed_total{status="error"}[1h])

# Среднее время обработки
avg(bioetl_processing_duration_seconds_bucket)
```

### Полезные URL

| URL | Назначение |
|-----|-----------|
| http://localhost:3000 | Grafana Home |
| http://localhost:3000/dashboards | Все дашборды |
| http://localhost:3000/d/bioetl-simple | BioETL Simple Dashboard |
| http://localhost:3000/explore | Prometheus Query Explorer |
| http://localhost:9090 | Prometheus Web UI |
| http://localhost:9090/targets | Targets статус |
| http://localhost:9090/graph | Query граф (deprecated) |
| http://localhost:8000/metrics | BioETL Metrics endpoint |

---

## Поддержка и вопросы

Если возникают вопросы:

1. **Проверить логи контейнеров**
   ```bash
   docker compose -f docker-compose.monitoring.yml logs
   ```

2. **Перезагрузить все компоненты**
   ```bash
   docker compose -f docker-compose.monitoring.yml down
   docker compose -f docker-compose.monitoring.yml up -d
   python ./metrics_server.py &
   ```

3. **Проверить здоровье компонентов**
   ```bash
   curl http://localhost:9090/-/healthy
   curl http://localhost:3000/api/health
   curl http://localhost:8000/health
   ```

---

**Версия документации:** 1.0  
**Последнее обновление:** 22 февраля 2026  
**Совместимость:** BioETL v6.0.0, Prometheus 3.9.1, Grafana 10.2.0+
