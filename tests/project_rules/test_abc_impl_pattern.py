from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any

import pytest
import yaml

ABC_REGISTRY_PATH = Path("src/bioetl/infrastructure/clients/base/abc_registry.yaml")
ABC_IMPLS_PATH = Path("src/bioetl/infrastructure/clients/base/abc_impls.yaml")


def _import_object(dotted_path: str) -> Any:
    module_path, attr = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def test_abc_roles_have_impls() -> None:
    registry = _load_yaml(ABC_REGISTRY_PATH)
    impls = _load_yaml(ABC_IMPLS_PATH)

    missing: list[str] = []
    for role in registry:
        if role not in impls:
            missing.append(role)
    if missing:
        pytest.fail(f"Нет реализаций для ABC: {', '.join(sorted(missing))}")


def test_impls_subclass_their_abcs() -> None:
    registry = _load_yaml(ABC_REGISTRY_PATH)
    impls = _load_yaml(ABC_IMPLS_PATH)

    violations: list[str] = []
    for role, abc_path in registry.items():
        try:
            abc_cls = _import_object(abc_path)
        except (AttributeError, ModuleNotFoundError) as e:
            violations.append(f"Не удалось импортировать {abc_path}: {e}")
            continue
        role_entry = impls.get(role, {})

        for impl_path in (role_entry.get("implementations") or {}).values():
            impl_cls = _import_object(impl_path)
            if not inspect.isclass(impl_cls) or not issubclass(impl_cls, abc_cls):
                violations.append(f"{impl_path} не наследует {abc_path}")

        factory_path = role_entry.get("default_factory")
        if factory_path:
            factory_obj = _import_object(factory_path)
            if not callable(factory_obj):
                violations.append(f"Фабрика {factory_path} не является callable")
            else:
                sig = inspect.signature(factory_obj)
                ret = sig.return_annotation
                if ret is not inspect.Signature.empty and inspect.isclass(ret):
                    try:
                        if not issubclass(ret, abc_cls):
                            violations.append(
                                f"Фабрика {factory_path} аннотирована типом {ret} "
                                f"не совместимым с {abc_path}"
                            )
                    except TypeError:
                        # ignore non-class annotations (e.g., typing.Any)
                        pass

    if violations:
        pytest.fail("\n".join(sorted(set(violations))))
