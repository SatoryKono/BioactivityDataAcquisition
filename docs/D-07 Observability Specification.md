______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-07 Observability Specification (Draft Sync Note)

## Назначение

D-07 сохраняется как draft-рамка для будущего consolidated observability handbook.
Сейчас это non-normative синхронизационный документ, который не заменяет опубликованные contracts/guides/runbooks.

## Канонические источники

- `docs/04-reference/contracts/observability.md`
- `docs/03-guides/metrics-monitoring.md`
- `docs/05-operations/01-monitoring-guide.md`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/05-operations/runbooks/observability-checklist.md`
- `docs/05-operations/runbooks/traceability-signal-ownership.md`
- `docs/05-operations/runbooks/run-manifest-inspection.md`

## Текущий validated observability contour (summary)

- Канонический observability contract уже закреплён в `04-reference/contracts/observability.md`.
- Operator surfaces (dashboards, alert-backed triage, runbook routing) закреплены в `01-monitoring-guide.md` и runbook-пакете.
- Metrics naming и label guardrails должны оставаться low-cardinality и согласованными с текущим Prometheus/Grafana rollout.
- Control-plane observability (`manifest`, `ledger`, `checkpoint compatibility`, `read outcomes`) уже входит в published monitoring/runbook контур.

## Текущие зоны дрейфа

- Наибольший риск — дублирование alert/SLO таблиц и metric lists в нескольких документах.
- Черновые описания, не связанные с каноническими rules/runbooks, быстро расходятся с реальными dashboard/rule конфигурациями.
- D-07 не должен вводить собственную альтернативную терминологию для severity, alert routing и triage sequence.

## План синхронизации D-07

1. Держать в D-07 только карту canonical observability surfaces и их назначение.
1. Не дублировать списки метрик и alert rules из `contracts/observability.md` и monitoring/runbook документов.
1. Все runtime-facing утверждения (SLO, alert thresholds, triage order) обновлять сначала в канонических документах, затем отражать в D-07 как summary.

## Критерии промоушена в future published handbook

1. Единый observability терминологический словарь согласован между contracts, guides и runbooks.
1. D-07 не содержит дублируемых таблиц метрик/алертов и не конфликтует с Grafana/Prometheus rollout.
1. Любое утверждение в D-07 трассируется к published source и проверяемому runtime artifact.
