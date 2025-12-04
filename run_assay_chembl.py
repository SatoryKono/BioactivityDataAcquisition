"""Запуск пайплайна assay_chembl с лимитом 10."""
import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path("src").absolute()))

# Отключаем предупреждения pandera
os.environ["DISABLE_PANDERA_IMPORT_WARNING"] = "True"

from bioetl.interfaces.cli.app import app

# Устанавливаем аргументы командной строки
sys.argv = [
    "bioetl",
    "run",
    "assay_chembl",
    "--config", "configs/pipelines/chembl/assay.yaml",
    "--output", "data/output/assay",
    "--limit", "10"
]

if __name__ == "__main__":
    print("=" * 60)
    print("Запуск пайплайна assay_chembl с лимитом 10 записей")
    print("=" * 60)
    try:
        app()
        print("\n" + "=" * 60)
        print("Пайплайн завершен успешно!")
        print("=" * 60)
    except SystemExit as e:
        if e.code != 0:
            print(f"\n[ОШИБКА] Пайплайн завершился с кодом: {e.code}")
            sys.exit(e.code)
    except KeyboardInterrupt:
        print("\n[ПРЕРВАНО] Выполнение прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ОШИБКА] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

