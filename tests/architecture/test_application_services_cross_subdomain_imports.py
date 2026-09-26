"""Enforce forbidden imports between application service subdomains (#9623)."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = PROJECT_ROOT / "src" / "bioetl" / "application" / "services"
OWNERSHIP_CONFIG = (
    PROJECT_ROOT / "configs" / "quality" / "application_services_ownership.yaml"
)
SERVICES_PREFIX = "bioetl.application.services"

EXPECTED_FORBIDDEN_PAIRS = frozenset(
    {
        (
            "bioetl.application.services.dq",
            "bioetl.application.services.control_plane",
        ),
        (
            "bioetl.application.services.dq",
            "bioetl.application.services.execution",
        ),
        (
            "bioetl.application.services.dq",
            "bioetl.application.services.run_reports",
        ),
        (
            "bioetl.application.services.protein",
            "bioetl.application.services.control_plane",
        ),
        (
            "bioetl.application.services.protein",
            "bioetl.application.services.execution",
        ),
        (
            "bioetl.application.services.protein",
            "bioetl.application.services.run_reports",
        ),
    }
)


@dataclass(frozen=True)
class ForbiddenImport:
    """One forbidden directed edge found in a Python source file."""

    path: Path
    line: int
    source_prefix: str
    target_prefix: str
    imported_module: str


def _load_policy(path: Path = OWNERSHIP_CONFIG) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, Mapping), f"Ownership config must be a mapping: {path}"
    return cast(Mapping[str, Any], payload)


def _declared_subdomain_prefixes(policy: Mapping[str, Any]) -> frozenset[str]:
    subdomains = policy.get("subdomains")
    assert isinstance(subdomains, Mapping), "subdomains must be a mapping"
    return frozenset(
        f"{SERVICES_PREFIX}.{name}"
        for name in subdomains
        if isinstance(name, str) and name != "root_legacy"
    )


def _forbidden_pairs(policy: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    configured = policy.get("forbidden_cross_subdomain_imports")
    assert isinstance(configured, Mapping), (
        "forbidden_cross_subdomain_imports must be a mapping"
    )

    pairs: list[tuple[str, str]] = []
    for source_prefix, raw_targets in configured.items():
        assert isinstance(source_prefix, str), "Forbidden source prefix must be text"
        assert isinstance(raw_targets, list), (
            f"Forbidden targets for {source_prefix} must be a list"
        )
        for target_prefix in raw_targets:
            assert isinstance(target_prefix, str), (
                f"Forbidden target prefix for {source_prefix} must be text"
            )
            pairs.append((source_prefix, target_prefix))
    return tuple(pairs)


def _module_name(path: Path, services_root: Path) -> str:
    relative = path.relative_to(services_root).with_suffix("")
    return ".".join((SERVICES_PREFIX, *relative.parts))


def _resolve_import_from(node: ast.ImportFrom, current_module: str) -> Iterable[str]:
    if node.level == 0:
        base = node.module or ""
    else:
        current_parts = current_module.split(".")
        package_parts = current_parts[:-1]
        ascending = node.level - 1
        if ascending > len(package_parts):
            return
        resolved_parts = package_parts[: len(package_parts) - ascending]
        if node.module:
            resolved_parts.extend(node.module.split("."))
        base = ".".join(resolved_parts)

    if base:
        yield base
    for alias in node.names:
        if alias.name != "*":
            yield ".".join(part for part in (base, alias.name) if part)


def _imported_modules(tree: ast.AST, current_module: str) -> Iterable[tuple[int, str]]:
    # ast.walk intentionally includes imports guarded by TYPE_CHECKING.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            for module in _resolve_import_from(node, current_module):
                yield node.lineno, module


def _matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def _find_forbidden_imports(
    services_root: Path,
    pairs: Iterable[tuple[str, str]],
) -> list[ForbiddenImport]:
    configured_pairs = tuple(pairs)
    violations: list[ForbiddenImport] = []
    for path in sorted(services_root.rglob("*.py")):
        current_module = _module_name(path, services_root)
        source_pairs = tuple(
            pair
            for pair in configured_pairs
            if _matches_prefix(current_module, pair[0])
        )
        if not source_pairs:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, imported_module in _imported_modules(tree, current_module):
            for source_prefix, target_prefix in source_pairs:
                if _matches_prefix(imported_module, target_prefix):
                    violations.append(
                        ForbiddenImport(
                            path=path,
                            line=line,
                            source_prefix=source_prefix,
                            target_prefix=target_prefix,
                            imported_module=imported_module,
                        )
                    )
    return violations


def _assert_no_forbidden_imports(
    services_root: Path,
    pairs: Iterable[tuple[str, str]],
) -> None:
    violations = _find_forbidden_imports(services_root, pairs)
    details = "\n".join(
        f"- {violation.path}:{violation.line}: {violation.source_prefix} -> "
        f"{violation.target_prefix} via {violation.imported_module}"
        for violation in violations
    )
    assert violations == [], f"Forbidden cross-subdomain imports detected:\n{details}"


def test_forbidden_pair_contract_is_bounded_unique_and_declared() -> None:
    policy = _load_policy()
    pairs = _forbidden_pairs(policy)
    unique_pairs = frozenset(pairs)

    assert 3 <= len(pairs) <= 10, "Define between 3 and 10 forbidden directed pairs"
    assert len(unique_pairs) == len(pairs), "Forbidden directed pairs must be unique"
    assert unique_pairs == EXPECTED_FORBIDDEN_PAIRS

    declared_prefixes = _declared_subdomain_prefixes(policy)
    used_prefixes = {prefix for pair in pairs for prefix in pair}
    assert used_prefixes <= declared_prefixes, (
        "Forbidden pairs reference undeclared subdomain prefixes: "
        f"{sorted(used_prefixes - declared_prefixes)}"
    )
    for prefix in used_prefixes:
        relative_prefix = prefix.removeprefix(f"{SERVICES_PREFIX}.")
        package_path = SERVICES_ROOT.joinpath(*relative_prefix.split("."))
        assert (package_path / "__init__.py").is_file(), (
            f"Declared subdomain prefix has no package: {prefix}"
        )


def test_real_application_services_tree_has_no_forbidden_imports() -> None:
    _assert_no_forbidden_imports(SERVICES_ROOT, _forbidden_pairs(_load_policy()))


@pytest.mark.parametrize(
    "source",
    [
        "from bioetl.application.services.control_plane import manifest\n",
        (
            "from typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING:\n"
            "    from ..execution import pipeline_runner_service\n"
        ),
    ],
    ids=["absolute", "relative-inside-type-checking"],
)
def test_negative_fixture_rejects_new_forbidden_import(
    tmp_path: Path,
    source: str,
) -> None:
    services_root = tmp_path / "src" / "bioetl" / "application" / "services"
    dq_root = services_root / "dq"
    dq_root.mkdir(parents=True)
    (dq_root / "probe.py").write_text(source, encoding="utf-8")

    with pytest.raises(AssertionError, match="Forbidden cross-subdomain imports"):
        _assert_no_forbidden_imports(services_root, _forbidden_pairs(_load_policy()))
