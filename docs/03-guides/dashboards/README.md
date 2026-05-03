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
drill down first? The first visible answer is `System Status` plus `Next Action`;
`OK` requires recent activity, while missing samples/no denominator remain
`UNKNOWN`. Backlog/lag cards expose the responsible stage, and `Flow Balance`
replaces vanity yield with Bronze/Gold/loss denominator context. Keep
record-level filters, provider deep diagnostics, DQ cause breakdowns, and
control-plane replay/audit detail out of Overview.

`bioetl-control-plane-v1` is the Control Plane / Replay Safety surface. It
now starts with an answer-first **Trust Summary** block: replay safety state,
checkpoint freshness proxy, and ledger/manifest consistency for the selected
pipeline scope. A visible **Known Blind Spots** list is part of this top block
and documents currently non-instrumented signals.

Global lookup/read-path panels stay separated in a dedicated
**Global diagnostics (non-pipeline scoped)** block and MUST remain unfiltered by
`$pipeline` / `$run_type`.

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
