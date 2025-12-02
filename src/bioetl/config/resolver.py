import os
from typing import Any
import yaml

from bioetl.config.models import PipelineConfig


class ConfigResolver:
    """
    Загрузка и объединение конфигураций.
    """

    def resolve(self, config_path: str, profile: str = "default") -> PipelineConfig:
        # Simplification for now: just load the yaml
        # Real implementation would merge profile, base, env vars
        
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
            
        # Here we would merge with defaults from profile
        # ...
        
        return PipelineConfig(**raw_config)

