# PILLARS — Research Scope

**Brief:** `../00-brief/BRIEF.md`
**Created:** 2026-08-20
**Default mode:** single-stream (multi-stream только по явному запросу)

> Скоупы ниже — дефолт для BioETL. Приоритеты можно поменять перед фазой Evidence.

| Pillar | Priority | Scope (research questions) | Key sources | Evidence dir |
|--------|----------|----------------------------|-------------|--------------|
| **market** | High | Размер и рост рынка биоактивностных данных; спрос на unified warehouse vs прямые API; роль Delta Lake / Lakehouse в биоинформатике; ценовые ожидания на self-hosted ETL | ChEMBL/PubChem/UniProt usage reports, Delta Lake adoption, bioinformatics tooling surveys | `ledger/02-evidence/market/` |
| **users** | High | JTBD исследователей и data engineers; боли текущих пайплайнов (дедупликация, SCD2, quarantine); требования к CLI/HTTP UX и форензике отбракованных строк | Интервью пользователей, GitHub issues/discussions, UX-аудиты CLI | `ledger/02-evidence/users/` |
| **tech** | High | Medallion-инварианты, Pandera vs Pydantic, Delta time travel, детерминированные записи, порты/адаптеры, unified HTTP client, in-memory locking, replay | ADRs (002/014/018/032/044/048), `src/bioetl/`, `tests/architecture/` | `ledger/02-evidence/tech/` |
| **competitors** | Medium | Прямые конкуренты (Open Targets, BindingDB ETL, custom ChEMBL loaders) и косвенные (general ETL: Airflow/Dagster + Delta); дифференциация по local-first и DQ | Сравнительные таблицы фич, доки конкурентов, бенчмарки | `ledger/02-evidence/competitors/` |
| **design** | Medium | CLI/HTTP операторский опыт, дашборды L0/L1 (DASHBOARD_REQUIREMENTS), quarantine inspect UX, конфиг-DSL для entities/workflows | `grafana/dashboards/`, `docs/04-reference/`, CLI help | `ledger/02-evidence/design/` |
| **legal** | Medium | Лицензии источников (ChEMBL CC, UniProt, PubChem), rate-limit compliance, PII/лицензии публикаций, forensic retention | Лицензии провайдеров, `configs/contracts/` | `ledger/02-evidence/legal/` |
| **ops** | High | Локальный деплой, control plane (manifest/ledger), бэкап/DR, exclusive backfill locks, observability (Prometheus/Grafana опционально), health checks | `src/bioetl/domain/control_plane/`, `src/bioetl/infrastructure/observability/`, runbooks | `ledger/02-evidence/ops/` |
| **economics** | Low | Стоимость владения (self-host vs cloud), операционные затраты на хранение Delta, экономия от дедупликации и quarantine | Cost models, storage benchmarks, API cost vs local cache | `ledger/02-evidence/economics/` |

## Priority Tiers

1. **Tier 1 (сначала):** tech, users, market, ops
2. **Tier 2:** competitors, design, legal
3. **Tier 3:** economics

## Evidence Gate

- Минимум **5 Evidence Objects** на пиллар перед синтезом (см. `research-workflow` Phase 2).
- Схема объекта: `id`, `pillar`, `source{type,ref,retrieved_at}`, `claim` (фальсифицируемый), `quote`, `confidence 0.0–1.0`, `assumptions[]`, `notes`, `tags[]`.
- Типы источников: `url`, `pdf`, `interview`, `internal-doc`, `experiment`, `dataset`.

## Next Steps

1. Подтверди/поправь `00-brief/BRIEF.md`.
2. Запусти `research-workflow --phase evidence --pillar <name>` для Tier 1 пилларов.
3. После гейта (≥5) — `--phase synthesis --pillar <name>`, затем `--phase decisions` и `--phase specs`.
