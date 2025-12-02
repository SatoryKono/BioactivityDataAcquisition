# Configuration Infrastructure

Система конфигурации BioETL построена на каскадном объединении (merging) настроек из разных источников.

## ConfigResolver

`ConfigResolver` отвечает за загрузку и объединение конфигураций в следующем порядке приоритета (от высшего к низшему):

1. **Переменные окружения** (`BIOETL_*`).
2. **CLI Overrides** (параметры `--set key=value`).
3. **Pipeline Config** (специфичный YAML пайплайна, например, `activity.yaml`).
4. **Profile Config** (выбранный профиль, например, `production.yaml`).
5. **Base Profile** (`chembl_default.yaml`).

## SecretProvider

Для безопасной работы с секретами (API keys, credentials) используется `SecretProviderABC`.
Реализация по умолчанию `EnvSecretProvider` читает секреты из переменных окружения.

**Важно:** Секреты никогда не должны храниться в YAML-файлах или коде.

## Профили

Конфигурации поддерживают наследование через поле `extends`.

```yaml
# development.yaml
extends: chembl_default

pagination:
  limit: 100  # Переопределение для dev
```

