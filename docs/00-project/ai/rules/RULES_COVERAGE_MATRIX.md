______________________________________________________________________

Version: 1.1.0
Status: internal-published
Class: internal
Owner: BioETL Team
Last verified: '2026-07-04'
Aligned with: consolidated AI rules digest 2.0.0 (RULES v6.1.4, REQUIREMENTS v1.10, ADR-050)

______________________________________________________________________

# Cursor Rules Coverage Matrix

Карта покрытия `docs/00-project/RULES.md` v6.1.4 тематическими `.mdc` правилами.
Канон — `RULES.md` + `REQUIREMENTS.md` + ADR; правила — condensed guidance.

## Legend

| Status | Meaning |
| ------ | ------- |
| covered | Основные MUST/SHOULD отражены в `.mdc` |
| partial | Есть ссылка или фрагмент; детали только в RULES |
| mirror | Только в `bioetl-ai-rules.md` / docs mirror |
| gap | Не покрыто (acceptance risk для AI guidance) |

## Matrix (RULES § → cursor rule)

| RULES § | Topic | REQ prefix | Rule file | Status |
| ------- | ----- | ---------- | --------- | ------ |
| §1 | Hexagonal / layers | REQ-ARCH-* | `00-architecture.mdc` | covered |
| §1.1.3–4 | Technical debt budgets | REQ-ARCH-* | `05-agent-workflow.mdc` | covered |
| §2.1 | Medallion Bronze/Silver/Gold | REQ-DATA-* | `01-data-quality.mdc` | covered |
| §2.4 | Backfill / replay / locks | REQ-BACKFILL-* | `08-operations.mdc` | covered |
| §2.6 | NULL policy | REQ-NULL-* | `01-data-quality.mdc` | covered |
| §2.8 | DQ Contract System | REQ-DQ-* | `01-data-quality.mdc`, `10-error-resilience.mdc` | covered |
| §2.9 | Entity ID / content hash | REQ-ID-* | `01-data-quality.mdc`, `02-code-style.mdc` | covered |
| §2.9 | Composite pipelines | REQ-COMP-* | `04-patterns.mdc` | covered |
| §2.10 | Lineage / partitions / load strategy | REQ-LINEAGE-*, REQ-PARTITION-*, REQ-LOAD-* | `01-data-quality.mdc`, `08-operations.mdc` | covered |
| §3.1 | Error classification / retry / CB | REQ-RETRY-*, REQ-CB-* | `04-patterns.mdc`, `10-error-resilience.mdc` | covered |
| §3.1.2 | DQ batch thresholds | REQ-DQ-* | `10-error-resilience.mdc` | covered |
| §3.2 | Observability / metrics / logs / anomaly | REQ-OBS-*, REQ-ANOMALY-* | `09-observability.mdc` | covered |
| §3.3 | Locks / concurrency | REQ-LOCK-* | `08-operations.mdc` | covered |
| §4.1.1 | UnifiedHTTPClient / provider health | REQ-STACK-*, REQ-HEALTH-* | `04-patterns.mdc`, `10-error-resilience.mdc` | covered |
| §4.2 | Testing policy | REQ-TEST-* | `03-testing.mdc` | covered |
| §4.3 | Determinism | REQ-CTRL-* | `01-data-quality.mdc`, `00-bioetl-core-governance.mdc` | covered |
| §4.4 | Python standards | REQ-NAMING-* | `02-code-style.mdc` | covered |
| §5.1 | Rate limiting | REQ-RATE-* | `04-patterns.mdc`, `08-operations.mdc` | covered |
| §5.2 | Secrets | REQ-OPS-* | `08-operations.mdc`, `05-agent-workflow.mdc` | covered |
| §5.3 | Graceful shutdown / checkpoints | REQ-OPS-* | `08-operations.mdc` | covered |
| §5.4 | Sensitive data / PII | REQ-OPS-* | `01-data-quality.mdc` | covered |
| §5.5 | Disaster recovery | REQ-DR-* | `08-operations.mdc` | covered |
| §5.6 | Environment isolation | REQ-OPS-* | `08-operations.mdc` | covered |
| §6 | Documentation automation | REQ-DOC-* | `06-docs-standards.mdc` | partial |
| §7.1 | Schema evolution / deprecation | REQ-SCHEMA-* | `11-schema-evolution.mdc` | covered |
| §8.1 | Data contracts | REQ-SCHEMA-* | `11-schema-evolution.mdc` | covered |
| §8.2 | Rollback strategy | REQ-OPS-* | `11-schema-evolution.mdc` | partial |
| §9 | Developer experience / CI gates | REQ-DX-*, REQ-DEP-* | `02-code-style.mdc`, `03-testing.mdc` | covered |
| Governance | AI agent workflow | — | `05-agent-workflow.mdc` | covered |
| Governance | Qodo traceability | — | `07-qodo-enforcement.mdc` | covered |
| Governance | Core invariants | — | `00-bioetl-core-governance.mdc` | covered |

## Intentional partial coverage

Следующие темы **MUST** оставаться в каноне; `.mdc` даёт только entry points:

- Appendices A–F (provider catalogs, runbooks, schema evolution details)
- Full Prometheus metric catalog (§3.2.2)
- Complete ADR text
- Full `POST_CHANGE_VALIDATION.md` protocol (сводка в `05-agent-workflow.mdc`)

## Deploy surfaces

| Surface | Path | Sync |
| ------- | ---- | ---- |
| Canonical | `docs/00-project/ai/rules/cursor/*.mdc` | edit here |
| Cursor IDE | `.cursor/rules/*.mdc` | `scripts/ai/sync_cursor_rules.py --deploy` |
| Windsurf | `docs/00-project/ai/rules/windsurf/rules/*.md` | `scripts/ai/sync_windsurf_rules.py` |

## Verification commands

```bash
uv run python scripts/ai/sync_cursor_rules.py --check
uv run python scripts/ai/sync_windsurf_rules.py --check
uv run python -m scripts.docs check-drift --runtime-mirrors --freshness
```

## Changelog

| Date | Change |
| ---- | ------ |
| 2026-07-04 | Sync with consolidated rules digest 2.0.0; expanded 00–04, 08–11; improved coverage matrix |
| 2026-07-04 | Initial matrix; added rules `08`–`11`; closed gaps §2.4, §3.1–3.2, §5, §7–8 |
