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

    def document(self) -> dict[str, str]:
        return asdict(self)


def validate_deployment_binding(
    paths: dict[str, Path], binding: TargetDeploymentBinding | None
) -> None:
    """Fail before writes if the caller has not resolved the real deployment."""
    if binding is None:
        raise ValueError("target migration requires a resolved deployment binding")
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


__all__ = ["TargetDeploymentBinding", "validate_deployment_binding"]
