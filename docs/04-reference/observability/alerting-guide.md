# Alerting Guide

## Overview

BioETL использует Prometheus alerting rules для мониторинга системы и уведомлений о проблемах.

## Alerting Rules Location

Alerting rules определены в следующих файлах:

- `grafana/prometheus-rules/bioetl_observability.yml` - Основные observability правила (pipeline, DQ, provider, system alerts)
- `grafana/prometheus-rules/bioetl_control_plane_current_status.yml` - Control Plane status alerts (workflow, run ledger, checkpoint alerts)

## Key Alert Rules

### Pipeline Alerts

- `PipelineFailureRate`: Высокий процент failed pipeline runs
- `PipelineDurationHigh`: Pipeline выполняется слишком долго
- `PipelineStuck`: Pipeline застрял в RUNNING состоянии

### Data Quality Alerts

- `DQScoreLow`: Низкий показатель качества данных
- `QuarantineRateHigh`: Высокий процент записей в карантине
- `SilverRejectRateHigh`: Высокий процент отклонений на Silver

### Provider Alerts

- `ProviderDown`: Provider недоступен
- `ProviderHighLatency`: Высокая задержка provider
- `ProviderRateLimited`: Provider rate limiting активен

### System Alerts

- `HighMemoryUsage`: Высокое использование памяти
- `HighCPUUsage**: Высокое использование CPU
- `DiskSpaceLow`: Мало места на диске

## Alert Severity Levels

- **Critical**: Требует немедленного внимания
- **Warning**: Требует внимания в ближайшее время
- **Info**: Информационное уведомление

## Alert Thresholds

Пороги настроены в alerting rules:

```yaml
- alert: PipelineFailureRate
  expr: rate(bioetl_pipeline_run_failed_total[5m]) > 0.1
  for: 5m
  labels:
    severity: critical
```

## Recording Rules

Recording rules используются для pre-computation агрегаций:

```yaml
groups:
  - name: bioetl_recording
    rules:
      - record: bioetl_pipeline_success_rate_5m
        expr: |
          sum(rate(bioetl_pipeline_run_completed_total[5m]))
          /
          sum(rate(bioetl_pipeline_run_total[5m]))
```

## Alert Routing

Alerts routing конфигурируется через Alertmanager (если настроен).

## Best Practices

1. Устанавливать appropriate thresholds
2. Использовать recording rules для сложных запросов
3. Добавлять annotations к alerts для контекста
4. Регулярно reviewing и tuning alert rules