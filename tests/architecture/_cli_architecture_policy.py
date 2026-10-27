# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Load the single machine-readable CLI architecture boundary.

Human norm: ``docs/02-architecture/decisions/ADR-005-composition-layer-separation.md``
(import matrix: interfaces must not import infrastructure; indirect imports stay
allowed) and ``docs/00-project/RULES.md`` §1.1.1.
Machine source: ``.importlinter`` contract ``interfaces-no-direct-infrastructure``.

``configs/quality/architecture/composition_ownership_map.yaml`` is the M5
composition ownership map. It is not this policy, and this loader does not
read it. ``cli_architecture_policy.yaml`` is not a second source.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

CLI_ARCHITECTURE_CONTRACT_ID = "interfaces-no-direct-infrastructure"
IMPORT_LINTER_RELATIVE = ".importlinter"
_SECTION_HEADER = f"[importlinter:contract:{CLI_ARCHITECTURE_CONTRACT_ID}]"
_LIST_KEYS = frozenset({"source_modules", "forbidden_modules", "ignore_imports"})

CLI_ARCHITECTURE_CONTRACT_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "contract_id",
        "name",
        "type",
        "source_modules",
        "forbidden_modules",
        "allow_indirect_imports",
        "ignore_imports",
    ],
    "properties": {
        "contract_id": {"const": CLI_ARCHITECTURE_CONTRACT_ID},
        "name": {"type": "string", "minLength": 1},
        "type": {"const": "forbidden"},
        "source_modules": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
            "contains": {"const": "bioetl.interfaces"},
        },
        "forbidden_modules": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
            "contains": {"const": "bioetl.infrastructure"},
        },
        "allow_indirect_imports": {"const": True},
        "ignore_imports": {"type": "array", "maxItems": 0},
    },
}


class CliArchitecturePolicyError(ValueError):
    """The CLI architecture contract is missing or violates its schema."""


def parse_cli_architecture_contract(text: str) -> dict[str, object]:
    """Parse one contract section and reject anything outside the schema.

    Missing section, missing required fields, a direct infrastructure
    allowance, and a non-empty ignore list raise
    ``CliArchitecturePolicyError``. They do not return a default policy.
    """

    fields = _extract_contract_fields(text)
    instance = _normalize_contract(fields)
    _validate_contract(instance)
    return instance


@lru_cache(maxsize=1)
def load_repo_cli_architecture_contract() -> dict[str, object]:
    """Load ``.importlinter`` from the repository root.

    A missing file raises. It is not treated as an empty allowlist.
    """

    path = Path(__file__).resolve().parents[2] / IMPORT_LINTER_RELATIVE
    if not path.is_file():
        raise CliArchitecturePolicyError(
            f"missing required CLI architecture policy source: {IMPORT_LINTER_RELATIVE}"
        )
    return parse_cli_architecture_contract(path.read_text(encoding="utf-8"))


def forbidden_infrastructure_modules() -> tuple[str, ...]:
    """Return infrastructure modules the live contract forbids interfaces to import."""

    modules = load_repo_cli_architecture_contract()["forbidden_modules"]
    if not isinstance(modules, list) or not all(
        isinstance(item, str) for item in modules
    ):
        raise CliArchitecturePolicyError(
            "forbidden_modules must be a list of module names"
        )
    return tuple(modules)


def is_forbidden_infrastructure_import(imported: str) -> bool:
    """Return whether ``imported`` is a direct import of a forbidden module."""

    return any(
        imported == module or imported.startswith(f"{module}.")
        for module in forbidden_infrastructure_modules()
    )


def _extract_contract_fields(text: str) -> dict[str, str | list[str]]:
    lines = text.splitlines()
    header_indexes = [
        index for index, line in enumerate(lines) if line.strip() == _SECTION_HEADER
    ]
    if not header_indexes:
        raise CliArchitecturePolicyError(
            f"missing required contract section: {_SECTION_HEADER}"
        )
    if len(header_indexes) != 1:
        raise CliArchitecturePolicyError(
            f"ambiguous contract section {_SECTION_HEADER}: "
            f"{len(header_indexes)} occurrences"
        )

    fields: dict[str, str | list[str]] = {}
    current_key: str | None = None
    for line in lines[header_indexes[0] + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            break
        if line[:1] in {" ", "\t"}:
            if current_key is None:
                raise CliArchitecturePolicyError(
                    f"invalid contract continuation: {stripped}"
                )
            _append_list_item(fields, current_key, stripped)
            continue
        if "=" not in line:
            raise CliArchitecturePolicyError(f"invalid contract line: {stripped}")
        key, _, raw_value = line.partition("=")
        key = key.strip()
        if not key:
            raise CliArchitecturePolicyError(f"invalid contract line: {stripped}")
        if key in fields:
            raise CliArchitecturePolicyError(f"duplicate contract key: {key}")
        current_key = key
        fields[key] = raw_value.strip()
    return fields


def _append_list_item(
    fields: dict[str, str | list[str]],
    key: str,
    item: str,
) -> None:
    existing = fields[key]
    if isinstance(existing, list):
        existing.append(item)
        return
    if existing == "":
        fields[key] = [item]
        return
    fields[key] = [existing, item]


def _normalize_contract(fields: dict[str, str | list[str]]) -> dict[str, object]:
    instance: dict[str, object] = {"contract_id": CLI_ARCHITECTURE_CONTRACT_ID}
    for key, value in fields.items():
        if key in _LIST_KEYS:
            instance[key] = _as_list(value)
            continue
        if key == "allow_indirect_imports":
            instance[key] = _parse_bool(value)
            continue
        instance[key] = value if isinstance(value, str) else _as_list(value)
    if "ignore_imports" not in instance:
        instance["ignore_imports"] = []
    return instance


def _as_list(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    if value == "":
        return []
    return [value]


def _parse_bool(value: str | list[str]) -> object:
    if isinstance(value, list):
        return value
    if value == "True":
        return True
    if value == "False":
        return False
    return value


def _format_schema_error(error: object) -> str:
    message = getattr(error, "message", str(error))
    schema = getattr(error, "schema", None)
    bits = [str(message)]
    if isinstance(schema, dict):
        const = schema.get("const")
        if isinstance(const, str):
            bits.append(f"required item {const!r}")
        contains = schema.get("contains")
        if isinstance(contains, dict) and isinstance(contains.get("const"), str):
            bits.append(f"required item {contains['const']!r}")
    context = getattr(error, "context", ())
    bits.extend(str(item.message) for item in context)
    return "; ".join(bits)


def _validate_contract(instance: dict[str, object]) -> None:
    try:
        validator = Draft202012Validator(CLI_ARCHITECTURE_CONTRACT_SCHEMA)
    except SchemaError as exc:
        raise CliArchitecturePolicyError(
            f"CLI policy schema is invalid: {exc.message}"
        ) from exc
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda item: list(item.path),
    )
    if not errors:
        return
    details = "; ".join(_format_schema_error(error) for error in errors)
    raise CliArchitecturePolicyError(details)
