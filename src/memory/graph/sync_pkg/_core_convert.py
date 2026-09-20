"""Coercion, text, path, and git helpers extracted from the graph sync kernel (AUD-001 slice 1)."""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

YAML_SUFFIX = ".yaml"

GITHUB_DIR = ".github"

GITHUB_PATH_PREFIX = f"{GITHUB_DIR}/"

_DOCS_DRIFT_EXCLUDED_PREFIXES = (
    ".github/ISSUES",
    ".github/ISSUE_TEMPLATE",
    ".github/actions",
    ".github/workflows",
    "docs/00-project/ai",
    "docs/02-architecture/diagrams/descriptions",
    "docs/reports/evidence",
    "docs/reports",
)

__all__ = [
    "GITHUB_DIR",
    "GITHUB_PATH_PREFIX",
    "YAML_SUFFIX",
    "_DOCS_DRIFT_EXCLUDED_PREFIXES",
    "_as_iterable",
    "_as_mapping",
    "_as_string_list",
    "_coerce_float",
    "_coerce_int",
    "_git_cached_commit_ages",
    "_is_claim_candidate",
    "_is_dataframe_model_base",
    "_is_doc_artifact_file",
    "_is_excluded_docs_drift_prefix",
    "_is_ignored_repo_path",
    "_is_protocol_base",
    "_module_dotted_name",
    "_normalize_cli_command_name",
    "_normalize_docs_glob_candidate",
    "_normalize_env_value",
    "_normalize_repo_relative_path",
    "_normalize_workflow_matrix_axis_name",
    "_normalized_alert_selector",
    "_normalized_text_list",
    "_optional_text",
    "_read_text",
    "_rel_path",
    "_resolve_git_executable",
    "_resolve_repo_path",
]


def _as_iterable(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return []


def _as_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    return {}


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _coerce_int(value: object, default: int = 0) -> int:
    """Coerce mapping/JSON payload values to int for static checkers and runtime."""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _git_cached_commit_ages(
    unique_paths: list[str],
    cache: dict[str, int | None],
) -> dict[str, int | None]:
    return {path: cache[path] for path in unique_paths if path in cache}


def _is_claim_candidate(stripped_line: str) -> bool:
    if not stripped_line or len(stripped_line) < 12:
        return False
    lowered = stripped_line.lower()
    return any(
        token in lowered
        for token in ("must", "never", "must not", "should not", "required")
    )


def _is_dataframe_model_base(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "DataFrameModel"
    if isinstance(node, ast.Attribute):
        return node.attr == "DataFrameModel"
    if isinstance(node, ast.Subscript):
        return _is_dataframe_model_base(node.value)
    return False


def _is_doc_artifact_file(relative_file: str, file_extension: str) -> bool:
    return file_extension in {".md", ".yml", YAML_SUFFIX} and (
        relative_file in {"README.md", "mkdocs.yml"}
        or relative_file.startswith("docs/")
        or relative_file.startswith(GITHUB_PATH_PREFIX)
    )


def _is_excluded_docs_drift_prefix(normalized_source_path: str) -> bool:
    return any(
        normalized_source_path == prefix
        or normalized_source_path.startswith(f"{prefix}/")
        for prefix in _DOCS_DRIFT_EXCLUDED_PREFIXES
    )


def _is_ignored_repo_path(path: Path) -> bool:
    return "__pycache__" in path.parts


def _is_protocol_base(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "Protocol"
    if isinstance(node, ast.Attribute):
        return node.attr == "Protocol"
    if isinstance(node, ast.Subscript):
        return _is_protocol_base(node.value)
    return False


def _module_dotted_name(relative_path: str) -> str:
    without_suffix = relative_path.removesuffix(".py")
    return without_suffix.replace("/", ".")


def _normalize_cli_command_name(raw_command: str) -> str | None:
    lowered = raw_command.lower()
    if " -m bioetl " in lowered:
        match = re.search(r"-m\s+bioetl\s+([\w-]+)", raw_command)
        if match:
            return f"bioetl {match.group(1)}"
        return "bioetl"
    script_module_match = re.search(
        r"-m\s+scripts\.(\w+)(?:\s+([\w.-]+))?", raw_command
    )
    if script_module_match:
        module_name = script_module_match.group(1)
        subcommand = script_module_match.group(2)
        if subcommand and not subcommand.startswith("-"):
            return f"scripts.{module_name} {subcommand}"
        return f"scripts.{module_name}"
    script_path_match = re.search(r"scripts/(\w+)/([\w.-]+)", raw_command)
    if script_path_match:
        return f"scripts.{script_path_match.group(1)} {script_path_match.group(2)}"
    return None


def _normalize_docs_glob_candidate(candidate: str) -> str:
    if candidate.endswith("/**"):
        return candidate[: -len("/**")]
    if "/*." in candidate:
        return candidate.rsplit("/", 1)[0]
    if candidate.endswith("/*"):
        return candidate[: -len("/*")]
    return candidate


def _normalize_env_value(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def _normalize_repo_relative_path(relative_path: str) -> str:
    return relative_path.replace("\\", "/").strip().strip("/")


def _normalize_workflow_matrix_axis_name(axis_name: str) -> str:
    """Stabilize workflow matrix axis names across workflow refactors."""
    if axis_name == "test-group":
        return "suite"
    return axis_name


def _normalized_alert_selector(group_name: str, expr: str) -> str:
    return f"{group_name} {expr}".lower()


def _normalized_text_list(value: object) -> list[str] | None:
    if not isinstance(value, list | tuple):
        return None
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return normalized


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_text(path: Path) -> str:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    return path.read_text(encoding="utf-8")


def _rel_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _resolve_git_executable() -> str:
    git_path = shutil.which("git")
    if git_path:
        return git_path
    windows_candidates = (
        "/mnt/c/Program Files/Git/cmd/git.exe",
        "/mnt/c/Program Files/Git/bin/git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    )
    for candidate in windows_candidates:
        if Path(candidate).exists():
            return candidate
    return "git"


def _resolve_repo_path(root: Path, base_path: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (base_path.parent / candidate).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if candidate.exists():
        return candidate
    return None
