from __future__ import annotations

import ast
from collections import defaultdict
import importlib
import inspect
from pathlib import Path

import yaml


# -----------------------------------------------------------------------------
# T01_DUPL_CLASS_NAMES
# Название: Уникальные имена классов в пайплайнах
# Цель: убедиться, что в каталоге пайплайнов нет повторяющихся имен классов.
# При добавлении нового класса дублирующийся функционал должен быть
# удален или объединен (принцип zero‑sum class count), поэтому каждый
# класс в `src/bioetl/application/pipelines/` должен иметь уникальное имя.
def test_no_duplicate_class_names(project_root: Path) -> None:
    root = project_root / "src/bioetl/application/pipelines"
    class_occurrences: dict[str, list[Path]] = defaultdict(list)
    for file_path in sorted(root.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_occurrences[node.name].append(file_path)
    duplicates = {
        cls: files for cls, files in class_occurrences.items() if len(files) > 1
    }
    assert not duplicates, f"Повторяющиеся имена классов обнаружены: {duplicates}"


# -----------------------------------------------------------------------------
# T02_DUPL_FUNC_NAMES
# Название: Уникальные модульные функции
# Цель: проверить, что модульные функции (не методы классов) в пайплайнах
# объявлены один раз. Одинаковые имена функций в разных модулях могут
# указывать на дублирование логики, что нарушает принцип DRY.
def test_no_duplicate_module_functions(project_root: Path) -> None:
    root = project_root / "src/bioetl/application/pipelines"
    func_occurrences: dict[str, list[Path]] = defaultdict(list)
    for file_path in sorted(root.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                func_occurrences[node.name].append(file_path)
    duplicates = {fn: files for fn, files in func_occurrences.items() if len(files) > 1}
    assert not duplicates, f"Дублирующиеся функции найдены: {duplicates}"


# -----------------------------------------------------------------------------
# T03_DUPL_FUNC_BODY
# Название: Дублирование тела функций
# Цель: выявить функции с одинаковым абстрактным синтаксическим деревом (AST).
# Если две функции имеют идентичную структуру, возможно, их стоит
# объединить или вынести в общий модуль. Тест игнорирует приватные
# функции (начинающиеся с `_`).
def test_no_duplicate_function_bodies(project_root: Path) -> None:
    root = project_root / "src/bioetl/application/pipelines"
    body_hashes: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    for file_path in sorted(root.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                body = ast.dump(node, include_attributes=False)
                body_hashes[body].append((file_path, node.name))
    duplicates = {body: locs for body, locs in body_hashes.items() if len(locs) > 1}
    assert not duplicates, "Найдены дублирующиеся тела функций: " + ", ".join(
        f"{locs}" for locs in duplicates.values()
    )


# -----------------------------------------------------------------------------
# T04_PIPELINE_INHERIT_BASE
# Название: Наследование от базовых классов
# Цель: убедиться, что каждый конкретный пайплайн наследует `PipelineBase`
# или `ChemblPipelineBase`. Это обеспечивает повторное использование
# общих стадий и исключает дублирование реализации ETL.
def test_pipeline_inherits_base(project_root: Path) -> None:
    root = project_root / "src/bioetl/application/pipelines"
    src_root = project_root / "src"
    for file_path in sorted(root.rglob("*/pipeline.py")):
        module_name = ".".join(file_path.with_suffix("").relative_to(src_root).parts)
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module_name:
                bases = [base.__name__ for base in cls.mro()[1:]]
                assert any(
                    base in {"PipelineBase", "ChemblPipelineBase"} for base in bases
                ), (
                    f"{cls.__name__} не наследует базовый класс "
                    "PipelineBase/ChemblPipelineBase"
                )


# -----------------------------------------------------------------------------
# T05_CONST_DUPLICATE_VALUES
# Название: Дублирование констант
# Цель: проверить, что значения констант (имена в UPPER_SNAKE_CASE) не
# копируются в разных модулях. Одинаковое значение в нескольких местах
# указывает на необходимость вынести константу в общее место.
def test_no_duplicate_constant_values(project_root: Path) -> None:
    root = project_root / "src/bioetl"
    value_map: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    for file_path in sorted(root.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if name.isupper() and isinstance(node.value, ast.Constant):
                            literal = node.value.value
                            if literal in (True, False, None):
                                continue
                            value_map[str(literal)].append((name, file_path))
    duplicates = {
        val: bindings for val, bindings in value_map.items() if len(bindings) > 1
    }
    assert not duplicates, f"Найдены дублирующиеся значения констант: {duplicates}"


# -----------------------------------------------------------------------------
# T06_SCHEMA_DUPLICATE_DEFINITION
# Название: Уникальность файлов схем
# Цель: убедиться, что в каталоге `src/bioetl/domain/schemas` нет двух файлов
# схем с одинаковым именем. Дублирующие имена могут означать повторение
# определения схемы для разных сущностей, что затрудняет сопровождение.
def test_no_duplicate_schema_filenames(project_root: Path) -> None:
    root = project_root / "src/bioetl/domain/schemas"
    file_occurrences: dict[str, list[Path]] = defaultdict(list)
    for file_path in sorted(root.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue
        file_occurrences[file_path.name].append(file_path)
    duplicates = {
        name: files for name, files in file_occurrences.items() if len(files) > 1
    }
    assert not duplicates, f"Дублирующиеся файлы схем: {duplicates}"


# -----------------------------------------------------------------------------
# T07_YAML_PIPELINE_ID_UNIQUE
# Название: Уникальные идентификаторы YAML‑пайплайнов
# Цель: проверить, что каждое описание пайплайна в `configs/pipelines` имеет
# уникальный идентификатор `id`. Несколько YAML с одинаковым `id`
# приводят к конфликтам и дублированию ETL‑логики.
def test_yaml_pipeline_ids_unique(configs_root: Path) -> None:
    ids: dict[str, Path] = {}
    root = configs_root / "pipelines"
    for file_path in sorted(root.rglob("*.yaml")):
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        pipe_id = data.get("id")
        if pipe_id:
            assert (
                pipe_id not in ids
            ), f"Дублирующийся id '{pipe_id}' в {file_path} и {ids[pipe_id]}"
            ids[pipe_id] = file_path


# -----------------------------------------------------------------------------
# T08_CLI_DUPLICATE_COMMANDS
# Название: Уникальность CLI‑команд
# Цель: убедиться, что команды Typer, определённые в интерфейсном слое
# (`src/bioetl/interfaces/cli`), имеют уникальные имена. Дублирование
# команд может приводить к неожиданным конфликтам при запуске.
def test_cli_commands_unique(project_root: Path) -> None:
    cli_dir = project_root / "src/bioetl/interfaces/cli"
    command_names: dict[str, Path] = {}
    for file_path in sorted(cli_dir.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                cmd_name = None
                for deco in node.decorator_list:
                    if (
                        isinstance(deco, ast.Call)
                        and isinstance(deco.func, ast.Attribute)
                        and deco.func.attr == "command"
                    ):
                        for kw in deco.keywords:
                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                cmd_name = kw.value.value
                        if cmd_name is None:
                            cmd_name = node.name
                        if cmd_name in command_names:
                            raise AssertionError(
                                "Дублирующаяся CLI‑команда "
                                f"'{cmd_name}' в {file_path} и "
                                f"{command_names[cmd_name]}"
                            )
                        command_names[cmd_name] = file_path


# -----------------------------------------------------------------------------
# T09_ABC_IMPL_DUPLICATE
# Название: Единственная реализация для каждого ABC
# Цель: проверить, что каждой абстракции (ABC) в реестрах соответствует
# не более одной Default‑/Impl‑реализации. Дублирование реализаций
# нарушает паттерн ABC/Default/Impl и усложняет поддержку.
def test_abc_impls_unique(configs_root: Path) -> None:
    registry_path = configs_root / "abc_registry.yaml"
    impls_path = configs_root / "abc_impls.yaml"
    if not (registry_path.exists() and impls_path.exists()):
        return
    impls_data = yaml.safe_load(impls_path.read_text(encoding="utf-8"))
    if not isinstance(impls_data, dict):
        return
    reverse_map: dict[str, list[str]] = defaultdict(list)
    for abc, impl in impls_data.items():
        reverse_map[str(impl)].append(str(abc))
    duplicates = {impl: abcs for impl, abcs in reverse_map.items() if len(abcs) > 1}
    assert (
        not duplicates
    ), f"Для следующих реализаций назначено несколько ABC: {duplicates}"


# -----------------------------------------------------------------------------
# T10_TEST_NAME_UNIQUE
# Название: Уникальные имена тестовых функций
# Цель: убедиться, что каждая функция теста (`test_`) в каталоге `tests/`
# имеет уникальное имя. Дублирующиеся названия тестов могут скрывать
# дублирование логики и усложнять отладку.
def test_test_function_names_unique(project_root: Path) -> None:
    root = project_root / "tests"
    seen_names: dict[str, Path] = {}
    for file_path in sorted(root.rglob("test_*.py")):
        if file_path.name == "__init__.py":
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                if node.name in seen_names:
                    raise AssertionError(
                        "Имя тестовой функции "
                        f"'{node.name}' повторяется в {file_path} и "
                        f"{seen_names[node.name]}"
                    )
                seen_names[node.name] = file_path
