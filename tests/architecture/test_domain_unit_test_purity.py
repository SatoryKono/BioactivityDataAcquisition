"""Architecture guards for domain purity and domain-unit test purity."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest


DISALLOWED_IMPORT_PREFIXES = (
    "bioetl.application",
    "bioetl.infrastructure",
    "bioetl.composition",
)

DISALLOWED_RUNTIME_SEAMS: tuple[tuple[str, str], ...] = (
    ("open", "filesystem I/O via open()"),
    ("path.open", "filesystem I/O via Path.open()"),
    ("read_text", "filesystem I/O via Path.read_text()"),
    ("write_text", "filesystem I/O via Path.write_text()"),
    ("glob", "filesystem discovery via Path.glob()"),
    ("rglob", "filesystem discovery via Path.rglob()"),
    ("exists", "filesystem discovery via Path.exists()"),
    ("mkdir", "filesystem mutation via Path.mkdir()"),
    ("unlink", "filesystem mutation via Path.unlink()"),
    ("touch", "filesystem mutation via Path.touch()"),
    ("yaml", "direct YAML parsing/serialization"),
    ("datetime.now", "wall-clock time via datetime.now()"),
    ("datetime.utcnow", "wall-clock time via datetime.utcnow()"),
    ("time.time", "wall-clock time via time.time()"),
)

_SEAM_MESSAGES = dict(DISALLOWED_RUNTIME_SEAMS)

_ALLOWED_RUNTIME_SEAMS: dict[tuple[str, str], str] = {
    (
        "src/bioetl/domain/context.py",
        "datetime.now",
    ): "canonical PipelineContext time-source seam; tracked by ADR-014 guard",
    (
        "src/bioetl/domain/control_plane/config_source_hashing.py",
        "yaml",
    ): "pure canonical-YAML parsing from supplied bytes, not filesystem persistence",
    (
        "tests/unit/domain/composite/test_composite_config_facade.py",
        "read_text",
    ): "config facade contract fixture reads canonical composite YAML",
    (
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
        "read_text",
    ): "hash-policy golden fixture contract reads canonical policy YAML/JSON",
    (
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
        "write_text",
    ): "hash-policy golden fixture contract writes isolated tmp_path output",
    (
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
        "exists",
    ): "hash-policy golden fixture contract verifies expected fixture paths",
    (
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
        "mkdir",
    ): "hash-policy golden fixture contract creates isolated tmp_path output dir",
    (
        "tests/unit/domain/hash_policy/test_hash_policy_stability.py",
        "yaml",
    ): "hash-policy golden fixture contract parses canonical policy YAML",
    (
        "tests/unit/domain/models/test_metadata_output.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/normalization/profiles/test_additional_profiles.py",
        "read_text",
    ): "normalization profile fixture contract reads observed-value YAML",
    (
        "tests/unit/domain/normalization/profiles/test_additional_profiles.py",
        "yaml",
    ): "normalization profile fixture contract parses observed-value YAML",
    (
        "tests/unit/domain/normalization/profiles/test_chembl_enum_externalization_ratchet.py",
        "read_text",
    ): "AST ratchet reads domain source text as test input",
    (
        "tests/unit/domain/normalization/profiles/test_chembl_enum_externalization_ratchet.py",
        "glob",
    ): "AST ratchet enumerates profile source files as test input",
    (
        "tests/unit/domain/normalization/profiles/test_chembl_policy_registry.py",
        "read_text",
    ): "policy registry contract reads canonical vocab YAML",
    (
        "tests/unit/domain/normalization/profiles/test_chembl_policy_registry.py",
        "yaml",
    ): "policy registry contract parses canonical vocab YAML",
    (
        "tests/unit/domain/normalization/test_join_keys.py",
        "glob",
    ): "join-key contract enumerates checked-in composite YAML configs",
    (
        "tests/unit/domain/normalization/test_join_keys.py",
        "read_text",
    ): "join-key contract reads checked-in composite YAML configs",
    (
        "tests/unit/domain/normalization/test_join_keys.py",
        "yaml",
    ): "join-key contract parses checked-in composite YAML configs",
    (
        "tests/unit/domain/normalization/test_unit_dq_parity.py",
        "read_text",
    ): "normalization/DQ parity contract reads canonical entity config",
    (
        "tests/unit/domain/normalization/test_unit_dq_parity.py",
        "yaml",
    ): "normalization/DQ parity contract parses canonical entity config",
    (
        "tests/unit/domain/ports/test_noop_audit.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/ports/test_port_dtos.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/ports/test_protocol_stubs.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/schemas/chembl/test_schemas.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/schemas/common/test_publication_base.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/schemas/openalex/test_publication_schema.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/schemas/test_constants_yaml.py",
        "exists",
    ): "schema constants sync contract verifies canonical enum YAML presence",
    (
        "tests/unit/domain/schemas/test_constants_yaml.py",
        "path.open",
    ): "schema constants sync contract reads canonical enum YAML",
    (
        "tests/unit/domain/schemas/test_constants_yaml.py",
        "yaml",
    ): "schema constants sync contract parses canonical enum YAML",
    (
        "tests/unit/domain/schemas/test_year_validation.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/services/test_merged_metadata_explainability.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/test_contract_identity.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/test_entities.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/test_pipeline_context.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/value_objects/test_dq_result.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
    (
        "tests/unit/domain/value_objects/test_run_context.py",
        "datetime.now",
    ): "legacy deterministic-test cleanup backlog covered by global test-time ratchet",
}


@dataclass(frozen=True)
class RuntimeSeamViolation:
    """Structured purity violation for precise allowlist matching."""

    file_path: Path
    line: int
    seam: str
    reason: str

    def render(self) -> str:
        return f"{self.file_path}:{self.line}: uses {self.reason}"


def _collect_disallowed_imports(file_path: Path) -> list[str]:
    violations: list[str] = []
    content = file_path.read_text(encoding="utf-8")

    for prefix in DISALLOWED_IMPORT_PREFIXES:
        pattern = re.compile(
            rf"^\s*(?:from|import)\s+{re.escape(prefix)}\b", re.MULTILINE
        )
        if pattern.search(content):
            violations.append(f"{file_path}: imports {prefix}")

    return violations


def _attribute_path(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _attribute_path(node.value)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _collect_disallowed_runtime_seams(file_path: Path) -> list[RuntimeSeamViolation]:
    violations: list[RuntimeSeamViolation] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "yaml" or alias.name.startswith("yaml."):
                    violations.append(
                        RuntimeSeamViolation(
                            file_path=file_path,
                            line=node.lineno,
                            seam="yaml",
                            reason=_SEAM_MESSAGES["yaml"],
                        )
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "yaml" or node.module.startswith("yaml."):
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam="yaml",
                        reason=_SEAM_MESSAGES["yaml"],
                    )
                )
        if isinstance(node, ast.Call):
            target = _attribute_path(node.func)
            attr_name = node.func.attr if isinstance(node.func, ast.Attribute) else None
            if target == "open":
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam="open",
                        reason=_SEAM_MESSAGES["open"],
                    )
                )
            elif target == "datetime.now":
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam="datetime.now",
                        reason=_SEAM_MESSAGES["datetime.now"],
                    )
                )
            elif target == "datetime.utcnow":
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam="datetime.utcnow",
                        reason=_SEAM_MESSAGES["datetime.utcnow"],
                    )
                )
            elif target == "time.time":
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam="time.time",
                        reason=_SEAM_MESSAGES["time.time"],
                    )
                )
            elif attr_name == "open":
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam="path.open",
                        reason=_SEAM_MESSAGES["path.open"],
                    )
                )
            elif attr_name in {
                "read_text",
                "write_text",
                "glob",
                "rglob",
                "exists",
                "mkdir",
                "unlink",
                "touch",
            }:
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam=attr_name,
                        reason=_SEAM_MESSAGES[attr_name],
                    )
                )
            elif target is not None and target.startswith("yaml."):
                violations.append(
                    RuntimeSeamViolation(
                        file_path=file_path,
                        line=node.lineno,
                        seam="yaml",
                        reason=_SEAM_MESSAGES["yaml"],
                    )
                )

    return violations


def _relative_repo_path(project_root: Path, file_path: Path) -> str:
    return file_path.relative_to(project_root).as_posix()


def _filter_allowed_runtime_seams(
    *,
    project_root: Path,
    violations: list[RuntimeSeamViolation],
) -> list[RuntimeSeamViolation]:
    return [
        violation
        for violation in violations
        if (
            _relative_repo_path(project_root, violation.file_path),
            violation.seam,
        )
        not in _ALLOWED_RUNTIME_SEAMS
    ]


@pytest.mark.parametrize(
    ("root_path", "surface_label"),
    (
        ("src/bioetl/domain", "Production domain modules"),
        ("tests/unit/domain", "Domain unit tests"),
    ),
)
def test_domain_surfaces_do_not_import_orchestration_layers(
    project_root: Path,
    root_path: str,
    surface_label: str,
) -> None:
    """Domain surfaces must not depend on application/infrastructure/composition."""
    root = project_root / root_path
    if not root.exists():
        pytest.skip(f"{root_path} not found")

    violations: list[str] = []
    for py_file in sorted(root.rglob("*.py")):
        violations.extend(_collect_disallowed_imports(py_file))

    assert not violations, (
        f"{surface_label} import non-domain layers (application/"
        "infrastructure/composition):\n" + "\n".join(violations)
    )


@pytest.mark.parametrize(
    ("root_path", "file_glob", "surface_label"),
    (
        (
            "src/bioetl/domain",
            "*.py",
            "Production domain modules",
        ),
        (
            "tests/unit/domain",
            "*.py",
            "Domain unit tests",
        ),
    ),
)
def test_domain_surfaces_do_not_use_filesystem_wall_clock_or_yaml_seams(
    project_root: Path,
    root_path: str,
    file_glob: str,
    surface_label: str,
) -> None:
    """Domain surfaces must stay pure and deterministic."""
    root = project_root / root_path
    if not root.exists():
        pytest.skip(f"{root_path} not found")

    violations: list[RuntimeSeamViolation] = []
    for py_file in sorted(root.rglob(file_glob)):
        violations.extend(_collect_disallowed_runtime_seams(py_file))
    violations = _filter_allowed_runtime_seams(
        project_root=project_root,
        violations=violations,
    )

    assert not violations, (
        f"{surface_label} use forbidden filesystem/time/YAML seams:\n"
        + "\n".join(violation.render() for violation in violations)
        + "\n\nForbidden seams: "
        + ", ".join(label for label, _reason in DISALLOWED_RUNTIME_SEAMS)
        + "\n\nAllowed exceptions must be explicit in _ALLOWED_RUNTIME_SEAMS."
    )


def test_runtime_seam_detector_catches_representative_violations(
    tmp_path: Path,
) -> None:
    """Regression proof for the runtime-seam detector used by the purity guard."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        "\n".join(
            [
                "import time",
                "import yaml",
                "from datetime import datetime",
                "from pathlib import Path",
                "open('x')",
                "Path('x').open()",
                "Path('x').read_text()",
                "Path('x').write_text('x')",
                "Path('x').glob('*.py')",
                "Path('x').exists()",
                "Path('x').mkdir()",
                "Path('x').touch()",
                "Path('x').unlink()",
                "datetime.now()",
                "datetime.utcnow()",
                "time.time()",
                "yaml.safe_load('x: 1')",
            ]
        ),
        encoding="utf-8",
    )

    seams = {violation.seam for violation in _collect_disallowed_runtime_seams(sample)}

    assert {
        "open",
        "path.open",
        "read_text",
        "write_text",
        "glob",
        "exists",
        "mkdir",
        "touch",
        "unlink",
        "yaml",
        "datetime.now",
        "datetime.utcnow",
        "time.time",
    } <= seams
