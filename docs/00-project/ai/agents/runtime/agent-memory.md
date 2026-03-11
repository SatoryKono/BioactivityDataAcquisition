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
- Быстрый старт: `./dev-setup.sh` (или `--quick`).
- Проверки: `make lint && make test` (локальный stable suite, без E2E).
- Пример запуска: `bioetl run --pipeline chembl_activity --run-type incremental`.

## Гигиена репозитория
- Артефакты → `reports/` или `logs/`, временные дампы → `tmp/`.
- Корень репозитория защищён политикой allowlist.
