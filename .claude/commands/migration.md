---
description: Создание и запуск миграций Delta Lake таблиц BioETL. Действия: list, create, run, dry-run, status. Пример: /migration create rename_field_X_to_Y
---

# /migration

Создание и запуск миграций данных для BioETL Delta Lake tables.

## Использование
```
/migration [action] [target]
```

**Действия:** `list` (default), `create`, `run`, `dry-run`, `status`

---

## Инструкции

### `list` (default)
```bash
find scripts/migrations -type f -name '*.py' | sort
```
Per migration: filename, description (docstring), date (git log), status (applied/pending).

### `create`

Ask via AskUserQuestion: name (snake_case), description, target tables (Silver/Gold), operation (rename/cast/add/drop/transform).

Study existing: `find scripts/migrations -type f -name '*.py' | sort | head`

Template:
```python
"""<Description>.

Migrates <what> in <which tables>.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import polars as pl
from deltalake import DeltaTable

logger = logging.getLogger(__name__)


def migrate(data_dir: Path, *, dry_run: bool = False) -> int:
    tables = [
        data_dir / "silver" / "<provider>" / "<entity>",
    ]
    for table_path in tables:
        if not table_path.exists():
            logger.warning("Table not found: %s", table_path)
            continue
        dt = DeltaTable(str(table_path))
        df = pl.read_delta(str(table_path))
        logger.info("Table %s: %d rows, columns: %s", table_path.name, len(df), df.columns)
        if dry_run:
            logger.info("[DRY RUN] Would migrate table %s", table_path.name)
            continue
        # === MIGRATION LOGIC HERE ===
        logger.info("Migrated table %s", table_path.name)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/output"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.backup:
        logger.info("Creating backup...")
    exit_code = migrate(args.data_dir, dry_run=args.dry_run)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
```

Verify: `uv run python scripts/migrations/{active|oneoff}/{name}.py --dry-run`

### `run`
```bash
uv run python scripts/migrations/{target}.py --data-dir data/output
```

### `dry-run`
```bash
uv run python scripts/migrations/{target}.py --data-dir data/output --dry-run
```

### `status`
```bash
find data/output/ -name "_delta_log" -type d 2>/dev/null | sed 's|/_delta_log||' | sort
```
Per table: path, version, file count, size.
