---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Dashboards Docs Index

Дата сверки: **2026-03-29**  
Источник истины: `grafana/dashboards/*.json`

## Актуальные документы

- `monitoring-index.md` — canonical reading order по monitoring docs.
- `dashboard-v2-usage.md` — как использовать дашборды в операционной работе.
- `dashboard-extension-human.md` — краткое руководство для инженера по расширению shipped dashboards.
- `dashboard-extension-llm.md` — краткий playbook для LLM/AI-агента по безопасной правке dashboard JSON и docs cascade.
- `variables-guide.md` — фактические Grafana variables и их PromQL.
- `dashboard-v2-updates.md` — что именно проверено и исправлено в JSON.

Текущий shipped Explore handoff:
- Loki использует безопасный baseline `{job="bioetl"}`.
- Tempo использует contextual TraceQL filters по текущему dashboard scope (`pipeline/run_type` или `provider`).

## Legacy-документы

Архивные материалы перемещены в `docs/03-guides/dashboards/legacy/`.

Они могут содержать устаревшие переменные (`$run-id`, `execution`) и старые формулы.
