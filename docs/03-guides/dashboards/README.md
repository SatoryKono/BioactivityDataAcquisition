______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-13'

______________________________________________________________________

# Dashboards Docs Index

Дата сверки: **2026-04-13**
Источник истины: `grafana/dashboards/*.json`

## Актуальные документы

- `monitoring-index.md` — canonical reading order по monitoring docs.
- `dashboard-v2-usage.md` — как использовать дашборды в операционной работе, включая runtime adaptive-memory triage.
- `dashboard-extension-human.md` — краткое руководство для инженера по расширению shipped dashboards.
- `dashboard-extension-llm.md` — краткий playbook для LLM/AI-агента по безопасной правке dashboard JSON и docs cascade.
- `variables-guide.md` — фактические Grafana variables и их PromQL.
- `dashboard-v2-updates.md` — что именно проверено и исправлено в JSON.

Текущий shipped Explore handoff:

- Loki использует безопасный baseline `{job="bioetl"}`.
- Tempo использует contextual TraceQL filters по текущему dashboard scope (`pipeline/run_type` или `provider`).
- `bioetl-runtime` остаётся Prometheus-first в tracing-off режиме: Loki log-hygiene panels теперь живут в collapsed row `Tracing-only Log Hygiene`, а базовый triage path не требует Loki/Tempo datasource.

Текущая навигационная модель:

- `1. BioETL Overview` -> `2. Runtime` / `Control Plane / Replay Safety` / `3. Provider Health` / `4. Data Quality` / `6. Workflow Overview`
- `2. Runtime` -> `Back to Overview` / `Control Plane / Replay Safety` / `4. Data Quality`
- `3. Provider Health` -> `Back to Overview` / `2. Runtime`
- `4. Data Quality` -> `Back to Overview` / `5. Silver Reject Explorer`
- `6. Workflow Overview` -> `Back to Overview` / `2. Runtime` / `Control Plane / Replay Safety`

`bioetl-overview-v2` is the L0 answer-first surface. It answers one question:
what is currently broken or degraded in BioETL, and where should the operator
drill down first? The first visible answer is now a compact KPI-first row: `System Status`,
`Next Action`, `Failed Runs in Range`, `Worst Backlog Stage`, `Worst Lag Stage`,
and `Flow Balance`. `OK` requires recent activity, while missing samples/no
denominator remain `UNKNOWN`. Detail panels are moved to collapsed rows
(`Throughput details`, `Freshness breakdown`, `Extended distributions`) so the
first screen answers the operator question without scroll. Keep record-level
filters, provider deep diagnostics, DQ cause breakdowns, and control-plane
replay/audit detail out of Overview.

`bioetl-control-plane-v1` is the Control Plane / Replay Safety surface. It
answers whether manifest, ledger, checkpoint, replay, and lineage state are
trustworthy enough to allow replay/resume. GLOBAL read panels are diagnostic,
not pipeline-scoped, and missing checkpoint-age / replay-duplicate metrics are
documented as blind spots until instrumentation exists.

## Legacy-документы

Архивные материалы перемещены в `docs/03-guides/dashboards/legacy/`.

Они могут содержать устаревшие переменные (`$run-id`, `execution`) и старые формулы.


## Regenerate and verify parity

Для регенерации инвентаризации dashboard metadata (UID/title/variables/links/tags):

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --json
```

Для проверки parity с каноническими документами (`variables-guide.md`, `monitoring-index.md`)
и mandatory links contract:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
```

CI gate запускает эту проверку в `docs.yml` и фейлит pipeline при расхождении
канонических полей.
