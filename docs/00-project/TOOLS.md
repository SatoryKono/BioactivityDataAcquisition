______________________________________________________________________

Version: 3.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# BioETL: Утилиты Проекта

______________________________________________________________________

> Этот документ — активный hub для текущих tool entry points и правил размещения.
> Исторические детали и superseded notes не являются источником истины:
> для текущего состояния используйте `docs/00-05`, для скриптовых деталей —
> `scripts/<group>/README.md`, для исторического контекста —
> repository path `docs/99-archive/README.md`.

______________________________________________________________________

## Разграничение src/tools/ и scripts/

Согласно [03-file-policy.md](governance/03-file-policy.md):

| Директория   | Назначение              | Критерий                                |
| ------------ | ----------------------- | --------------------------------------- |
| `src/tools/` | Утилиты проекта         | **Импортирует** `bioetl` модули         |
| `scripts/`   | CI/операционные скрипты | **Standalone**, НЕ импортирует `bioetl` |

______________________________________________________________________

## Docs Toolchain

- `mkdocs` pinned to `<2.0` in `pyproject.toml` to avoid known compatibility risk with current Material stack.
- Docs site tooling lives in the separate `docs` extra; install it via `uv sync --extra dev --extra tracing --extra docs` or `pip install -e ".[dev,tracing,docs]"` before running MkDocs commands.
- Preferred invocation after `uv sync` is `uv run python -m scripts.<group> ...`.
  With an activated virtual environment, `python -m scripts.<group> ...` remains a valid fallback.
- Local automation that must resolve the project-preferred interpreter without
  assuming `uv` should use
  `python scripts/engineering/dev/run_project_python.py -m scripts.<group> ...`.
- Standard docs checks:

```bash
uv run python -m scripts.docs verify
uv run python -m scripts.docs check-links --links --specs --configs
uv run python -m scripts.docs check-drift --ports --classes
uv run python -m scripts.docs check-docstrings --summary
uv run python -m scripts.docs build-site --strict
```

- Preferred end-to-end entrypoint: `uv run python -m scripts.docs verify`

- Published workflow guide: [Docs Verification](../03-guides/docs-verification.md)

- For a non-strict local site render, use
  `uv run python -m scripts.docs build-site` after installing the separate
  `docs` extra.

- Migration to MkDocs 2.x must be tracked as a dedicated task with explicit compatibility validation.

______________________________________________________________________

## Unified Entry Points

Каждая каноническая директория `scripts/<group>/` предоставляет `__main__.py` dispatcher.
Полный список команд: `uv run python -m scripts.<group> --help`.

```bash
uv run python -m scripts.engineering.repo check-inventory --check
uv run python -m scripts.engineering.qa check-c901 --target src/bioetl
uv run python -m scripts.schema validate-configs
uv run python -m scripts.engineering.qa.vcr check-naming
uv run python -m scripts.ops.data check-delta
uv run python -m scripts.docs check-drift
uv run python -m scripts.diagrams lint
uv run python -m scripts.engineering.ci quality-gate
```

Канонические data/VCR команды живут в `scripts.ops.data` и
`scripts.engineering.qa.vcr`; новые вызовы не должны идти через legacy
facade-пути.

Каждый скрипт также можно запустить напрямую (см. `scripts/<group>/README.md`).

______________________________________________________________________

## Сводная таблица

| Файл                           | Директория                       | bioetl? | Unified command                                              | Make-цель    | Описание                                   |
| ------------------------------ | -------------------------------- | ------- | ------------------------------------------------------------ | ------------ | ------------------------------------------ |
| `create_pipeline.py`           | scripts/engineering/dev/          | Да      | `uv run python -m scripts.engineering.dev create-pipeline`   | —            | Генерация boilerplate для новых пайплайнов |
| `verify_schema_parity.py`      | scripts/schema/validation/        | Да      | `uv run python -m scripts.schema verify-schema-parity`       | —            | Верификация Silver↔Gold schema parity      |
| `file_merger.py`               | scripts/engineering/common/       | Нет     | —                                                            | —            | Объединение файлов с метаданными           |
| `cleanup_project.py`           | scripts/engineering/diagnostics/ | Нет     | `uv run python -m scripts.engineering.diagnostics cleanup`   | `make clean` | Очистка локальных кэшей и build-артефактов |
| `cleanup_consolidate.py`       | scripts/engineering/diagnostics/ | Нет     | —                                                            | —            | Консолидированный аудит очистки            |
| `audit_structure.py`           | scripts/engineering/diagnostics/ | Нет     | `uv run python -m scripts.engineering.diagnostics audit-structure` | —     | Аудит соответствия File Policy             |
| `vacuum_delta.py`              | scripts/ops/data/                | Нет     | `uv run python -m scripts.ops.data vacuum`                   | —            | VACUUM Delta Lake таблиц                   |
| `dq_baseline_update.py`        | scripts/engineering/baselines/   | Нет     | `uv run python -m scripts.engineering.baselines dq-baseline` | —            | Пересчёт DQ baseline                       |
| `verify_checksums.py`          | scripts/ops/data/                | Нет     | `uv run python -m scripts.ops.data checksums`                | —            | Верификация контрольных сумм               |
| `salt_rotate.py`               | scripts/ops/                     | Нет     | —                                                            | —            | Ротация PII-соли                           |
| `naming_audit.py`              | scripts/engineering/qa/          | Нет     | `uv run python -m scripts.engineering.qa check-naming`       | —            | Аудит naming conventions                   |
| `lint_terminology.py`          | scripts/engineering/qa/          | Нет     | `uv run python -m scripts.engineering.qa check-terminology`  | —            | Линтер терминологии                        |
| `config_gap_analysis.py`       | scripts/schema/                  | Нет     | `uv run python -m scripts.schema analyze-gaps`               | —            | Анализ расхождений конфигов                |
| `validate_pipeline_configs.py` | scripts/schema/                  | Нет     | `uv run python -m scripts.schema validate-configs`           | —            | Валидация configs vs JSON Schema           |

> Для детального описания каждого скрипта, параметров и примеров: `scripts/<group>/README.md`.

______________________________________________________________________

## Бенчмарки

Performance-тесты находятся в `tests/benchmarks/`:

| Файл                         | Назначение                                 |
| ---------------------------- | ------------------------------------------ |
| `test_bronze_write.py`       | Бенчмарки записи Bronze слоя               |
| `test_delta_write.py`        | Бенчмарки Delta Lake операций              |
| `test_json_serialization.py` | Сравнение JSON encoders (stdlib vs orjson) |

```bash
pytest tests/benchmarks/ -v --benchmark-only
```

______________________________________________________________________

## Добавление нового инструмента

Шаблоны и governance playbook: [04-extending-bioetl.md](governance/04-extending-bioetl.md).

Критерий размещения:

1. Скрипт импортирует `bioetl` → **scripts/engineering/** или **scripts/schema/**
1. Скрипт standalone → **scripts/**

______________________________________________________________________

## Связи с документацией

| Документ                                                    | Связанные инструменты                                          |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| [03-file-policy.md](governance/03-file-policy.md)           | `audit_structure.py`, `create_pipeline.py`                     |
| [cleanup-policy.md](../03-guides/cleanup-policy.md)         | `cleanup_project.py`, `cleanup_repository.py`, `vacuum_delta.py`, `verify_checksums.py` |
| RULES.md §2                                                 | `naming_audit.py`                                              |
| RULES.md §2.1.1                                             | `vacuum_delta.py`                                              |
| RULES.md §3.4.1                                             | `dq_baseline_update.py`                                        |
| RULES.md §5.4.1                                             | `salt_rotate.py`                                               |
| [glossary.md](glossary.md)                                  | `lint_terminology.py`                                          |
| [03-file-policy.md](governance/03-file-policy.md) (configs) | `config_gap_analysis.py`, `validate_pipeline_configs.py`       |

______________________________________________________________________

## История изменений

| Версия | Дата       | Изменения                                                                                   |
| ------ | ---------- | ------------------------------------------------------------------------------------------- |
| 3.0    | 2026-03-13 | Навигационный hub: детали в `scripts/<group>/README.md`, шаблоны в `04-extending-bioetl.md` |
| 2.4    | 2026-03-12 | Unified entry points (`python -m scripts.<group>`) для всех доменов                         |
| 2.0    | 2026-01-07 | Разделение на src/tools/ и scripts/ по критерию импорта bioetl                              |
| 1.1    | 2026-01-07 | Добавлены все инструменты                                                                   |
| 1.0    | 2025-01-07 | Начальная версия                                                                            |

## CodeRabbit audits

- Playbook: [coderabbit-audit-playbook.md](../03-guides/coderabbit-audit-playbook.md)
- Workflow: `.github/workflows/coderabbit.yml` (CLI on trusted `main` push /
  `workflow_dispatch`; GitHub App on PRs)
- Config: `.coderabbit.yaml` (assertive profile)
- Residual audit report example:
  `reports/grok/review_coderabbit_architecture_audit_20260728_1520_FINAL.md`
- Issue pack example: `.github/ISSUES/ARCH-CR2-2026-07-29-ISSUE-PACK.md`
 
