# Мониторинг BioETL (Prometheus + Grafana)

Система мониторинга реального времени для отслеживания производительности, здоровья провайдеров и качества данных.

## Архитектура мониторинга

1.  **BioETL App**: Экспортирует метрики через `prometheus_client` на порту `BIOETL_METRICS_PORT` (по умолчанию `8000`).
2.  **Prometheus**: Скрейпит метрики из приложения и хранит их в TSDB.
3.  **Grafana**: Визуализирует данные из Prometheus через предустановленные дашборды.

## Быстрый запуск (Docker Compose)

Самый простой способ запустить стек мониторинга:

```bash
# Запуск Prometheus и Grafana
make monitoring-up

# Проверка статуса
docker compose -f docker-compose.monitoring.yml ps

# Просмотр логов
make monitoring-logs

# Остановка
make monitoring-down
```

После запуска:
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana**: [http://localhost:3000](http://localhost:3000) (логин: `admin`, пароль: `admin`)

Дашборды импортируются автоматически через механизм provisioning.

## Доступные дашборды

| Название | Описание | Основные метрики |
| :--- | :--- | :--- |
| **Overview** | Общий обзор пайплайнов | `pipeline_duration_seconds`, `records_processed_total`, `errors_total`, `batch_size_records`, `data_freshness_seconds`, `filter_ids_*` |
| **Provider Health** | Здоровье API-адаптеров | `circuit_breaker_state`, `circuit_breaker_trips_total`, `circuit_breaker_success_total`, `circuit_breaker_failure_total` |
| **Data Quality** | Качество данных и карантин | `dq_validation_score`, `dq_records_quarantined_total`, `dq_anomaly_detected`, `dq_check_duration_ms`, `dq_baseline_*` |
| **Operations** | Обслуживание хранилища | `vacuum_files_removed_total`, `vacuum_duration_seconds`, `archive_files_total`, `archive_duration_seconds` |
| **Infrastructure Health** | Статус инфраструктуры | `pipeline_health_check_passed`, `infrastructure_validated`, `health_check_duration_seconds` |

## Конфигурация приложения

Для корректной работы мониторинга убедитесь, что в `.env` установлены следующие переменные:

```env
BIOETL_METRICS_ENABLED=true
BIOETL_METRICS_PORT=8000
BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED=true
```

## Устранение неполадок

### Prometheus не видит приложение (Target Down)

Если вы запускаете мониторинг в Docker, а приложение — локально на хосте, убедитесь, что в `grafana/prometheus.yml` указано:

```yaml
static_configs:
  - targets: ['host.docker.internal:8000']
```

Для Windows и macOS это работает "из коробки". На Linux может потребоваться флаг `--add-host=host.docker.internal:host-gateway` при запуске контейнера.

### Дашборды пустые

1.  Запустите любой пайплайн: `make run-local`.
2.  Убедитесь, что метрики доступны локально: `curl http://localhost:8000/metrics`.
3.  Проверьте соединение в Prometheus: **Status -> Targets**.

## Ручная установка (без Docker)

Если вы предпочитаете устанавливать компоненты вручную:

1.  **Prometheus**: Используйте конфиг `grafana/prometheus.yml`.
2.  **Grafana**:
    - Добавьте Prometheus как DataSource (`http://localhost:9090`).
    - Импортируйте JSON-файлы из `grafana/dashboards/`.
    - Или настройте provisioning, отредактировав `grafana/provisioning/dashboards/bioetl.yaml` (поле `path` должно указывать на абсолютный путь к папке с JSON-файлами).
