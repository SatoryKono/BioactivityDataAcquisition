"""Preserve pristine structural Protocol members inside the mutation sandbox.

mutmut 3.8 adds callable implementation helpers to decorated Protocol classes.
Those helpers are mutants, not adapter interface members. This plugin changes
only each captured Protocol's cached structural-member set. Helpers, mutation
dictionaries, executable bodies, assertions and mutation targets stay intact.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any
from pathlib import Path
from types import FunctionType, MethodType

MANIFEST_ENV = "BIOETL_MUTATION_PROTOCOL_MANIFEST"
ROOT_ENV = "BIOETL_MUTATION_SOURCE_ROOT"
HELPER = re.compile(
    r"xǁ(?P<owner>[^ǁ]+)ǁ(?P<method>.+)__mutmut_(?P<id>orig|[1-9][0-9]*)"
)


@dataclass(frozen=True)
class Contract:
    """A captured, source-bound runtime Protocol interface."""

    module: str
    name: str
    source: str
    sha256: str
    members: frozenset[str]
    non_callable: frozenset[str] | None


def _names(value: object) -> frozenset[str]:
    if not isinstance(value, (list, set, frozenset)):
        raise ValueError("Protocol members must be an explicit collection")
    result: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item in result:
            raise ValueError("Invalid or duplicate Protocol member")
        result.add(item)
    return frozenset(result)


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Missing mutation Protocol identity")
    return value


def _protocol(value: object) -> type[object]:
    if not isinstance(value, type):
        raise ValueError("Captured Protocol class is missing")
    if (
        getattr(value, "_is_protocol", False) is not True
        or getattr(value, "_is_runtime_protocol", False) is not True
    ):
        raise ValueError("Captured class is not a runtime-checkable Protocol")
    return value


def _function(value: object) -> FunctionType:
    if isinstance(value, (classmethod, staticmethod, MethodType)):
        value = value.__func__
    if not isinstance(value, FunctionType):
        raise ValueError("Mutation helper is not a function")
    return value


def _verify_helper(protocol: type[object], contract: Contract, name: str) -> None:
    match = HELPER.fullmatch(name)
    if match is None or match["method"] not in contract.members:
        raise ValueError("Unexpected structural Protocol member: " + name)
    owners = [base for base in protocol.__mro__ if base.__name__ == match["owner"]]
    if len(owners) != 1:
        raise ValueError("Mutation helper has an unknown declaring class")
    owner = owners[0]
    _verify_binding(owner, name, match["id"])
    _function(vars(owner).get(match["method"]))


def _verify_binding(owner: type[object], name: str, mutant_id: str) -> None:
    helper = _function(vars(owner).get(name))
    module = sys.modules.get(owner.__module__)
    stem = name.rsplit("_", 1)[0]
    mapping: object = getattr(module, "mutants_" + stem, None)
    key = "_mutmut_orig" if mutant_id == "orig" else name
    if not isinstance(mapping, dict) or _function(mapping.get(key)) is not helper:
        raise ValueError("Protocol helper is not bound to its mutation dictionary")
    if helper.__name__ != name or helper.__module__ != owner.__module__:
        raise ValueError("Mutation helper identity changed")


def normalize_protocol(protocol: type[object], contract: Contract) -> None:
    """Remove only authenticated mutmut helpers from cached membership metadata."""
    _protocol(protocol)
    observed = _names(getattr(protocol, "__protocol_attrs__", None))
    if not contract.members.issubset(observed):
        raise ValueError("A real Protocol member disappeared")
    non_callable = getattr(protocol, "__non_callable_proto_members__", None)
    actual_non_callable = None if non_callable is None else _names(non_callable)
    if actual_non_callable != contract.non_callable:
        raise ValueError("Protocol callable classification changed")
    extras = observed - contract.members
    for name in extras:
        _verify_helper(protocol, contract, name)
    if extras:
        clear: object = getattr(protocol, "_abc_caches_clear", None)
        if not callable(clear):
            raise ValueError("Protocol cache cannot be invalidated")
        attribute = "__protocol_attrs__"
        setattr(protocol, attribute, set(contract.members))
        clear()


def _git(root: Path, argument: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", argument], text=True
    ).strip()


def _source_files(root: Path, target: Path) -> list[Path]:
    resolved = (root / target).resolve()
    resolved.relative_to(root / "src")
    files = sorted(resolved.rglob("*.py")) if resolved.is_dir() else [resolved]
    if not files or any(not path.is_file() or path.is_symlink() for path in files):
        raise ValueError("Mutation target source is missing or redirected")
    return files


def _runtime_names(raw: bytes) -> list[str]:
    return [
        node.name
        for node in ast.parse(raw).body
        if isinstance(node, ast.ClassDef)
        and any(_runtime_decorator(item) for item in node.decorator_list)
    ]


def _runtime_decorator(node: ast.expr) -> bool:
    return (isinstance(node, ast.Name) and node.id == "runtime_checkable") or (
        isinstance(node, ast.Attribute) and node.attr == "runtime_checkable"
    )


def _module_name(root: Path, path: Path) -> str:
    return (
        path.relative_to(root / "src")
        .with_suffix("")
        .as_posix()
        .replace("/", ".")
        .removesuffix(".__init__")
    )


def _source_census(root: Path, target: Path) -> list[list[str]]:
    return sorted(
        [_module_name(root, path), name]
        for path in _source_files(root, target)
        for name in _runtime_names(path.read_bytes())
    )


def _committed_source(root: Path, path: Path) -> bytes:
    raw = path.read_bytes()
    committed = subprocess.check_output(
        ["git", "-C", str(root), "show", "HEAD:" + path.relative_to(root).as_posix()]
    )
    if raw != committed:
        raise ValueError("Pristine Protocol source differs from the checked-out commit")
    return raw


def capture(root: Path, target: Path, output: Path) -> None:
    """Capture exact runtime members before mutmut creates its sandbox."""
    root = root.resolve()
    output = output.resolve()
    if not output.is_relative_to(root / "reports") or output.is_symlink():
        raise ValueError("Protocol manifest must be an owned reports artifact")
    records: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    sys.path.insert(0, str(root / "src"))
    try:
        for path in _source_files(root, target):
            raw = _committed_source(root, path)
            relative = path.relative_to(root).as_posix()
            names = _runtime_names(raw)
            if not names:
                continue
            module_name = _module_name(root, path)
            module = importlib.import_module(module_name)
            if Path(_text(module.__file__)).resolve() != path:
                raise ValueError("Pristine Protocol imported from the wrong source")
            for name in names:
                if (module_name, name) in seen:
                    raise ValueError("Duplicate Protocol identity")
                seen.add((module_name, name))
                protocol = _protocol(getattr(module, name, None))
                members = _names(getattr(protocol, "__protocol_attrs__", None))
                non_callable = getattr(protocol, "__non_callable_proto_members__", None)
                records.append(
                    {
                        "module": module_name,
                        "name": name,
                        "source": relative,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "members": sorted(members),
                        "non_callable": None
                        if non_callable is None
                        else sorted(_names(non_callable)),
                    }
                )
    finally:
        sys.path.pop(0)
    payload = {
        "schema_version": 1,
        "source_root": str(root),
        "target": str(target),
        "source_commit": _git(root, "HEAD"),
        "source_tree": _git(root, "HEAD^{tree}"),
        "expected_identities": [list(identity) for identity in sorted(seen)],
        "contracts": records,
    }
    _write_manifest(output, payload)


def _write_manifest(output: Path, payload: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, delete=False
        ) as stream:
            temporary = stream.name
            stream.write(json.dumps(payload, indent=2) + "\n")
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def pytest_configure(config: object) -> None:
    """Apply source-bound metadata correction only in the explicit CI sandbox."""
    del config
    manifest = Path(_text(os.environ.get(MANIFEST_ENV))).resolve()
    root = Path(_text(os.environ.get(ROOT_ENV))).resolve()
    sandbox = root / "mutants"
    if Path.cwd().resolve() != sandbox or not manifest.is_relative_to(root / "reports"):
        raise ValueError(
            "Mutation Protocol plugin requires the declared sandbox and manifest"
        )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Invalid mutation Protocol manifest")
    if (
        payload.get("source_root") != str(root)
        or payload.get("source_commit") != _git(root, "HEAD")
        or payload.get("source_tree") != _git(root, "HEAD^{tree}")
    ):
        raise ValueError("Mutation Protocol manifest has stale source provenance")
    records = _manifest_records(payload, root)
    for record in records:
        _apply_record(record, root, sandbox)


def _manifest_records(payload: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    records = payload.get("contracts")
    if not isinstance(records, list):
        raise ValueError("Mutation Protocol manifest lacks contracts")
    expected = payload.get("expected_identities")
    identities = [
        [_text(record.get("module")), _text(record.get("name"))]
        for record in records
        if isinstance(record, dict)
    ]
    source_census = _source_census(root, Path(_text(payload.get("target"))))
    if (
        not isinstance(expected, list)
        or sorted(identities) != expected
        or expected != source_census
    ):
        raise ValueError("Mutation Protocol identity census is incomplete")
    if len({tuple(identity) for identity in identities}) != len(identities):
        raise ValueError("Duplicate mutation Protocol identity")
    return records


def _apply_record(record: dict[str, Any], root: Path, sandbox: Path) -> None:
    if not isinstance(record, dict):
        raise ValueError("Invalid Protocol record")
    module_name, name = _text(record.get("module")), _text(record.get("name"))
    source = _text(record.get("source"))
    original = (root / source).resolve()
    original.relative_to(root / "src")
    digest = _text(record.get("sha256"))
    if (
        original.is_symlink()
        or hashlib.sha256(_committed_source(root, original)).hexdigest() != digest
    ):
        raise ValueError("Pristine Protocol source provenance changed")
    module = importlib.import_module(module_name)
    if Path(_text(module.__file__)).resolve() != sandbox / source:
        raise ValueError("Protocol was not imported from the mutation sandbox")
    contract = Contract(
        module_name,
        name,
        source,
        digest,
        _names(record.get("members")),
        None if record.get("non_callable") is None else _names(record["non_callable"]),
    )
    normalize_protocol(_protocol(getattr(module, name, None)), contract)
