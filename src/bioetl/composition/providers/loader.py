"""Provider loader module.

Обеспечивает явную загрузку и регистрацию всех провайдеров.
Вызывается из bootstrap.py для инициализации ProviderRegistry.
"""

from __future__ import annotations

import importlib

from bioetl.composition.providers.provider_registry import ProviderRegistry

# Список модулей адаптеров для загрузки
# При импорте модуля декоратор @register_provider автоматически
# регистрирует провайдера в ProviderRegistry
_PROVIDER_MODULES = [
    "bioetl.infrastructure.adapters.chembl.client",
    "bioetl.infrastructure.adapters.pubchem.client",
    "bioetl.infrastructure.adapters.uniprot.client",
    "bioetl.infrastructure.adapters.pubmed.pubmed_client",
]

_loaded = False


def load_providers(force: bool = False) -> None:
    """Загружает все зарегистрированные провайдеры.

    Эта функция должна вызываться один раз при старте приложения
    (например, в bootstrap.py) для инициализации ProviderRegistry.

    Функция идемпотентна — повторные вызовы безопасны (если force=False).

    Args:
        force: Если True, перезагружает модули даже если они уже загружены.
            Используется в тестах для сброса состояния.

    Example:
        >>> from bioetl.composition.providers import load_providers
        >>> load_providers()
        >>> # Теперь можно использовать ProviderRegistry
        >>> from bioetl.composition.providers import ProviderRegistry
        >>> config = ProviderRegistry.get("chembl")

    """
    global _loaded
    import sys

    if _loaded and not force:
        return

    for module_path in _PROVIDER_MODULES:
        try:
            if force and module_path in sys.modules:
                # Перезагружаем модуль для повторной регистрации
                importlib.reload(sys.modules[module_path])
            else:
                importlib.import_module(module_path)
        except ImportError as e:
            # Логируем ошибку, но не падаем — провайдер может быть опциональным
            import warnings

            warnings.warn(
                f"Failed to load provider module {module_path}: {e}",
                stacklevel=2,
            )

    _loaded = True


def ensure_providers_loaded() -> None:
    """Гарантирует, что провайдеры загружены.

    Удобная функция для использования в местах, где нужно быть уверенным,
    что ProviderRegistry инициализирован.
    """
    if not _loaded:
        load_providers()


def get_loaded_status() -> bool:
    """Возвращает статус загрузки провайдеров."""
    return _loaded


def reset_loader() -> None:
    """Сбрасывает статус загрузки. Только для тестов."""
    global _loaded
    _loaded = False
    ProviderRegistry.clear()
