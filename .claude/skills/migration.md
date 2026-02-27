# /migration

Создание и запуск миграций данных для BioETL Delta Lake tables.

## Использование

```
/migration [action] [target]
```

**Действия:**
- `list` — перечислить существующие миграции (по умолчанию)
- `create` — создать новую миграцию
- `run` — запустить миграцию
- `dry-run` — запустить миграцию в dry-run режиме
- `status` — показать статус Delta tables

**Target:**
- Имя миграции (для `run`/`dry-run`)
- Описание изменения (для `create`)

**Примеры:**
```
/migration list                             # показать все миграции
/migration create rename_field_X_to_Y       # создать новую миграцию
/migration run migrate_pmid_to_string       # запустить миграцию
/migration dry-run rename_structure_fields  # dry-run
/migration status                           # статус Delta tables
```

---

## Инструкции для Claude

### Действие: `list` (по умолчанию)

```bash
ls -la src/tools/scripts/migrations/*.py | grep -v __
```

Для каждой миграции показать:
- Имя файла
- Описание (из docstring)
- Дата создания (git log)
- Статус: applied / pending / unknown

### Действие: `create`

**Шаг 1:** Определить параметры миграции. Спросить через AskUserQuestion:
1. **Название** — snake_case (e.g., `rename_field_x_to_y`)
2. **Описание** — что мигрируется и зачем
3. **Target tables** — какие Silver/Gold Delta tables затрагиваются
4. **Операция** — rename field / cast type / add column / drop column / transform values

**Шаг 2:** Изучить существующие миграции:
```bash
cat src/tools/scripts/migrations/migrate_pmid_to_string.py
```

**Шаг 3:** Создать миграцию по шаблону:

```python
"""<Описание миграции>.

Migrates <что именно> in <какие таблицы>.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import polars as pl
from deltalake import DeltaTable

logger = logging.getLogger(__name__)


def migrate(data_dir: Path, *, dry_run: bool = False) -> int:
    """Run the migration.

    Args:
        data_dir: Root data directory containing Delta tables.
        dry_run: If True, only report what would change.

    Returns:
        0 on success, 1 on failure.
    """
    tables = [
        data_dir / "silver" / "<provider>" / "<entity>",
    ]

    for table_path in tables:
        if not table_path.exists():
            logger.warning("Table not found: %s", table_path)
            continue

        dt = DeltaTable(str(table_path))
        df = pl.read_delta(str(table_path))

        logger.info(
            "Table %s: %d rows, columns: %s",
            table_path.name,
            len(df),
            df.columns,
        )

        if dry_run:
            logger.info("[DRY RUN] Would migrate table %s", table_path.name)
            continue

        # === MIGRATION LOGIC HERE ===
        # df = df.with_columns(...)
        # df.write_delta(str(table_path), mode="overwrite", overwrite_schema=True)

        logger.info("Migrated table %s", table_path.name)

    return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/output"),
        help="Root data directory (default: data/output)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would change",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before migration",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.backup:
        logger.info("Creating backup...")
        # backup logic here

    exit_code = migrate(args.data_dir, dry_run=args.dry_run)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
```

**Шаг 4:** Верификация:
```bash
uv run python src/tools/scripts/migrations/{name}.py --dry-run
```

### Действие: `run`

```bash
uv run python src/tools/scripts/migrations/{target}.py --data-dir data/output
```

### Действие: `dry-run`

```bash
uv run python src/tools/scripts/migrations/{target}.py --data-dir data/output --dry-run
```

### Действие: `status`

```bash
# Перечислить Delta tables
find data/output/ -name "_delta_log" -type d 2>/dev/null | sed 's|/_delta_log||' | sort
```

Для каждой таблицы показать: путь, версия, количество файлов, размер.
