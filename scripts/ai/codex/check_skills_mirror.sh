#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

if [[ "${1:-}" != "--check" ]]; then
  echo "usage: check_skills_mirror.sh --check [--root PATH]" >&2
  echo "[FAIL] this validator is read-only and has no sync mode" >&2
  exit 2
fi
shift

validation_root="$repo_root"
while (($#)); do
  case "$1" in
    --root)
      if (($# < 2)); then
        echo "[FAIL] --root requires a path" >&2
        exit 2
      fi
      validation_root="$2"
      shift 2
      ;;
    *)
      echo "[FAIL] unsupported argument: $1" >&2
      exit 2
      ;;
  esac
done

python_bin="${PYTHON:-python3}"
exec "$python_bin" - "$validation_root" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve()
contract_path = root / "configs/quality/ai_skill_parity_contract.json"
# Support both table format (| `skill` | `.codex/skills/path` |) and list format (- [skill](path))
# Table format has multiple columns, so we match the path column specifically
catalog_entry_pattern = re.compile(
    r"(?:\|\s*`[^`]+`\s*\|\s*`\.codex/skills/([^`]+)`\s*\|)"
    r"|(?:- \[([^\]]+)\]\([^)]+/SKILL\.md\))"
)


def relative_files(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }


def entrypoints(files: set[str]) -> set[str]:
    suffix = "/SKILL.md"
    return {path[: -len(suffix)] for path in files if path.endswith(suffix)}


def string_set(contract: dict[str, object], name: str) -> set[str]:
    value = contract.get(name)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"contract field must be a list of strings: {name}")
    return set(value)


def compare_named_set(
    expected: set[str], actual: set[str], label: str, path_for
) -> list[str]:
    errors = [
        f"missing required {label}: {path_for(item)}" for item in sorted(expected - actual)
    ]
    errors.extend(
        f"unexpected {label}: {path_for(item)}" for item in sorted(actual - expected)
    )
    return errors


def catalog_entrypoints(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    # Extract from table format (group 1) and list format (group 2)
    table_matches = set(match.group(1) for match in catalog_entry_pattern.finditer(text) if match.group(1))
    list_matches = set(match.group(2) for match in catalog_entry_pattern.finditer(text) if match.group(2))
    return table_matches | list_matches


def validate() -> tuple[list[str], int]:
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"parity contract must be a JSON object: {contract_path}")
    if payload.get("schema_version") != 1:
        return [f"unsupported parity contract schema_version: {payload.get('schema_version')!r}"], 0

    canonical_root = root / str(payload["canonical_root"])
    runtime_root = root / str(payload["runtime_root"])
    docs_root = root / str(payload["docs_root"])
    required_entrypoints = string_set(payload, "required_entrypoints")
    required_identical = string_set(payload, "required_identical_files")
    runtime_variants = string_set(payload, "runtime_variant_files")
    canonical_only = string_set(payload, "canonical_only_files")
    runtime_only = string_set(payload, "runtime_only_files")
    expected_count = payload.get("expected_entrypoint_count")
    errors: list[str] = []
    if expected_count != len(required_entrypoints):
        errors.append(
            "contract expected_entrypoint_count does not match required_entrypoints: "
            f"{expected_count!r} != {len(required_entrypoints)}"
        )

    canonical_files = relative_files(canonical_root)
    runtime_files = relative_files(runtime_root)
    docs_files = relative_files(docs_root)
    errors.extend(
        compare_named_set(
            required_entrypoints,
            entrypoints(canonical_files),
            "Codex skill entrypoint",
            lambda item: f"{payload['canonical_root']}/{item}/SKILL.md",
        )
    )
    errors.extend(
        compare_named_set(
            required_entrypoints,
            entrypoints(runtime_files),
            "Devin skill entrypoint",
            lambda item: f"{payload['runtime_root']}/{item}/SKILL.md",
        )
    )
    errors.extend(
        compare_named_set(
            required_entrypoints,
            entrypoints(docs_files),
            "published skill entrypoint",
            lambda item: f"{payload['docs_root']}/{item}/SKILL.md",
        )
    )

    actual_common = canonical_files & runtime_files
    errors.extend(
        compare_named_set(
            required_identical | runtime_variants,
            actual_common,
            "classified common skill file",
            lambda item: item,
        )
    )
    errors.extend(
        compare_named_set(
            canonical_only,
            canonical_files - runtime_files,
            "classified Codex-only skill file",
            lambda item: f"{payload['canonical_root']}/{item}",
        )
    )
    errors.extend(
        compare_named_set(
            runtime_only,
            runtime_files - canonical_files,
            "classified Devin-only skill file",
            lambda item: f"{payload['runtime_root']}/{item}",
        )
    )

    for relative_path in sorted(required_identical & actual_common):
        if (canonical_root / relative_path).read_bytes() != (
            runtime_root / relative_path
        ).read_bytes():
            errors.append(
                "required-identical skill file mismatch: "
                f"{payload['canonical_root']}/{relative_path} != "
                f"{payload['runtime_root']}/{relative_path}"
            )

    for skill in sorted(required_entrypoints & entrypoints(docs_files)):
        expected_header = (
            f"> Canonical runtime source: `.codex/skills/{skill}/SKILL.md`"
        )
        if expected_header not in (docs_root / skill / "SKILL.md").read_text(
            encoding="utf-8"
        ):
            errors.append(
                "published skill mirror missing canonical header: "
                f"{payload['docs_root']}/{skill}/SKILL.md"
            )

    catalog_paths = payload.get("catalog_paths")
    if not isinstance(catalog_paths, list) or not all(
        isinstance(item, str) for item in catalog_paths
    ):
        raise ValueError("contract field must be a list of strings: catalog_paths")
    for relative_path in catalog_paths:
        path = root / relative_path
        if not path.is_file():
            errors.append(f"missing skill catalog: {relative_path}")
            continue
        errors.extend(
            compare_named_set(
                required_entrypoints,
                catalog_entrypoints(path),
                f"catalog entry in {relative_path}",
                lambda item: item,
            )
        )

    return sorted(set(errors)), int(expected_count)


try:
    violations, count = validate()
except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
    print(f"[FAIL] unable to validate skill parity: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

if violations:
    for violation in violations:
        print(f"[FAIL] {violation}", file=sys.stderr)
    raise SystemExit(1)

print(f"[OK] skill parity contract passed: {count} entrypoints")
PY
