# Operations Documentation Inventory

Status: active  
Class: published  
Owner: BioETL Team  
Last reviewed: 2026-05-26

## Canonical

- `docs/05-operations/README.md` — entrypoint и routing по operations.
- `docs/05-operations/runbooks/index.md` — единый каталог runbook-инструкций.
- `docs/05-operations/01-monitoring-guide.md`
- `docs/05-operations/sli-slo-baseline.md`
- `docs/05-operations/performance-baselines.md`
- `docs/05-operations/control-plane-lifecycle.md`
- `docs/05-operations/vacuum-retention.md`
- `docs/05-operations/runbooks/*.md` (кроме явно помеченных duplicate/obsolete ниже).
- `docs/05-operations/runbooks/game-day.md` — ежегодный DR restore drill (RPO/RTO).

## Duplicate (de-duplicated)

- ~~`docs/05-operations/runbooks/dq-failure-investigation.md`~~  
  Canonical: `docs/05-operations/runbooks/pipeline-failure-dq.md`. (Removed 2026-08-09)
- ~~`docs/05-operations/runbooks/neo4j-complete-recovery-guide.md`~~  
  Canonical: `docs/05-operations/runbooks/neo4j-backend-recovery-quick-start.md`. (Removed 2026-08-09)

Policy: duplicate-файлы сохраняются как short notice + ссылка на canonical.

## Experimental

- `docs/05-operations/deployment/README.md` и связанный `deployment/*` набор.
- `docs/05-operations/tooling/scripts-ops/*`.

Статус: **оставить** как Experimental/Extended материал, исключив из основных путей исполнения (runbook path).

## Obsolete / Historical

- `docs/05-operations/release-checklist.md` — historical release artifact.
- `docs/05-operations/verification/*` — verification evidence snapshots.

Статус: хранить в archive routing через `docs/05-operations/archive-index.md`.

## Doc ownership + review cadence

- Owner (section-level): **BioETL Team**.
- Canonical navigation surfaces: `README.md`, `runbooks/index.md`, `archive-index.md`.
- Cadence:
  - Ежемесячно: quick drift review canonical/duplicate links.
  - Ежеквартально: полный reclassification (canonical/duplicate/experimental/obsolete).
  - После каждого incident postmortem: targeted update затронутых runbook-файлов.
- Gate: при добавлении нового operations-дока автор обязан
  1) добавить его в этот inventory,
  2) определить категорию,
  3) добавить/обновить cross-link в `README.md`.
