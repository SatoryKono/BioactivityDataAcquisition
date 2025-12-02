from pathlib import Path
from typing import Any
import yaml

from bioetl.config.models import PipelineConfig


class ConfigResolver:
    """
    Загрузка и объединение конфигураций.
    Поддерживает наследование профилей через 'extends' и переопределение.
    """

    def __init__(self, profiles_dir: str = "configs/profiles") -> None:
        self.profiles_dir = Path(profiles_dir)

    def resolve(self, config_path: str, profile: str = "default") -> PipelineConfig:
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
        final_config = self._deep_merge(final_config, config_dict)
        
        # 4. Apply CLI profile overrides if not default
        if profile and profile != "default":
            # CLI profile might also have inheritance (e.g. development extends chembl_default)
            # But typically it's treated as a set of overrides.
            # If CLI profile extends something, we should probably resolve it too.
            cli_profile_dict = self._resolve_profile(profile)
            final_config = self._deep_merge(final_config, cli_profile_dict)
            
        return PipelineConfig(**final_config)

    def _resolve_profile(self, profile_name: str) -> dict[str, Any]:
        """
        Recursively resolves a profile.
        """
        path = self.profiles_dir / f"{profile_name}.yaml"
        if not path.exists():
            # If profile doesn't exist, return empty or raise?
            # For "default", if missing, maybe empty.
            if profile_name == "default":
                return {}
            raise FileNotFoundError(f"Profile not found: {path}")
            
        profile_dict = self._load_yaml(path)
        
        # Handle inheritance within profiles
        parent_profile = profile_dict.get("extends")
        if parent_profile:
            parent_dict = self._resolve_profile(parent_profile)
            profile_dict = self._deep_merge(parent_dict, profile_dict)
            
        return profile_dict

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _deep_merge(self, base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two dictionaries.
        """
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
