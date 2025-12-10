#!/usr/bin/env python3
"""
Скрипт для исправления проблемы с импортом numpy из исходников.

Проблема: numpy source tree находится в site-packages вместо установленного пакета.
Решение: удалить исходники и переустановить numpy.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def find_numpy_source_in_site_packages():
    """Найти исходники numpy в site-packages."""
    numpy_sources = []

    for path_str in sys.path:
        if "site-packages" in path_str.lower() or "dist-packages" in path_str.lower():
            site_packages = Path(path_str)
            if not site_packages.exists():
                continue

            # Проверить, есть ли setup.py в site-packages (это исходники)
            if (site_packages / "setup.py").exists():
                numpy_sources.append(site_packages)

            # Проверить, есть ли numpy с setup.py
            numpy_dir = site_packages / "numpy"
            if numpy_dir.exists() and (numpy_dir / "setup.py").exists():
                numpy_sources.append(numpy_dir)

    return numpy_sources


def main():
    """Главная функция."""
    print("=" * 60)
    print("NUMPY IMPORT FIX")
    print("=" * 60)

    # Шаг 1: Проверить PYTHONPATH
    print("\n1. Проверка PYTHONPATH...")
    if "PYTHONPATH" in os.environ:
        pythonpath = os.environ["PYTHONPATH"]
        print(f"   Найден PYTHONPATH: {pythonpath}")

        # Проверить, есть ли там старый проект
        if "bioactivity_data_acquisition1" in pythonpath.lower():
            print("   ⚠️  PYTHONPATH содержит путь к старому проекту")
            print("   Очистка PYTHONPATH...")
            del os.environ["PYTHONPATH"]
            print("   ✓ PYTHONPATH очищен")
        else:
            print("   ✓ PYTHONPATH не содержит проблемных путей")
    else:
        print("   ✓ PYTHONPATH не установлен")

    # Шаг 2: Найти исходники numpy в site-packages
    print("\n2. Поиск исходников numpy в site-packages...")
    numpy_sources = find_numpy_source_in_site_packages()

    if numpy_sources:
        print(f"   Найдено {len(numpy_sources)} исходных деревьев numpy:")
        for source in numpy_sources:
            print(f"   - {source}")

        print("\n   ⚠️  ВНИМАНИЕ: Исходники numpy найдены в site-packages!")
        print("   Это нужно исправить вручную:")
        print("   1. Удалите исходники numpy из site-packages")
        print("   2. Переустановите numpy: pip uninstall numpy && pip install numpy")

        response = input("\n   Удалить найденные исходники автоматически? (y/N): ")
        if response.lower() == "y":
            for source in numpy_sources:
                if source.exists():
                    print(f"   Удаление {source}...")
                    try:
                        if source.is_dir():
                            shutil.rmtree(source)
                        else:
                            source.unlink()
                        print(f"   ✓ Удалено: {source}")
                    except Exception as e:
                        print(f"   ✗ Ошибка при удалении {source}: {e}")
        else:
            print("   Пропущено автоматическое удаление")
    else:
        print("   ✓ Исходники numpy не найдены в site-packages")

    # Шаг 3: Переустановка numpy
    print("\n3. Переустановка numpy...")
    response = input("   Переустановить numpy? (y/N): ")
    if response.lower() == "y":
        print("   Удаление numpy...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "numpy", "-y"],
                check=True,
            )
            print("   ✓ numpy удалён")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Ошибка при удалении: {e}")

        print("   Установка numpy...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "numpy"],
                check=True,
            )
            print("   ✓ numpy установлен")
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Ошибка при установке: {e}")
            return 1
    else:
        print("   Пропущена переустановка")

    # Шаг 4: Проверка импорта
    print("\n4. Проверка импорта numpy...")
    try:
        import numpy

        numpy_file = getattr(numpy, "__file__", None)
        if numpy_file:
            print(f"   ✓ numpy успешно импортирован из: {numpy_file}")
            if "site-packages" in str(numpy_file).lower():
                print("   ✓ numpy импортируется из site-packages (правильно)")
            else:
                print("   ⚠️  numpy импортируется не из site-packages")
        else:
            print("   ✓ numpy успешно импортирован")
    except ImportError as e:
        print(f"   ✗ Ошибка импорта numpy: {e}")
        return 1
    except Exception as e:
        print(f"   ✗ Неожиданная ошибка: {e}")
        return 1

    print("\n" + "=" * 60)
    print("Исправление завершено!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
