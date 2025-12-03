from pathlib import Path
from typing import Any

import yaml

from bioetl.core.utils.merge import deep_merge
from bioetl.infrastructure.config.models import PipelineConfig


class ConfigResolver:
    """
    Загрузка и объединение конфигураций.
    Поддерживает наследование профилей через 'extends' и переопределение.
    """

    def __init__(self, profiles_dir: str = "configs/profiles") -> None:
        self.profiles_dir = Path(profiles_dir)
        self._profile_cache: dict[str, dict[str, Any]] = {}

    def resolve(
        self, config_path: str, profile: str = "default"
    ) -> PipelineConfig:
        """
        Resolves configuration by merging:
        1. Base profile (referenced in config via 'extends')
        2. Pipeline config (the file itself)
        3. CLI profile overrides (if provided)
        """
        # 1. Load the main config file
        config_dict = self._load_yaml(Path(config_path))

        # 2. Resolve base profile if 'extends' is present in config
        base_profile_name = config_dict.get("extends")
        final_config = {}

        if base_profile_name:
            final_config = self._resolve_profile(base_profile_name)

        # 3. Merge config over base profile
        final_config = deep_merge(final_config, config_dict)

        # 4. Apply CLI profile overrides if not default
        if profile and profile != "default":
            cli_profile_dict = self._resolve_profile(profile)
            final_config = deep_merge(final_config, cli_profile_dict)

        return PipelineConfig(**final_config)

    def _resolve_profile(
        self, profile_name: str, visited: set[str] | None = None
    ) -> dict[str, Any]:
        """
        Recursively resolves a profile.
        """
        # Check cache first
        if profile_name in self._profile_cache:
            return self._profile_cache[profile_name]

        # Cycle detection
        visited = visited or set()
        if profile_name in visited:
            raise ValueError(f"Circular extends detected: {profile_name}")
        visited.add(profile_name)

        path = self.profiles_dir / f"{profile_name}.yaml"
        if not path.exists():
            if profile_name == "default":
                return {}
            raise FileNotFoundError(f"Profile not found: {path}")

        profile_dict = self._load_yaml(path)

        # Handle inheritance within profiles
        parent_profile = profile_dict.get("extends")
        if parent_profile:
            parent_dict = self._resolve_profile(parent_profile, visited)
            profile_dict = deep_merge(parent_dict, profile_dict)

        # Update cache
        self._profile_cache[profile_name] = profile_dict
        return profile_dict

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
