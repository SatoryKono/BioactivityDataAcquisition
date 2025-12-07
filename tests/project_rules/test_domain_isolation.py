from __future__ import annotations

import pytest

from tests.architecture.test_layer_dependencies import _collect_imports
from tests.project_rules.conftest import iter_python_files

BANNED_THIRD_PARTY = {
    "requests",
    "httpx",
    "aiohttp",
    "pymongo",
    "sqlalchemy",
    "psycopg2",
    "boto3",
}


def _assert_no_violations(violations: list[str]) -> None:
    if violations:
        pytest.fail("\n".join(sorted(set(violations))))


def test_domain_has_no_external_side_effects(bioetl_root) -> None:
    violations: list[str] = []
    domain_root = bioetl_root / "domain"

    for file_path in iter_python_files(domain_root):
        for reference in _collect_imports(file_path):
            module = reference.module

            if module.startswith(("bioetl.infrastructure", "bioetl.application", "bioetl.interfaces")):
                violations.append(
                    f"{file_path.as_posix()}:{reference.lineno}: "
                    f"domain must not depend on outer layers ({module})"
                )

            root_module = module.split(".")[0]
            if root_module in BANNED_THIRD_PARTY:
                violations.append(
                    f"{file_path.as_posix()}:{reference.lineno}: "
                    f"domain must not import I/O or network libs ({module})"
                )

    _assert_no_violations(violations)

