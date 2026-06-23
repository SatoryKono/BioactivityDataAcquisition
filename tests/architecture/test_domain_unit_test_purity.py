"""Architecture guards for domain purity and domain-unit test purity."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

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
        "tests/unit/domain/normalization/test_pubchem_constants_yaml.py",
        "read_text",
    ): "PubChem enum catalog contract reads canonical enum YAML",
    (
        "tests/unit/domain/normalization/test_pubchem_constants_yaml.py",
        "yaml",
    ): "PubChem enum catalog contract parses canonical enum YAML",
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
        "tests/unit/domain/normalization/profiles/test_publication_identifier_profiles.py",
        "read_text",
    ): "publication taxonomy fixture contract reads canonical identifier YAML",
    (
        "tests/unit/domain/normalization/profiles/test_publication_identifier_profiles.py",
        "yaml",
    ): "publication taxonomy fixture contract parses canonical identifier YAML",
    (
        "tests/unit/domain/mapping/test_organism_classification.py",
        "path.open",
    ): "organism classification contract reads checked-in target.csv coverage fixture",
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


def _runtime_violation(
    *,
    file_path: Path,
    line: int,
    seam: str,
) -> RuntimeSeamViolation:
    return RuntimeSeamViolation(
        file_path=file_path,
        line=line,
        seam=seam,
        reason=_SEAM_MESSAGES[seam],
    )


def _import_runtime_seam(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return next(
            (
                "yaml"
                for alias in node.names
                if alias.name == "yaml" or alias.name.startswith("yaml.")
            ),
            None,
        )
    if isinstance(node, ast.ImportFrom) and node.module:
        if node.module == "yaml" or node.module.startswith("yaml."):
            return "yaml"
    return None


def _call_runtime_seam(node: ast.Call) -> str | None:
    target = _attribute_path(node.func)
    attr_name = node.func.attr if isinstance(node.func, ast.Attribute) else None
    if target in {"open", "datetime.now", "datetime.utcnow", "time.time"}:
        return target
    if attr_name == "open":
        return "path.open"
    if attr_name in {
        "read_text",
        "write_text",
        "glob",
        "rglob",
        "exists",
        "mkdir",
        "unlink",
        "touch",
    }:
        return attr_name
    if target is not None and target.startswith("yaml."):
        return "yaml"
    return None


def _collect_disallowed_runtime_seams(file_path: Path) -> list[RuntimeSeamViolation]:
    violations: list[RuntimeSeamViolation] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))

    for node in ast.walk(tree):
        import_seam = _import_runtime_seam(node)
        if import_seam is not None:
            violations.append(
                _runtime_violation(
                    file_path=file_path, line=node.lineno, seam=import_seam
                )
            )
        if isinstance(node, ast.Call):
            call_seam = _call_runtime_seam(node)
            if call_seam is not None:
                violations.append(
                    _runtime_violation(
                        file_path=file_path,
                        line=node.lineno,
                        seam=call_seam,
                    )
                )

    return violations


def _relative_repo_path(project_root: Path, file_path: Path) -> str:
    return file_path.relative_to(project_root).as_posix()


def _repo_root_from_project_root(project_root: Path) -> Path:
    """Convert tests/ project_root to actual repository root for exemption lookup."""
    if project_root.name == "tests":
        return project_root.parent
    return project_root


def _filter_allowed_runtime_seams(
    *,
    project_root: Path,
    violations: list[RuntimeSeamViolation],
) -> list[RuntimeSeamViolation]:
    repo_root = _repo_root_from_project_root(project_root)
    return [
        violation
        for violation in violations
        if (
            _relative_repo_path(repo_root, violation.file_path),
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


def test_allowlist_contains_no_stale_legacy_time_cleanup_reasons() -> None:
    """Legacy datetime cleanup reasons must be removed once source tests are fixed."""
    stale_reason = " ".join(
        (
            "legacy deterministic-test cleanup backlog",
            "covered by global test-time ratchet",
        )
    )
    assert stale_reason not in _ALLOWED_RUNTIME_SEAMS.values()
