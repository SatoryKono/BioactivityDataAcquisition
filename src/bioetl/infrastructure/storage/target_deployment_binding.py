"""Immutable deployment facts supplied by the real composition/config loader."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from iuphar_target_class.stage0.io import sha256_file


@dataclass(frozen=True, slots=True)
class TargetDeploymentBinding:
    """Bind maintenance paths to the configuration actually loaded after cutover."""

    config_path: str
    original_config_sha256: str
    deployment_config_sha256: str
    silver_path: str
    gold_path: str
    profile_sha256: str
    settings_sha256: str
    role: str = "deployment"
    rehearsal_root: str = ""
    approved_workspace: str = ""

    def document(self) -> dict[str, str]:
        document = asdict(self)
        if self.role == "deployment" and not (self.rehearsal_root or self.approved_workspace):
            # Preserve historical production journal/plan identities.
            for key in ("role", "rehearsal_root", "approved_workspace"):
                document.pop(key)
        return document


def validate_rehearsal_paths(
    paths: dict[str, Path], *, workspace: Path, rehearsal_root: Path
) -> Path:
    """Fence every mutable resource inside one unredirected local occurrence."""
    for path in (workspace, rehearsal_root):
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("rehearsal needs explicit absolute workspace/root paths")
        if any(part.is_symlink() or part.is_junction() for part in (path, *path.parents)):
            raise ValueError("rehearsal refuses symlink/junction paths")
    workspace = workspace.resolve(strict=True)
    root = rehearsal_root.resolve(strict=True)
    local = workspace / "reports" / "local"
    if root == local or not root.is_relative_to(local):
        raise ValueError("rehearsal root must be a dedicated reports/local occurrence")
    if any(path.resolve() == root or not path.resolve().is_relative_to(root) for path in paths.values()):
        raise ValueError("all rehearsal resources must stay inside the rehearsal root")
    return root


def _validate_binding_role(paths: dict[str, Path], binding: TargetDeploymentBinding) -> None:
    if binding.role == "rehearsal":
        validate_rehearsal_paths(
            paths,
            workspace=Path(binding.approved_workspace),
            rehearsal_root=Path(binding.rehearsal_root),
        )
    elif binding.role != "deployment" or binding.rehearsal_root or binding.approved_workspace:
        raise ValueError("unsupported or mixed target deployment binding role")


def validate_deployment_binding(
    paths: dict[str, Path], binding: TargetDeploymentBinding | None
) -> None:
    """Fail before writes if the caller has not resolved the real deployment."""
    if binding is None:
        raise ValueError("target migration requires a resolved deployment binding")
    _validate_binding_role(paths, binding)
    expected = {
        "config_path": str(paths["config"].resolve()),
        "silver_path": str(paths["silver"].resolve()),
        "gold_path": str(paths["gold"].resolve()),
        "original_config_sha256": sha256_file(paths["config"]),
        "deployment_config_sha256": sha256_file(paths["candidate_config"]),
    }
    if any(getattr(binding, key) != value for key, value in expected.items()):
        raise ValueError(
            "deployment binding differs from the actual migration paths/bytes"
        )


__all__ = ["TargetDeploymentBinding", "validate_deployment_binding", "validate_rehearsal_paths"]
