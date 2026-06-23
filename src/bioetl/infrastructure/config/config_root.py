"""Canonical config-root resolution helpers.

The repository keeps tracked runtime configuration under the repo-root
``configs/`` tree. Composition/runtime/bootstrap code should resolve that
location through this module instead of relying on the current working
directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "ConfigRootResolver",
    "get_default_repo_root",
    "resolve_config_subdir",
    "resolve_configs_root",
]


def get_default_repo_root() -> Path:
    """Return the repository root inferred from the installed source layout."""
    source_path = Path(__file__).resolve()
    for candidate in source_path.parents:
        if not (candidate / "configs").is_dir():
            continue
        if (candidate / "pyproject.toml").is_file() or (
            candidate / "AGENTS.md"
        ).is_file():
            return candidate
    return source_path.parents[4]


@dataclass(frozen=True, slots=True)
class ConfigRootResolver:
    """Resolve the canonical tracked ``configs/`` directory for this checkout."""

    repo_root: Path = field(default_factory=get_default_repo_root)
    prefer_cwd_configs: bool = False

    @staticmethod
    def _is_rooted_explicit_path(path: Path) -> bool:
        """Whether an explicit path has a filesystem root even without a drive."""
        return bool(path.root)

    def resolve(self, configs_root: Path | None = None) -> Path:
        """Return an explicit configs root or the canonical repo-root fallback."""
        if configs_root is not None:
            explicit_root = configs_root.expanduser()
            if explicit_root.is_absolute() or self._is_rooted_explicit_path(
                explicit_root
            ):
                return explicit_root
            return (self.repo_root / explicit_root).resolve()
        if self.prefer_cwd_configs and self.repo_root == get_default_repo_root():
            cwd_configs = (Path.cwd() / "configs").resolve()
            if cwd_configs.is_dir():
                return cwd_configs
        return (self.repo_root / "configs").resolve()


def resolve_configs_root(
    configs_root: Path | None = None,
    *,
    prefer_cwd_configs: bool = False,
) -> Path:
    """Convenience wrapper for the canonical config-root resolver."""
    return ConfigRootResolver(prefer_cwd_configs=prefer_cwd_configs).resolve(
        configs_root
    )


def resolve_config_subdir(
    subdir: str | Path,
    *,
    configs_root: Path | None = None,
) -> Path:
    """Resolve a tracked config subdirectory beneath the canonical config root."""
    subdir_path = Path(subdir).expanduser()
    if subdir_path.is_absolute() or ConfigRootResolver._is_rooted_explicit_path(
        subdir_path
    ):
        return subdir_path

    parts = subdir_path.parts
    if parts and parts[0] == "configs":
        subdir_path = Path(*parts[1:])
    return resolve_configs_root(configs_root) / subdir_path
