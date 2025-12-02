# 03 Config Precedence and Profiles

> **Note**: This document has been consolidated into the [Configuration Guide](../../guides/configuration.md). Please refer to that document for detailed information about configuration precedence and profiles.

## Quick Reference

Configuration sources are applied in the following order (highest to lowest priority):

1. Environment variables
2. CLI overrides (`--set key=value`)
3. Pipeline configuration files
4. Profiles

For detailed information, examples, and best practices, see [Configuration Guide](../../guides/configuration.md).

## Related Components

- **FileConfigResolver**: резолвер конфигурации (см. `docs/reference/infrastructure/config/00-config-resolver.md`)
- **EnvSecretProvider**: провайдер секретов (см. `docs/reference/infrastructure/config/01-secret-provider.md`)
