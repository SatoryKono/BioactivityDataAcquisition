---
Version: 1.1.1
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-06'
---

# Memory: BioETL (краткая выжимка)

*Статус: internal-published (Internal / Extended)*

## Что это
- BioETL — локальный ETL для биологической активности: ChEMBL, PubChem, UniProt и др.
- Цель: нормализация и загрузка в **Delta Lake** с воспроизводимыми результатами.

## Архитектура
- **Hexagonal (Ports & Adapters)**: `domain` (чистая логика, ports), `application` (оркестрация), `infrastructure` (адаптеры), `composition` (DI root), `interfaces` (CLI).
- **Запрещено** импортировать `infrastructure` в `domain`/`application`.
- Логирование только через `UnifiedLogger`, **никаких `print()`**.

## Поток данных (Medallion)
- **Bronze**: JSONL + zstd, append-only.
- **Silver**: Delta Lake, merge/upsert, ACID, raw Parquet **запрещён**.
- **Gold**: строгая валидация, SCD2 или overwrite/append по политике.
- **Детерминизм**: фиксированный порядок колонок/строк, UTC, validate-before-write.

## Ключевые правила
- Python **3.11+** (в правилах проекта упоминается 3.12+ для tooling).
- **Coverage ≥ 85%**, `ruff` + `mypy --strict`.
- **VCR.py** для HTTP-тестов, кассеты строго в `tests/fixtures/vcr/{provider}/`.
- **Quarantine** для невалидных данных; DQ thresholds: >5% warning, >20% fail.
- **Local-only**: `MemoryLock` (TTL 90s, heartbeat 30s, max 4h).
- **Secrets** только через `pydantic-settings`/`os.environ`, без хардкода.
- **Папка с промтами проекта**: `docs/00-project/ai/prompts/`.

## Разработка и запуск
- Быстрый старт: `make install && make test-deps && make setup-plugins`.
- Проверки: `make lint && make test` (локальный stable suite, без E2E).
- Пример запуска: `bioetl run --pipeline chembl_activity --run-type incremental`.

Если checkout используется из PowerShell и WSL одновременно, не дели одну
`.venv` между ОС:

- PowerShell: `.\scripts\engineering\dev\setup_env_windows.ps1`,
  `.\scripts\engineering\dev\run_pytest.ps1`, `.\scripts\engineering\dev\run_mypy.ps1`
- WSL/Linux: `bash scripts/engineering/dev/setup_env_wsl.sh`,
  `bash scripts/engineering/dev/run_pytest.sh`, `bash scripts/engineering/dev/run_mypy.sh`
- OS-specific runtimes:
  `.venv-win` в PowerShell и
  `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}` в WSL

## Гигиена репозитория
- Артефакты → `reports/` или `logs/`, временные дампы → `tmp/`.
- Корень репозитория защищён политикой allowlist.

## Evidence anchors
- File structure: `docs/reports/evidence/project-file-structure/SUMMARY.md`
- File structure decisions: `docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md`
- Package topology: `docs/reports/evidence/project-package-topology/SUMMARY.md`
- Package topology decisions: `docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md`
- Governance signals: `docs/reports/evidence/governance-signals/SUMMARY.md`

Для structural claims:
- не считать package count самостоятельным сигналом к reorg;
- проверять family-level topology и governance evidence вместе.

## Debt tracking on file changes
- При изменении файлов обязательно различай `exemption debt` и `hotspot inventory`.
- Проверяй применимые registries в `configs/quality/debt_scorecard.yaml`:
  `file_size_limits`, `function_complexity`, `function_length`, `class_size`,
  `class_method_count`, `god_object`, `domain_complexity`.
- Если путь входит в hotspot family из scorecard, отслеживай family-level
  параметры вроде `duplication_clusters`, `files_ge_250_loc`,
  `max_internal_fan_in` и не ухудшай их молча.
- Не добавляй новый exemption без required metadata в
  `configs/quality/architecture_metric_exemptions.yaml` и без scorecard sync.
- В финале задачи помечай debt outcome для touched files:
  `improved`, `unchanged` или `worsened`.
