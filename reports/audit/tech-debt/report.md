# Аудит технического долга — BioactivityDataAcquisition

- Промпт: prompt.audit.tech-debt v1.2.0, MODE=audit
- Источник: ТОЛЬКО компактные свидетельства (prior result 1–3); новых измерений не проводилось
- Находок: 12 (AUD-001…AUD-012), все PROVEN; NOT_PROVEN нет
- Поверхностная оценка (surface_score, шкала 0–3): **общий 2** (макс. 3 у P0; средний 1,8)
- Повышение бюджетов/порогов (exemptions, jscpd threshold, mypy-поблажки) — **НЕ предлагается** ни по одной находке

## Реестр по риску

### P0 — критично

| ID | Находка | Surface | Путь |
|----|---------|---------|------|
| AUD-001 | God-module `sync_pkg/_core.py`: 18179 строк / 576676 Б, смешение argparse/ast/subprocess/threading/tempfile/http/Neo4j; разрыв ~10x со следующим файлом | 3 | `src/memory/graph/sync_pkg/_core.py:1` |
| AUD-002 | Синхронизированный обрыв quality-gate exemptions 2026-12-31: весь `src/memory/` + 15 путей тяжёлых подсистем + 4 CC-лимита (25/20/15) на retry/fallback | 3 | `configs/quality/duplication_complexity_exemptions.yaml:17` |

### P1 — высокий

| ID | Находка | Surface | Путь |
|----|---------|---------|------|
| AUD-003 | Query-слой расколот: `graph/query.py` (1968 строк) + `query.py` (1700 строк), владение не зафиксировано | 2 | `src/memory/graph/query.py:1` |
| AUD-004 | Типовой долг: 11x `type:ignore` в startup-пути (строки 122–177) + весь `src/memory/` вне mypy strict + `warn_unused_ignores=false`, `warn_unreachable=false` | 2 | `src/bioetl/application/services/ops/observability_backend_startup.py:122` |
| AUD-005 | FK-reconciliation в трёх местах: infra-адаптер (~471) + application-трансформ (~464) + `_support`/`_quarantine` хелперы | 2 | `src/bioetl/infrastructure/storage/workflow_foreign_key_reconciliation.py:1` |
| AUD-006 | Хрупкие пины: `arro3-core==0.6.5`, `pandas<2.3`, `deltalake<1.0`, `mypy==2.3.1` (Windows-wheel комментарии) | 2 | `pyproject.toml:25` |

### P2 — средний

| ID | Находка | Surface | Путь |
|----|---------|---------|------|
| AUD-007 | Перефрагментация `composite/`: 66 записей, merger-mixin x8, coordinator x3, lifecycle/dependency_join/preflight кластеры; jscpd-порог 5 подтверждает давление дублирования | 2 | `src/bioetl/application/composite/` |
| AUD-008 | Star-реэкспорты `noqa F403` в 4 фасадах (factory_wiring, field_transforms, transformer_runtime, openalex extractors) | 1 | `src/bioetl/application/core/transformer_runtime/__init__.py:11` |
| AUD-009 | 37x `pragma: no cover` в runner/fallback wiring и lazy-export путях | 1 | `src/bioetl/application/` |
| AUD-010 | Legacy/compat-шимы без sunset: `Metrics*Result` (deprecated с 2026-08-26), pandera-shim `strict=False`, `strip_legacy_keys`, memory_monitor re-export, legacy string IDs | 1 | `src/bioetl/application/ports/metrics.py:116` |
| AUD-011 | 12 постоянных CLI entrypoints, sunset только через breaking change (`external_breaking_change_required=true`) | 2 | `configs/quality/compatibility_facade_inventory.yaml:23` |

### P3 — низкий

| ID | Находка | Surface | Путь |
|----|---------|---------|------|
| AUD-012 | Принятые `nosec`-подавления без реестра (subprocess B404/B603 + 7x ET B405); гигиена маркеров хорошая (TODO/FIXME/HACK: 0) | 1 | `src/bioetl/infrastructure/storage/silver/delta_write_execution.py:8` |

## Quick wins (малые усилия, быстрый эффект)

- AUD-008: явные `__all__` и прямые реэкспорты, убрать `noqa F403` (S).
- AUD-010: зафиксировать sunset-даты шимов, начать с `Metrics*Result` (S).
- AUD-012: завести реестр подавлений `nosec` с обоснованием и сроком пересмотра (XS).
- AUD-009: к каждому `pragma: no cover` привязать issue-ссылку; runner-пути покрыть интеграционными тестами (M).

## Стратегические (структурные)

- AUD-001 → AUD-003: декомпозиция memory-sidecar (god-module → cohesive модули <500 строк; единый query-слой). Снимает и AUD-002 для `src/memory/`.
- AUD-002: рассредоточить сроки exemptions, привязать каждую запись к removal_step с прогрессом; CI должен падать при истечении без review.
- AUD-004: типизировать DI-seam startup-пути, включить `src/memory/` в mypy strict, включить `warn_unused_ignores`/`warn_unreachable`.
- AUD-005: одно каноническое место FK-reconciliation + тесты паритета.
- AUD-006: снять жёсткие пины (диапазоны + Windows-CI), план апгрейда deltalake/pandas/arro3.
- AUD-007: граф владения composite-пакета, укрупнение миксинов >200 строк.
- AUD-011: реестр entrypoints с deprecation-окном и миграционным гайдом.

## Примечание о полноте

Синтез ограничен переданными свидетельствами; независимых замеров (прогон xenon/jscpd/mypy/pytest) в рамках задачи не выполнялось — команды регрессии зафиксированы в `findings.json` (`validation_commands`) для исполнения владельцами.
