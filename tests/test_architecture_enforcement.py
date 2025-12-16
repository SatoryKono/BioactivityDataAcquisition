"""Строгие архитектурные тесты с AST-анализом.

Автоматически проверяют соблюдение правил чистой архитектуры:
- Domain слой не зависит от внешних фреймворков
- Application не импортирует конкретные реализации Infrastructure
- Запрет небезопасных функций (print, eval, exec)
- Проверка всех импортов на соответствие архитектурным границам

Тесты используют AST (Abstract Syntax Tree) для анализа импортов
и обеспечивают "железный занавес" между слоями.
"""

import ast
from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# Архитектурные правила
# =============================================================================

# Внешние фреймворки, запрещенные в Domain
FORBIDDEN_DOMAIN_FRAMEWORKS = {
    "prefect",
    "boto3",
    "click",
    "fastapi",
    "flask",
    "django",
    "sqlalchemy",
    "httpx",
    "requests",
    "aiohttp",
    "redis",
    "polars",
    "deltalake",
    "psycopg2",
    "pymongo",
}

# Разрешенные импорты в Domain
ALLOWED_DOMAIN_IMPORTS = {
    # Стандартная библиотека
    "abc",
    "collections",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "functools",
    "itertools",
    "pathlib",
    "typing",
    "uuid",
    "warnings",
    "__future__",
    # Validation (только для Value Objects)
    "pydantic",
}

# Конкретные реализации Infrastructure, запрещенные в Application
FORBIDDEN_APPLICATION_INFRASTRUCTURE = {
    "bioetl.infrastructure.adapters.chembl",
    "bioetl.infrastructure.adapters.pubchem",
    "bioetl.infrastructure.checkpoint.s3_checkpoint",
    "bioetl.infrastructure.locking.redis_lock",
    "bioetl.infrastructure.storage.s3_storage",
    "bioetl.infrastructure.quarantine.s3_quarantine",
}

# Небезопасные функции
UNSAFE_BUILTINS = {"eval", "exec", "compile", "__import__"}

# Функции для вывода (должен использоваться только logger)
PRINT_FUNCTIONS = {"print", "pprint"}


# =============================================================================
# AST Visitor для анализа импортов
# =============================================================================


class ImportVisitor(ast.NodeVisitor):
    """Собирает все импорты из AST."""

    def __init__(self):
        self.imports: list[dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Обрабатывает: import foo, import bar as baz."""
        for alias in node.names:
            self.imports.append(
                {
                    "type": "import",
                    "module": alias.name,
                    "lineno": node.lineno,
                    "col_offset": node.col_offset,
                }
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Обрабатывает: from foo import bar."""
        if node.module:
            for alias in node.names:
                self.imports.append(
                    {
                        "type": "from",
                        "module": node.module,
                        "name": alias.name,
                        "lineno": node.lineno,
                        "col_offset": node.col_offset,
                    }
                )
        self.generic_visit(node)


class FunctionCallVisitor(ast.NodeVisitor):
    """Собирает все вызовы функций."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Обрабатывает вызовы функций."""
        func_name = None

        # Простой вызов: print(), eval()
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        # Атрибут: pprint.pprint()
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name:
            self.calls.append(
                {
                    "name": func_name,
                    "lineno": node.lineno,
                    "col_offset": node.col_offset,
                }
            )

        self.generic_visit(node)


# =============================================================================
# Вспомогательные функции
# =============================================================================


def get_top_level_module(module_path: str) -> str:
    """Извлекает верхний уровень модуля: 'foo.bar.baz' -> 'foo'."""
    return module_path.split(".")[0]


def analyze_python_file(file_path: Path) -> tuple[list, list]:
    """Анализирует Python файл и возвращает импорты и вызовы функций.

    Returns:
        (imports, function_calls)
    """
    try:
        with file_path.open(encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        import_visitor = ImportVisitor()
        import_visitor.visit(tree)

        call_visitor = FunctionCallVisitor()
        call_visitor.visit(tree)

        return import_visitor.imports, call_visitor.calls

    except SyntaxError:
        # Пропускаем файлы с синтаксическими ошибками
        return [], []


def format_violation(file_path: Path, lineno: int, message: str, src_dir: Path) -> str:
    """Форматирует сообщение о нарушении."""
    relative_path = file_path.relative_to(src_dir)
    return f"{relative_path}:{lineno}: {message}"


# =============================================================================
# REQ-ARCH-DOMAIN-001: Domain слой — чистота
# =============================================================================


def test_domain_no_external_frameworks(src_dir: Path):
    """Domain слой не должен импортировать внешние фреймворки.

    Domain — самый чистый слой. Разрешены только:
    - Стандартная библиотека Python
    - Pydantic (для Value Objects)

    Запрещены: prefect, boto3, click, fastapi, httpx, redis, polars и т.д.
    """
    domain_path = src_dir / "bioetl" / "domain"
    violations = []

    for py_file in domain_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        imports, _ = analyze_python_file(py_file)

        for imp in imports:
            module = imp["module"]
            top_level = get_top_level_module(module)

            # Проверяем запрещенные фреймворки
            if top_level in FORBIDDEN_DOMAIN_FRAMEWORKS:
                violation = format_violation(
                    py_file,
                    imp["lineno"],
                    f"Forbidden framework import '{module}' in Domain layer",
                    src_dir,
                )
                violations.append(violation)

    assert not violations, (
        "Domain layer must not import external frameworks.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
        "Domain should only use:\n"
        "  - Standard library\n"
        "  - Pydantic (for Value Objects)\n"
        "  - Domain-internal modules"
    )


def test_domain_no_infrastructure_imports(src_dir: Path):
    """Domain не должен импортировать Infrastructure или Application слои."""
    domain_path = src_dir / "bioetl" / "domain"
    violations = []

    forbidden_layers = {
        "bioetl.infrastructure",
        "bioetl.application",
    }

    for py_file in domain_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        imports, _ = analyze_python_file(py_file)

        for imp in imports:
            module = imp["module"]

            for forbidden in forbidden_layers:
                if module.startswith(forbidden):
                    violation = format_violation(
                        py_file,
                        imp["lineno"],
                        f"Domain imports from {forbidden} ('{module}')",
                        src_dir,
                    )
                    violations.append(violation)

    assert not violations, (
        "Domain layer must not import from Infrastructure or Application.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
        "Domain should only depend on itself and standard library."
    )


def test_domain_only_allowed_imports(src_dir: Path):
    """Domain должен импортировать только разрешенные модули.

    Это белый список: только стандартная библиотека + pydantic.
    """
    domain_path = src_dir / "bioetl" / "domain"
    violations = []

    for py_file in domain_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        imports, _ = analyze_python_file(py_file)

        for imp in imports:
            module = imp["module"]
            top_level = get_top_level_module(module)

            # Разрешаем импорты из самого domain
            if module.startswith("bioetl.domain"):
                continue

            # Проверяем белый список
            if top_level not in ALLOWED_DOMAIN_IMPORTS:
                violation = format_violation(
                    py_file,
                    imp["lineno"],
                    f"Import '{module}' not in allowed list for Domain",
                    src_dir,
                )
                violations.append(violation)

    # Это warning-тест, но можем сделать строгим
    if violations:
        pytest.fail(
            "Domain layer imports modules not in allowed list.\n"
            "Violations found:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\n"
            f"Allowed imports: {sorted(ALLOWED_DOMAIN_IMPORTS)}\n"
            "If you need to add a module, update ALLOWED_DOMAIN_IMPORTS in test."
        )


# =============================================================================
# REQ-ARCH-APP-001: Application слой — интерфейсы, не реализации
# =============================================================================


def test_application_no_concrete_infrastructure_imports(src_dir: Path):
    """Application не должен импортировать конкретные реализации Infrastructure.

    Разрешены:
    - Domain (ports, types, exceptions)
    - Infrastructure.factories (для создания адаптеров)
    - Infrastructure.observability (логирование)

    Запрещены:
    - Конкретные адаптеры (chembl, pubchem, s3_checkpoint, redis_lock)
    """
    application_path = src_dir / "bioetl" / "application"
    violations = []

    for py_file in application_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        imports, _ = analyze_python_file(py_file)

        for imp in imports:
            module = imp["module"]

            # Проверяем запрещенные конкретные реализации
            for forbidden in FORBIDDEN_APPLICATION_INFRASTRUCTURE:
                if module.startswith(forbidden):
                    violation = format_violation(
                        py_file,
                        imp["lineno"],
                        f"Application imports concrete infrastructure ('{module}')",
                        src_dir,
                    )
                    violations.append(violation)

    assert not violations, (
        "Application layer must not import concrete Infrastructure implementations.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
        "Application should only depend on:\n"
        "  - Domain ports (bioetl.domain.ports)\n"
        "  - Infrastructure factories (bioetl.infrastructure.factories)\n"
        "  - Infrastructure observability (bioetl.infrastructure.observability)"
    )


def test_application_no_direct_adapter_imports(src_dir: Path):
    """Application не должен импортировать из infrastructure.adapters напрямую.

    Допустимые исключения:
    - TYPE_CHECKING блоки (для type hints)
    - Factories
    """
    application_path = src_dir / "bioetl" / "application"
    violations = []

    for py_file in application_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        try:
            with py_file.open(encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(py_file))

            # Проверяем импорты вне TYPE_CHECKING
            in_type_checking = False

            for node in ast.walk(tree):
                # Определяем блок TYPE_CHECKING
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                        in_type_checking = True

                if isinstance(node, (ast.Import, ast.ImportFrom)) and not in_type_checking:
                    if isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        if module.startswith("bioetl.infrastructure.adapters"):
                            violation = format_violation(
                                py_file,
                                node.lineno,
                                f"Direct import from infrastructure.adapters: '{module}'",
                                src_dir,
                            )
                            violations.append(violation)

        except SyntaxError:
            continue

    assert not violations, (
        "Application must not import directly from infrastructure.adapters.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
        "Use factories or dependency injection instead."
    )


# =============================================================================
# REQ-SECURITY-001: Запрет небезопасных функций
# =============================================================================


def test_no_print_statements(src_dir: Path):
    """В коде не должно быть print() — только logger.

    Исключения:
    - cli.py (может использовать print для вывода в консоль)
    - __main__.py
    """
    violations = []
    allowed_files = {"cli.py", "__main__.py"}

    for py_file in (src_dir / "bioetl").rglob("*.py"):
        if py_file.name.startswith("__pycache__"):
            continue

        # Разрешаем print в CLI и __main__
        if py_file.name in allowed_files:
            continue

        _, calls = analyze_python_file(py_file)

        for call in calls:
            if call["name"] in PRINT_FUNCTIONS:
                violation = format_violation(
                    py_file,
                    call["lineno"],
                    f"Use of '{call['name']}()' instead of logger",
                    src_dir,
                )
                violations.append(violation)

    assert not violations, (
        "Code must not use print() — use logger instead.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
        "Exceptions: cli.py, __main__.py"
    )


def test_no_unsafe_builtins(src_dir: Path):
    """В коде не должно быть eval(), exec(), compile()."""
    violations = []

    for py_file in (src_dir / "bioetl").rglob("*.py"):
        if py_file.name.startswith("__pycache__"):
            continue

        _, calls = analyze_python_file(py_file)

        for call in calls:
            if call["name"] in UNSAFE_BUILTINS:
                violation = format_violation(
                    py_file,
                    call["lineno"],
                    f"Unsafe builtin '{call['name']}()' detected",
                    src_dir,
                )
                violations.append(violation)

    assert not violations, (
        "Code must not use unsafe builtins: eval, exec, compile.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations)
    )


# =============================================================================
# REQ-ARCH-INFRA-001: Infrastructure может зависеть от Domain, но не от Application
# =============================================================================


def test_infrastructure_no_application_imports(src_dir: Path):
    """Infrastructure не должен импортировать Application.

    Infrastructure может зависеть только от Domain портов.
    """
    infrastructure_path = src_dir / "bioetl" / "infrastructure"
    violations = []

    for py_file in infrastructure_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        imports, _ = analyze_python_file(py_file)

        for imp in imports:
            module = imp["module"]

            if module.startswith("bioetl.application"):
                violation = format_violation(
                    py_file,
                    imp["lineno"],
                    f"Infrastructure imports Application layer ('{module}')",
                    src_dir,
                )
                violations.append(violation)

    assert not violations, (
        "Infrastructure must not import from Application layer.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
        "Infrastructure should only depend on Domain (ports, types, exceptions)."
    )


# =============================================================================
# REQ-ARCH-IMPORT-001: Проверка .importlinter контрактов
# =============================================================================


def test_importlinter_enforces_architecture(project_root: Path):
    """Import-linter должен проверять архитектурные границы в CI/CD.

    Этот тест проверяет, что import-linter настроен правильно.
    """
    importlinter_config = project_root / ".importlinter"

    if not importlinter_config.exists():
        pytest.skip(".importlinter config not found")

    with importlinter_config.open(encoding="utf-8") as f:
        config_content = f.read()

    # Проверяем наличие критичных контрактов
    required_contracts = [
        "domain-independence",
        "domain-pure",
        "application-no-infrastructure-imports",
        "infrastructure-no-application",
    ]

    missing_contracts = []
    for contract in required_contracts:
        if f"[importlinter:contract:{contract}]" not in config_content:
            missing_contracts.append(contract)

    assert not missing_contracts, (
        f"Missing critical import-linter contracts: {missing_contracts}\n"
        "Add these contracts to .importlinter configuration."
    )


# =============================================================================
# Pytest fixtures
# =============================================================================


@pytest.fixture
def src_dir() -> Path:
    """Путь к директории src/."""
    return Path(__file__).parent.parent / "src"


@pytest.fixture
def project_root() -> Path:
    """Корень проекта."""
    return Path(__file__).parent.parent
