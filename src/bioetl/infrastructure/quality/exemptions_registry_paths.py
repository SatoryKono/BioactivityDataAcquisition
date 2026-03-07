"""Path and key normalization helpers for architecture exemptions registry."""

from __future__ import annotations

from pathlib import Path

_DEFAULT_REGISTRY_PATH = Path("configs/quality/architecture_metric_exemptions.yaml")
_SRC_ROOT_PREFIX = "src/bioetl/"


def project_root() -> Path:
    """Return repository root path."""
    return Path(__file__).resolve().parents[4]


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
    return normalized.startswith(_SRC_ROOT_PREFIX) and normalized.endswith(".py")


def build_module_path_key(
    module_path: Path | str,
    *,
    src_root: Path | str | None = None,
) -> str:
    """Build canonical registry key for a module path.

    Canonical format is repository-relative POSIX path:
    ``src/bioetl/<layer>/.../<module>.py``.

    Returns:
        Canonical registry key string in format 'src/bioetl/.../module.py'.
    """
    text = normalize_path_text(str(module_path))
    if is_module_path_key(text):
        return text

    src_root_path = (
        project_root() / "src" if src_root is None else Path(src_root).resolve()
    )
    path_obj = Path(module_path)
    if not path_obj.is_absolute():
        path_obj = path_obj.resolve()

    if path_obj.is_relative_to(src_root_path):
        rel = path_obj.relative_to(src_root_path).as_posix()
        return f"src/{rel}"

    if text.startswith("bioetl/") and text.endswith(".py"):
        return f"src/{text}"

    raise ValueError(
        f"module_path must resolve under src/ or already be canonical ({module_path!r})"
    )
