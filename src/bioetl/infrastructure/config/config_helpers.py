"""Config helpers module for common configuration operations."""


def load_config(config_path: str) -> dict[str, object]:
    """Load configuration from a file.
    
    Args:
        config_path: Path to the configuration file.
        
    Returns:
        Loaded configuration dictionary.
    """
    # Placeholder for actual config loading logic
    return {}


def load_and_validate_config(config_path: str) -> dict[str, object]:
    """Load and validate configuration.
    
    Args:
        config_path: Path to the configuration file.
        
    Returns:
        Validated configuration dictionary.
        
    Raises:
        ValueError: If configuration is not found or invalid.
    """
    config = load_config(config_path)
    if not config:
        raise ValueError("Config not found")
    return config
