# BioETL: Утилиты Проекта

*Версия: 2.4 | Синхронизировано с RULES.md v5.23 (2026-03-12)*

---

## Разграничение src/tools/ и scripts/

Согласно **03-file-policy.md**, проект разделяет вспомогательные скрипты:

| Директория | Назначение | Критерий |
|------------|------------|----------|
| `src/tools/` | Утилиты проекта | **Импортирует** `bioetl` модули |
| `scripts/` | CI/операционные скрипты | **Standalone**, НЕ импортирует `bioetl` |

**Правило**: Если скрипт использует `from bioetl...` или `import bioetl...` → `src/tools/`, иначе → `scripts/`.

---

## Содержание

1. [src/tools/ — Утилиты с зависимостями bioetl](#srctools--утилиты-с-зависимостями-bioetl)
2. [scripts/ — Standalone скрипты](#scripts--standalone-скрипты)
3. [Бенчмарки](#бенчмарки)
4. [Интеграция с Make](#интеграция-с-make)
5. [Добавление нового инструмента](#добавление-нового-инструмента)
6. [Docs Toolchain](#docs-toolchain)

---

## Docs Toolchain

- `mkdocs` pinned to `<2.0` in `pyproject.toml` to avoid known compatibility risk with current Material stack.
- Standard docs checks:
```bash
python -m scripts.docs check-links
make docs-build
bash scripts/docs/build_docs_site.sh --strict
```
- Migration to MkDocs 2.x must be tracked as a dedicated task with explicit compatibility validation.

---

## src/tools/ — Утилиты с зависимостями bioetl

Эти инструменты **импортируют** модули `bioetl` и требуют установленного пакета.

### create_pipeline.py

**Назначение:** Генерация boilerplate-кода для новых BioETL пайплайнов.

**Зависимости bioetl:**
- `bioetl.application.core.base.BasePipeline`
- `bioetl.application.core.base-transformer.BaseTransformer`
- `bioetl.composition.registry.register-pipeline`
- `bioetl.domain.context.PipelineContext`

**Создаёт:**
```
src/bioetl/application/pipelines/{provider}/{entity}/
├── __init__.py
├── pipeline.py      # {Provider}{Entity}Pipeline
├── transformer.py   # {Provider}{Entity}Transformer
└── config.py        # Config model

configs/entities/{provider}/{entity}.yaml
tests/unit/application/pipelines/{provider}/test-{entity}.py
```

**Использование:**
```bash
# Создать новый пайплайн
python src/tools/create_pipeline.py --provider chembl --entity document

# Dry-run (preview без создания файлов)
python src/tools/create_pipeline.py --provider pubchem --entity compound --dry-run
```

| Параметр | Описание |
|----------|----------|
| `--provider` | Имя провайдера (chembl, pubchem, etc.) |
| `--entity` | Имя сущности (activity, molecule, etc.) |
| `--dry-run` | Только показать генерируемые файлы |

**Ссылки:** 03-file-policy.md §Пайплайны

---

### verify_schema_parity.py

**Назначение:** Программная верификация соответствия схем между Domain entities и Infrastructure schemas.

**Зависимости bioetl:**
- `bioetl.domain.entities.bioactivity.Bioactivity`
- `bioetl.domain.entities.chembl_activity.Assay`
- `bioetl.domain.entities.chembl-structures.Molecule, Target`
- `bioetl.infrastructure.schemas.gold`
- `bioetl.infrastructure.schemas.silver`

**Использование:**
```bash
python src/tools/verify_schema_parity.py
```

**Проверяет паритет:**
- `Bioactivity` ↔ `ChEMBLActivityGoldSchema`
- `Molecule` ↔ `ChEMBLMoleculeGoldSchema`
- `Target` ↔ `ChEMBLTargetGoldSchema`
- `Assay` ↔ `ChEMBLAssayGoldSchema`

---

### file_merger.py

**Назначение:** Объединение нескольких файлов проекта в один выходной файл с метаданными.

**Использование:**
```bash
# Объединить файлы из директории
python src/tools/file_merger.py --dir src/bioetl/domain/ --ext .py --output merged.txt
```

| Параметр | Описание |
|----------|----------|
| `--dir` | Директория для рекурсивного обхода |
| `--ext` | Фильтр расширений файлов |
| `--output` | Путь к выходному файлу |

---

## scripts/ — Standalone скрипты

Эти скрипты **НЕ импортируют** `bioetl` и используют только stdlib/внешние библиотеки.

### Unified Entry Points

Каждая каноническая директория предоставляет `__main__.py` dispatcher.
Вместо запоминания имён файлов можно использовать domain-команды:

```bash
python -m scripts.repo check-inventory --check
python -m scripts.qa check-c901 --target src/bioetl
python -m scripts.schema validate-configs
python -m scripts.data check-vcr-naming
python -m scripts.docs check-drift
python -m scripts.diagrams lint
python -m scripts.ci quality-gate
```

Полный список команд: `python -m scripts.<group> --help`

Каждый скрипт также можно запустить напрямую:
```bash
python scripts/qa/check_c901_baseline.py --target src/bioetl
```

### cleanup_project.py

**Назначение:** Очистка кэшей, build-артефактов и временных файлов.

**Использование:**
```bash
# Dry-run (по умолчанию)
python scripts/diagnostics/cleanup_project.py

# Применить изменения с архивированием логов
python scripts/diagnostics/cleanup_project.py --apply --archive-logs

# Полная очистка (включая логи)
python scripts/diagnostics/cleanup_project.py --apply --purge-logs
```

| Флаг | Описание |
|------|----------|
| `--dry-run` | Показать кандидатов на удаление (default) |
| `--apply` | Выполнить удаление |
| `--archive-logs` | Переместить логи в `reports/` |
| `--purge-logs` | Принудительно удалить логи |

**Ссылки:** 05-cleanup-policy.md §4.2

**Make-цель:** `make clean-dev`

---

### cleanup_consolidate.py

**Назначение:** Консолидированный аудит очистки и качества проекта (dry-run по умолчанию).

**Использование:**
```bash
# Dry-run (по умолчанию)
python scripts/diagnostics/cleanup_consolidate.py

# Применить удаление .pyc/--pycache--/temp файлов
python scripts/diagnostics/cleanup_consolidate.py --apply
```

**Что анализирует:**
- `.pyc`, `--pycache--`, временные файлы (по шаблонам cleanup_project.py);
- YAML-конфиги без ссылок в коде/конфигах;
- дубликаты функций в утилитарных модулях (AST);
- неиспользуемые импорты (AST + текстовая проверка);
- неиспользуемые зависимости по `pyproject.toml` и фактическим импортам.

**Связанные инструменты:** `cleanup_project.py` — фактическая очистка кэшей и артефактов.

---

### vacuum_delta.py

**Назначение:** Еженедельный VACUUM для Delta Lake таблиц Silver слоя.

**Использование:**
```bash
# VACUUM всех Silver таблиц
python -m scripts.data vacuum

# VACUUM конкретной таблицы
python -m scripts.data vacuum --table silver/chembl/activity

# С кастомным retention
python -m scripts.data vacuum --retention-days 14

# Alternative (direct script path):
# python scripts/data/vacuum_delta.py [--table ...] [--retention-days ...]
```

| Параметр | Описание | Default |
|----------|----------|---------|
| `--table` | Путь к конкретной таблице | Все Silver |
| `--retention-days` | Период хранения файлов | 7 |
| `--dry-run` | Только показать файлы к удалению | False |

**Ссылки:** RULES.md §2.1.1, 05-cleanup-policy.md §4.3

**Make-цель:** `make vacuum-silver`

---

### salt_rotate.py

**Назначение:** Ротация соли для хеширования PII-данных.

**Использование:**
```bash
# Стандартная ротация
python scripts/ops/salt_rotate.py

# Экстренная ротация (инцидент безопасности)
python scripts/ops/salt_rotate.py --emergency
```

| Параметр | Описание |
|----------|----------|
| `--emergency` | Немедленная ротация без периода перехода |
| `--verify` | Проверить текущее состояние соли |

**Ссылки:** RULES.md §5.4.1

---

### dq_baseline_update.py

**Назначение:** Пересчёт baseline для Data Quality метрик.

**Использование:**
```bash
# Пересчитать baseline для всех пайплайнов
python -m scripts.data dq-baseline

# Для конкретного пайплайна
python -m scripts.data dq-baseline --pipeline chembl_activity

# Alternative (direct script path):
# python scripts/data/dq_baseline_update.py [--pipeline ...]
```

| Параметр | Описание |
|----------|----------|
| `--pipeline` | Имя пайплайна (default: все) |
| `--window-days` | Окно для расчёта baseline |

**Ссылки:** RULES.md §3.4.1

---

### verify_checksums.py

**Назначение:** Верификация контрольных сумм критических артефактов после DR-восстановления.

**Использование:**
```bash
python -m scripts.data checksums
python -m scripts.data checksums --table silver/chembl/activity

# Alternative (direct script path):
# python scripts/data/verify_checksums.py [--table ...]
```

**Ссылки:** 05-cleanup-policy.md §5.2

**Make-цель:** `make verify-checksums`

---

### audit_structure.py

**Назначение:** Проверяет соответствие структуры проекта File Policy (`03-file-policy.md`).

**Использование:**
```bash
# Стандартный аудит
python scripts/diagnostics/audit_structure.py

# JSON вывод для CI
python scripts/diagnostics/audit_structure.py --json

# Строгий режим (SHOULD violations = exit 1)
python scripts/diagnostics/audit_structure.py --strict
```

| Флаг | Описание |
|------|----------|
| `--json` | Вывод результатов в JSON формате |
| `--strict` | Exit code 1 при нарушениях SHOULD (default: только MUST) |

**Ссылки:** 03-file-policy.md

---

### naming_audit.py

**Назначение:** Валидация naming conventions согласно RULES.md §2.

**Проверяет:**
- Classes: PascalCase с role-appropriate суффиксами
- Modules: snake-case
- Functions: snake-case с семантическими префиксами
- Documentation: kebab-case (или NN- префикс для ordered docs)
- YAML Configs: snake-case
- Constants: UPPER-SNAKE-CASE

**Использование:**
```bash
# Полный аудит
python -m scripts.qa check-naming

# CI режим (exit 1 при нарушениях)
python -m scripts.qa check-naming --check

# Сохранить отчёт в файл
python -m scripts.qa check-naming --output report.md

# Alternative (direct script path):
# python scripts/qa/naming_audit.py [--check] [--output ...]
```

**Ссылки:** RULES.md §2, docs/glossary.md

---

### lint_terminology.py

**Назначение:** Линтер для проверки терминологии в коде и документации.

**Использование:**
```bash
# Проверить весь проект
python -m scripts.qa check-terminology

# Проверить конкретный файл
python scripts/qa/lint_terminology.py src/bioetl/domain/models/molecule.py

# Строгий режим (дополнительные context-sensitive проверки)
python scripts/qa/lint_terminology.py --strict src/bioetl/
```

**Что проверяет:**
- Соответствие терминов `docs/glossary.md`
- Provider-specific naming (Molecule vs Compound)
- Deprecated terms

**Ссылки:** docs/glossary.md

---

### scripts/diagrams/run_diagram_checks.sh

**Назначение:** Валидация и рендеринг Mermaid диаграмм из `docs/`.

**Использование:**
```bash
bash scripts/diagrams/run_diagram_checks.sh
```

> **Примечание:** Используйте этот скрипт как основной entrypoint для проверок диаграмм.

---

### config_gap_analysis.py

**Назначение:** Анализ расхождений между конфигурациями пайплайнов и фактическим кодом.

**Использование:**
```bash
python -m scripts.schema analyze-gaps

# Alternative (direct script path):
# python scripts/schema/config_gap_analysis.py
```

**Что анализирует:**
- Пропущенные entity configs для зарегистрированных пайплайнов
- Несоответствия между конфигурацией и кодовой базой
- Отсутствующие поля в entity configs

---

### validate_pipeline_configs.py

**Назначение:** Валидация всех pipeline configs против JSON Schema.

**Использование:**
```bash
python -m scripts.schema validate-configs

# Alternative (direct script path):
# python scripts/schema/validate_pipeline_configs.py
```

**Что проверяет:**
- Соответствие `-schema.json` для всех entity configs
- Обязательные поля (`pipeline_name`, `provider`, `entity-type`, etc.)
- Корректность `sink` путей и `sort-by` конфигурации

---

## Бенчмарки

Директория `src/tools/benchmarks/` содержит performance-тесты для критических операций.

| Файл | Назначение |
|------|------------|
| `test_bronze_write.py` | Бенчмарки записи Bronze слоя |
| `test_delta_write.py` | Бенчмарки Delta Lake операций |
| `test_json_serialization.py` | Сравнение JSON encoders (stdlib vs orjson) |

```bash
# Запуск бенчмарков
pytest src/tools/benchmarks/ -v --benchmark-only
```

---

## Интеграция с Make

```makefile
# Очистка
clean-dev:
    python scripts/diagnostics/cleanup_project.py --apply --purge-logs

# Delta Lake maintenance
vacuum-silver:
    python scripts/data/vacuum_delta.py

# Верификация
verify-checksums:
    python scripts/data/verify_checksums.py

# Аудит
audit-structure:
    python scripts/diagnostics/audit_structure.py

audit-naming:
    python scripts/qa/naming_audit.py

# Создание пайплайна (требует bioetl)
new-pipeline:
    python src/tools/create_pipeline.py --provider $(PROVIDER) --entity $(ENTITY)
```

---

## Добавление нового инструмента

### Критерий размещения

1. Скрипт импортирует `bioetl` → **src/tools/**
2. Скрипт standalone (только stdlib/внешние) → **scripts/**

### Шаблон для src/tools/ (с bioetl)

```python
#!/usr/bin/env python3
"""
{tool-name}.py - {краткое описание}.

Использование:
    python src/tools/{tool-name}.py [--option VALUE]

Зависимости bioetl:
    - bioetl.{module}

Ссылки:
    - RULES.md §X.Y: {описание правила}
"""
from __future__ import annotations

import argparse
from pathlib import Path

from bioetl.infrastructure.logging import get_logger

logger = get_logger(__name__)
PROJECT_ROOT = Path(__file__).parent.parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    logger.info("Starting tool", tool=__name__, dry-run=args.dry-run)
    # ... implementation ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### Шаблон для scripts/ (standalone)

```python
#!/usr/bin/env python3
"""
{script-name}.py - {краткое описание}.

Standalone скрипт (НЕ импортирует bioetl).

Использование:
    python scripts/{script-name}.py [--option VALUE]

Ссылки:
    - RULES.md §X.Y: {описание правила}
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()

    # ... implementation (без bioetl imports) ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Сводная таблица

| Файл | Директория | Импортирует bioetl | Unified command | Make-цель |
|------|------------|-------------------|-----------------|-----------|
| `create_pipeline.py` | src/tools/ | Да | — | `make new-pipeline` |
| `verify_schema_parity.py` | src/tools/ | Да | — | — |
| `file_merger.py` | src/tools/ | Нет | — | — |
| `cleanup_project.py` | scripts/ | Нет | — | `make clean-dev` |
| `vacuum_delta.py` | scripts/ | Нет | `python -m scripts.data vacuum` | `make vacuum-silver` |
| `salt_rotate.py` | scripts/ | Нет | — | — |
| `dq_baseline_update.py` | scripts/ | Нет | `python -m scripts.data dq-baseline` | — |
| `verify_checksums.py` | scripts/ | Нет | `python -m scripts.data checksums` | `make verify-checksums` |
| `audit_structure.py` | scripts/ | Нет | — | `make audit-structure` |
| `naming_audit.py` | scripts/ | Нет | `python -m scripts.qa check-naming` | `make audit-naming` |
| `lint_terminology.py` | scripts/ | Нет | `python -m scripts.qa check-terminology` | — |
| `build_diagram_docs.py` | src/tools/ | Да | — | — |
| `config_gap_analysis.py` | scripts/ | Нет | `python -m scripts.schema analyze-gaps` | — |
| `validate_pipeline_configs.py` | scripts/ | Нет | `python -m scripts.schema validate-configs` | — |

---

## Связи с документацией

| Документ | Связанные инструменты |
|----------|----------------------|
| 03-file-policy.md | `audit_structure.py`, `create_pipeline.py` |
| 05-cleanup-policy.md | `cleanup_project.py`, `vacuum_delta.py`, `verify_checksums.py` |
| RULES.md §2 | `naming_audit.py` |
| RULES.md §2.1.1 | `vacuum_delta.py` |
| RULES.md §3.4.1 | `dq_baseline_update.py` |
| RULES.md §5.4.1 | `salt_rotate.py` |
| docs/glossary.md | `lint_terminology.py` |
| 03-file-policy.md (configs) | `config_gap_analysis.py`, `validate_pipeline_configs.py` |

---

## История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 2.4 | 2026-03-12 | Unified entry points (`python -m scripts.<group>`) для всех доменов |
| 2.0 | 2026-01-07 | Разделение на src/tools/ и scripts/ по критерию импорта bioetl |
| 1.1 | 2026-01-07 | Добавлены все инструменты |
| 1.0 | 2025-01-07 | Начальная версия |
