"""Path and key normalization helpers for architecture exemptions registry."""

from __future__ import annotations

from pathlib import Path
from scripts.engineering.common.repo_paths import resolve_repo_root

_DEFAULT_REGISTRY_PATH = Path("configs/quality/architecture_metric_exemptions.yaml")
_CANONICAL_MODULE_PREFIXES = ("src/bioetl/", "scripts/engineering/")


def project_root() -> Path:
    """Return repository root path."""
    return resolve_repo_root()


def resolve_registry_path(path: Path | str | None = None) -> Path:
    """Resolve registry path against project root for relative paths."""
    candidate = _DEFAULT_REGISTRY_PATH if path is None else Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root() / candidate


def normalize_path_text(value: str) -> str:
    """Normalize mixed-slash and relative path text to canonical form."""
    return value.replace("\\", "/").lstrip("./")


def is_module_path_key(value: str) -> bool:
    """Check whether value matches canonical registry key format."""
    normalized = normalize_path_text(value)
    return normalized.endswith(".py") and normalized.startswith(
        _CANONICAL_MODULE_PREFIXES
    )


def build_module_path_key(
    module_path: Path | str,
    *,
    src_root: Path | str | None = None,
) -> str:
    """Build canonical registry key for a module path.

    Canonical format is a repository-relative POSIX path under either
    ``src/bioetl`` or ``scripts/engineering``.

    Returns:
        Canonical repository-relative registry key.
    """
    text = normalize_path_text(str(module_path))
    if is_module_path_key(text):
        return text

    src_root_path = project_root() / "src" if src_root is None else Path(src_root)
    if not src_root_path.is_absolute():
        src_root_path = (project_root() / src_root_path).absolute()
    path_obj = Path(module_path)
    if not path_obj.is_absolute():
        path_obj = (Path.cwd() / path_obj).absolute()

    repo_root = project_root()
    if path_obj.is_relative_to(repo_root):
        repo_relative = path_obj.relative_to(repo_root).as_posix()
        if is_module_path_key(repo_relative):
            return repo_relative

    if path_obj.is_relative_to(src_root_path):
        rel = path_obj.relative_to(src_root_path).as_posix()
        return f"src/{rel}"

    if text.startswith("bioetl/") and text.endswith(".py"):
        return f"src/{text}"

    raise ValueError(
        "module_path must resolve under src/bioetl or scripts/engineering, "
        f"or already be canonical ({module_path!r})"
    )
