from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

import yaml
import pytest

from src.tools.check_naming_policy import (
    check_file_content,
    check_file_naming,
)


ROOT_SRC = Path("src/bioetl")
ROOT_TESTS = Path("tests")
ROOT_DOCS = Path("docs")
PIPELINES_CONFIGS = Path("configs/pipelines")
NAMING_EXCEPTIONS_PATH = Path("configs/naming_exceptions.yaml")


MODULE_NAME_PATTERN = re.compile(r"^[a-z0-9_]+\.py$")
SNAKE_CASE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
UPPER_SNAKE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
KEBAB_CASE_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PIPELINE_ID_PATTERN = re.compile(r"^[a-z0-9]+_[a-z0-9]+$")
CLASS_CASE_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]+$")

ALLOWED_CLASS_SUFFIXES: tuple[str, ...] = (
    "Factory",
    "Client",
    "Facade",
    "Registry",
    "Adapter",
    "Transport",
    "Protocol",
    "ABC",
    "Config",
    "Model",
    "Params",
    "Error",
    "Impl",
)

ALLOWED_FUNCTION_PREFIXES: tuple[str, ...] = (
    "get_",
    "fetch_",
    "request_",
    "iter_",
    "extract_",
    "create_",
    "build_",
    "make_",
    "default_",
    "register_",
    "resolve_",
    "ensure_",
    "validate_",
    "parse_",
    "serialize_",
    "notify_",
    "process_",
    "handle_",
    "write_",
    "set_",
    "update_",
    "finish_",
    "inject_",
    "reset_",
    "execute_",
    "on_",
    "is_",
    "has_",
    "can_",
    "test_",
    "fixture_",
    "mock_",
    "sample_",
    "info",
    "error",
    "debug",
    "warning",
    "visit_",
    "apply",
    "pre_",
    "do_",
    "run",
    "start",
    "end_",
    "stop",
    "close",
    "bind",
    "main",
)

PIPELINE_STAGE_FILES = {"extract.py", "transform.py", "validate.py", "export.py"}
DOC_HEADER_EXCLUDE = {"README.md", "INDEX.md", "ABC_INDEX.md"}


def test_naming_policy_respected() -> None:
    exceptions = load_exceptions()
    violations: dict[str, list[str]] = {}

    for path in Path("src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        file_violations = check_file_naming(path, exceptions)
        content_violations = check_file_content(path, exceptions)
        combined = file_violations + content_violations
        if combined:
            violations[path.as_posix()] = combined

    if violations:
        formatted = []
        for file_path, items in sorted(violations.items()):
            for item in items:
                formatted.append(f"{file_path}: {item}")
        pytest.fail("\n".join(formatted))


@dataclass(frozen=True)
class ExceptionIndex:
    by_path: Mapping[str, frozenset[str]]

    def is_excepted(self, path: Path, rule_id: str) -> bool:
        normalized = path.as_posix()
        return rule_id in self.by_path.get(normalized, frozenset())


def load_exceptions() -> ExceptionIndex:
    if not NAMING_EXCEPTIONS_PATH.exists():
        return ExceptionIndex(by_path={})
    data = yaml.safe_load(NAMING_EXCEPTIONS_PATH.read_text(encoding="utf-8")) or {}
    entries = data.get("exceptions", []) or []
    by_path: dict[str, set[str]] = {}
    for entry in entries:
        path = entry.get("path")
        rule_id = entry.get("rule_id")
        if not path or not rule_id:
            continue
        by_path.setdefault(path, set()).add(rule_id)
    return ExceptionIndex(by_path={k: frozenset(v) for k, v in by_path.items()})


def iter_python_files(root: Path) -> Iterator[Path]:
    for file in root.rglob("*.py"):
        if "__pycache__" in file.parts:
            continue
        yield file


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _is_pytest_fixture(node: ast.FunctionDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Attribute) and decorator.attr == "fixture":
            return True
        if isinstance(decorator, ast.Name) and decorator.id == "fixture":
            return True
    return False


def _iter_module_level_assign_targets(node: ast.Assign) -> Iterator[ast.Name]:
    for target in node.targets:
        if isinstance(target, ast.Name):
            yield target


def _is_property_method(node: ast.FunctionDef) -> bool:
    return any(
        isinstance(decorator, ast.Name) and decorator.id == "property"
        for decorator in node.decorator_list
    )


def _is_typevar(value: ast.AST) -> bool:
    return isinstance(value, ast.Call) and (
        (isinstance(value.func, ast.Name) and value.func.id == "TypeVar")
        or (isinstance(value.func, ast.Attribute) and value.func.attr == "TypeVar")
    )


def _is_type_alias(name: str, value: ast.AST) -> bool:
    if not CLASS_CASE_PATTERN.match(name):
        return False
    if _is_typevar(value):
        return True
    return isinstance(value, (ast.Name, ast.Attribute, ast.Subscript))


def _collect_first_h1(path: Path) -> str | None:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#"):
                return line.lstrip("#").strip()
    return None


def _iter_pipeline_entity_dirs() -> Iterator[Path]:
    root = ROOT_SRC / "application" / "pipelines"
    if not root.exists():
        return iter(())
    for provider_dir in root.iterdir():
        if not provider_dir.is_dir():
            continue
        for entity_dir in provider_dir.iterdir():
            if entity_dir.is_dir() and entity_dir.name != "__pycache__":
                yield entity_dir


def test_t01_module_name_format() -> None:
    exceptions = load_exceptions()
    bad = []
    for file in iter_python_files(ROOT_SRC):
        if "tests" in file.parts:
            continue
        if exceptions.is_excepted(file, "MODULE_NAME"):
            continue
        if not MODULE_NAME_PATTERN.match(file.name):
            bad.append(file.as_posix())
    assert not bad, f"Нарушение snake_case в модулях: {sorted(bad)}"


def test_t02_global_name_conventions() -> None:
    exceptions = load_exceptions()
    violations: list[str] = []
    for file in iter_python_files(ROOT_SRC):
        if "tests" in file.parts:
            continue
        tree = _load_ast(file)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                name = node.name
                if name.startswith("__"):
                    continue
                if exceptions.is_excepted(file, "FUNC_FORMAT"):
                    continue
                if not SNAKE_CASE_PATTERN.match(name):
                    violations.append(f"{file.as_posix()}: function {name}")
            elif isinstance(node, ast.Assign):
                for target in _iter_module_level_assign_targets(node):
                    name = target.id
                    if name.isupper():
                        if exceptions.is_excepted(file, "CONST_FORMAT"):
                            continue
                        if not UPPER_SNAKE_PATTERN.match(name):
                            violations.append(f"{file.as_posix()}: constant {name}")
                    else:
                        if exceptions.is_excepted(file, "FUNC_FORMAT"):
                            continue
                        if _is_type_alias(name, node.value):
                            continue
                        if not SNAKE_CASE_PATTERN.match(name):
                            violations.append(f"{file.as_posix()}: variable {name}")
    assert not violations, f"Нарушения в именах глобальных переменных/функций: {sorted(violations)}"


def test_t03_class_suffix_pascal_case() -> None:
    exceptions = load_exceptions()
    violations: list[str] = []
    for file in iter_python_files(ROOT_SRC):
        if "tests" in file.parts:
            continue
        tree = _load_ast(file)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            name = node.name
            if name.startswith("Test") or name.startswith("_"):
                continue
            if not name or not name[0].isupper() or "_" in name:
                if not exceptions.is_excepted(file, "CLASS_FORMAT"):
                    violations.append(f"{file.as_posix()}: {name} формат")
                continue
            if not any(name.endswith(suffix) for suffix in ALLOWED_CLASS_SUFFIXES):
                if not exceptions.is_excepted(file, "CLASS_SUFFIX"):
                    violations.append(f"{file.as_posix()}: {name} суффикс")
    assert not violations, f"Классы с неправильным именованием: {sorted(violations)}"


def test_t04_no_camelcase_or_hyphen_names() -> None:
    exceptions = load_exceptions()
    violations: list[str] = []
    for file in iter_python_files(ROOT_SRC):
        if "tests" in file.parts:
            continue
        if "-" in file.name or " " in file.name:
            violations.append(f"{file.as_posix()}: имя файла")
        tree = _load_ast(file)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                name = node.name
                if name.startswith("__"):
                    continue
                if exceptions.is_excepted(file, "FUNC_FORMAT"):
                    continue
                if not SNAKE_CASE_PATTERN.match(name) and not name.isupper():
                    violations.append(f"{file.as_posix()}: функция {name}")
            elif isinstance(node, ast.Assign):
                for target in _iter_module_level_assign_targets(node):
                    name = target.id
                    if name.isupper():
                        if exceptions.is_excepted(file, "CONST_FORMAT"):
                            continue
                        if not UPPER_SNAKE_PATTERN.match(name):
                            violations.append(f"{file.as_posix()}: константа {name}")
                    else:
                        if exceptions.is_excepted(file, "FUNC_FORMAT"):
                            continue
                        if _is_type_alias(name, node.value):
                            continue
                        if not SNAKE_CASE_PATTERN.match(name):
                            violations.append(f"{file.as_posix()}: переменная {name}")
            elif isinstance(node, ast.ClassDef):
                name = node.name
                if name.startswith("_"):
                    continue
                if "-" in name or " " in name:
                    violations.append(f"{file.as_posix()}: класс {name}")
    assert not violations, f"Выявлены camelCase/дефис/пробел в именах: {sorted(violations)}"


def _has_allowed_prefix(name: str) -> bool:
    return any(name.startswith(prefix) for prefix in ALLOWED_FUNCTION_PREFIXES)


def test_t05_function_prefix_rules() -> None:
    exceptions = load_exceptions()
    violations: list[str] = []
    for file in iter_python_files(ROOT_SRC):
        if "tests" in file.parts:
            continue
        tree = _load_ast(file)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                name = node.name
                if name.startswith("__") or name.startswith("test_") or name.startswith("_"):
                    continue
                if _is_pytest_fixture(node):
                    continue
                if _is_property_method(node):
                    continue
                if exceptions.is_excepted(file, "FUNC_PREFIX"):
                    continue
                if not _has_allowed_prefix(name):
                    violations.append(f"{file.as_posix()}: {name}")
            elif isinstance(node, ast.ClassDef):
                for method in (item for item in node.body if isinstance(item, ast.FunctionDef)):
                    name = method.name
                    if name.startswith("__") or name.startswith("_"):
                        continue
                    if _is_property_method(method):
                        continue
                    if exceptions.is_excepted(file, "FUNC_PREFIX"):
                        continue
                    if not _has_allowed_prefix(name):
                        violations.append(f"{file.as_posix()}: {node.name}.{name}")
    assert not violations, f"Функции/методы без разрешённых префиксов: {sorted(violations)}"


def _iter_pipeline_configs() -> Iterable[Path]:
    if not PIPELINES_CONFIGS.exists():
        return []
    return PIPELINES_CONFIGS.rglob("*.yaml")


def test_t06_pipeline_id_pattern() -> None:
    bad: list[str] = []
    for file in _iter_pipeline_configs():
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            bad.append(f"{file.as_posix()}: пустой или некорректный YAML")
            continue
        pipeline_id = data.get("id")
        if not pipeline_id or not isinstance(pipeline_id, str):
            bad.append(f"{file.as_posix()}: отсутствует id")
            continue
        if not PIPELINE_ID_PATTERN.match(pipeline_id):
            bad.append(f"{file.as_posix()}: id {pipeline_id}")
    assert not bad, f"Идентификаторы пайплайнов нарушают формат: {sorted(bad)}"


def test_t07_pipeline_stage_filenames() -> None:
    violations: list[str] = []
    for entity_dir in _iter_pipeline_entity_dirs():
        actual = {file.name for file in entity_dir.iterdir() if file.is_file()}
        missing = PIPELINE_STAGE_FILES - actual
        unexpected = {name for name in actual if name.lower() in PIPELINE_STAGE_FILES and name not in PIPELINE_STAGE_FILES}
        if missing or unexpected:
            violations.append(
                f"{entity_dir.as_posix()}: missing={sorted(missing)}, unexpected={sorted(unexpected)}"
            )
    assert not violations, f"Нарушения в именах файлов этапов: {sorted(violations)}"


def test_t08_test_filename_conventions() -> None:
    violations: list[str] = []
    for file in ROOT_TESTS.rglob("*.py"):
        if "__pycache__" in file.parts:
            continue
        if not file.name.startswith("test_"):
            violations.append(f"{file.as_posix()}: не начинается с test_")
        if "golden" in file.stem and not file.name.endswith("_golden.py"):
            violations.append(f"{file.as_posix()}: golden без суффикса _golden")
    assert not violations, f"Нарушены правила именования тестовых файлов: {sorted(violations)}"


def test_t09_doc_filename_case() -> None:
    violations: list[str] = []
    for file in ROOT_DOCS.rglob("*.md"):
        if file.name in DOC_HEADER_EXCLUDE:
            continue
        stem = file.stem
        if not KEBAB_CASE_PATTERN.match(stem):
            violations.append(file.as_posix())
    assert not violations, f"Файлы документации нарушают kebab-case/англ.названия: {sorted(violations)}"


def test_t10_doc_header_match_filename() -> None:
    violations: list[str] = []
    for file in ROOT_DOCS.rglob("*.md"):
        if file.name in DOC_HEADER_EXCLUDE:
            continue
        header = _collect_first_h1(file)
        if not header:
            violations.append(f"{file.as_posix()}: нет H1")
            continue
        header_slug = slugify(header)
        file_slug = slugify(file.stem)
        file_slug = re.sub(r"^\d+-", "", file_slug)
        if header_slug != file_slug:
            violations.append(f"{file.as_posix()}: '{header}' vs '{file.stem}'")
    assert not violations, f"Несоответствие заголовка имени файла: {sorted(violations)}"

