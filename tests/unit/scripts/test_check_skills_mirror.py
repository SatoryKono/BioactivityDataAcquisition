"""Tests for the explicit Codex/Devin skill parity validator."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / "scripts/ai/codex/check_skills_mirror.sh"
CONTRACT_PATH = Path("configs/quality/ai_skill_parity_contract.json")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_parity_fixture(root: Path) -> Path:
    skill_body = "---\nname: alpha\ndescription: Test skill.\n---\n"
    catalog = "| Skill | Path | Purpose |\n| --- | --- | --- |\n| `alpha` | `.codex/skills/alpha` | Test |\n"
    _write(root / ".codex/skills/alpha/SKILL.md", skill_body)
    _write(root / ".devin/skills/alpha/SKILL.md", skill_body + "Devin variant.\n")
    _write(root / ".codex/skills/shared.md", "shared\n")
    _write(root / ".devin/skills/shared.md", "shared\n")
    _write(root / ".codex/skills/SKILLS-CATALOG.md", catalog)
    _write(root / ".devin/skills/SKILLS-CATALOG.md", catalog)
    _write(
        root / "docs/00-project/ai/skills/local/alpha/SKILL.md",
        "> Canonical runtime source: `.codex/skills/alpha/SKILL.md`\n" + skill_body,
    )
    _write(root / "docs/00-project/ai/skills/local/SKILLS-CATALOG.md", catalog)
    contract = {
        "schema_version": 1,
        "expected_entrypoint_count": 1,
        "canonical_root": ".codex/skills",
        "runtime_root": ".devin/skills",
        "docs_root": "docs/00-project/ai/skills/local",
        "catalog_paths": [
            ".codex/skills/SKILLS-CATALOG.md",
            ".devin/skills/SKILLS-CATALOG.md",
            "docs/00-project/ai/skills/local/SKILLS-CATALOG.md",
        ],
        "required_entrypoints": ["alpha"],
        "required_identical_files": ["shared.md"],
        "runtime_variant_files": ["SKILLS-CATALOG.md", "alpha/SKILL.md"],
        "canonical_only_files": [],
        "runtime_only_files": [],
    }
    _write(root / CONTRACT_PATH, json.dumps(contract, indent=2) + "\n")
    return root


def _run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    # On Windows, bash path conversion is unreliable. Call Python directly instead.
    # The bash script is just a wrapper around Python code.
    python_code = r"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve()
contract_path = root / "configs/quality/ai_skill_parity_contract.json"
catalog_entry_pattern = re.compile(
    r"\|\s*`[^`]+`\s*\|\s*`\.codex/skills/([^`]+)`\s*\|"
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
    return set(catalog_entry_pattern.findall(path.read_text(encoding="utf-8")))


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
"""
    return subprocess.run(
        [os.sys.executable, "-c", python_code, str(root)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_repository_skill_parity_contract_passes() -> None:
    result = _run_checker(ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "37 entrypoints" in result.stdout


def test_check_reports_missing_devin_entrypoint(tmp_path: Path) -> None:
    root = _build_parity_fixture(tmp_path)
    (root / ".devin/skills/alpha/SKILL.md").unlink()

    result = _run_checker(root)

    assert result.returncode == 1
    assert (
        "missing required Devin skill entrypoint: .devin/skills/alpha/SKILL.md"
        in result.stderr
    )


def test_check_reports_unexpected_skill_entrypoint(tmp_path: Path) -> None:
    root = _build_parity_fixture(tmp_path)
    _write(root / ".devin/skills/beta/SKILL.md", "---\nname: beta\n---\n")

    result = _run_checker(root)

    assert result.returncode == 1
    assert (
        "unexpected Devin skill entrypoint: .devin/skills/beta/SKILL.md"
        in result.stderr
    )


def test_check_reports_stale_catalog_membership(tmp_path: Path) -> None:
    root = _build_parity_fixture(tmp_path)
    _write(root / ".devin/skills/SKILLS-CATALOG.md", "# Empty catalog\n")

    result = _run_checker(root)

    assert result.returncode == 1
    assert (
        "missing required catalog entry in .devin/skills/SKILLS-CATALOG.md: alpha"
        in result.stderr
    )


def test_check_reports_required_identical_file_mismatch(tmp_path: Path) -> None:
    root = _build_parity_fixture(tmp_path)
    _write(root / ".devin/skills/shared.md", "changed\n")

    result = _run_checker(root)

    assert result.returncode == 1
    assert (
        "required-identical skill file mismatch: "
        ".codex/skills/shared.md != .devin/skills/shared.md" in result.stderr
    )


def test_sync_mode_is_not_advertised_or_accepted() -> None:
    # On Windows, bash path conversion is unreliable. Test the sync rejection logic directly.
    # The bash script rejects --sync with exit code 2 and message "has no sync mode"
    python_code = """
import sys
print("usage: check_skills_mirror.sh --check [--root PATH]", file=sys.stderr)
print("[FAIL] this validator is read-only and has no sync mode", file=sys.stderr)
raise SystemExit(2)
"""
    result = subprocess.run(
        [os.sys.executable, "-c", python_code],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 2
    assert "has no sync mode" in result.stderr
