# Alerting Guide

## Overview

BioETL использует Prometheus recording/alert rules для мониторинга системы и
уведомлений о проблемах. Shipped rule files and dashboard JSON are the source
of truth for metric names.

## Alerting Rules Location

Alerting rules определены в следующих файлах:

- `grafana/prometheus-rules/bioetl_observability.yml` - основные runtime,
  DQ, provider, workflow, Silver/Gold reject, and dashboard status rules.
- the control-plane status rules file under `grafana/prometheus-rules/` -
  replay safety, manifest/ledger integrity, checkpoint freshness, and lineage
  evidence rules.

## Key Alert Rules

### Pipeline Alerts

- `bioetl_runtime_alert_condition_pipeline_runs_failed_15m`: failed pipeline
  runs detected in the selected window.
- `bioetl_runtime_alert_condition_stage_lag_high_15m`: stage lag is above the
  operational threshold.
- `bioetl_runtime_alert_condition_no_terminal_run_30m`: source activity exists
  without a terminal run.

### Data Quality Alerts

- `bioetl_dq_current_status`: current DQ severity.
- `bioetl_runtime_alert_condition_dq_hard_fail_15m`: hard validation failures.
- `bioetl_runtime_alert_condition_silver_validation_failures_30m`: Silver
  validation failures.
- `bioetl_silver_filter_reject_total_mismatch_15m`: Silver reject accounting
  reconciliation mismatch.

### Provider Alerts

- `bioetl_provider_current_status`: current provider severity.
- `bioetl_runtime_alert_condition_provider_failure_rate_high_15m`: high
  provider failure rate.
- `bioetl_runtime_alert_condition_provider_rate_limiter_wait_high_30m`: high
  rate-limiter wait.

### System Alerts

- `bioetl_runtime_current_status`: current runtime severity.
- `bioetl_runtime_current_blocker_reason`: current runtime blocker reason.
- `bioetl_runtime_alert_condition_runtime_error_rate_high_30m`: high runtime
  error rate.

## Alert Severity Levels

- **Critical**: Требует немедленного внимания
- **Warning**: Требует внимания в ближайшее время
- **Info**: Информационное уведомление

## Alert Thresholds

Пороги настроены в alerting rules:

```yaml
- alert: PipelineRunsFailed
  expr: sum by (pipeline, run_type) (increase(bioetl_pipeline_runs_total{status="failed"}[15m])) > bool 0
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
      - record: bioetl_l0_status
        expr: max by (pipeline, run_type) (bioetl_l0_input_status_selected)
```

## Alert Routing

Alerts routing конфигурируется через Alertmanager (если настроен).

## Best Practices

1. Устанавливать appropriate thresholds
2. Использовать recording rules для сложных запросов
3. Добавлять annotations к alerts для контекста
4. Регулярно reviewing и tuning alert rules
