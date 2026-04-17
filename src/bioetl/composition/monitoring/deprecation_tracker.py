"""Track usage of deprecated classes and methods."""

from __future__ import annotations

import logging
import warnings
from typing import Any, Callable, Type, TypeVar

T = TypeVar("T")

# Set up deprecation logger
_deprecation_logger = logging.getLogger("bioetl.deprecation")
_deprecation_logger.setLevel(logging.WARNING)

# Add handler if not already configured
if not _deprecation_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    _deprecation_logger.addHandler(handler)


def track_deprecated_class(
    old_class_name: str, new_class_name: str
) -> Callable[[Type[T]], Type[T]]:
    """Decorator to track usage of deprecated classes."""

    def decorator(cls: Type[T]) -> Type[T]:
        original_init = cls.__init__

        def new_init(
            self: T,
            *args: Any,  # Any: Decorator must preserve arbitrary constructor signatures.
            **kwargs: Any,  # Any: Decorator must preserve arbitrary constructor signatures.
        ) -> None:
            # Log the usage
            _deprecation_logger.warning(
                f"Deprecated class used: {old_class_name}. "
                f"Please migrate to {new_class_name}. "
                f"This will be removed in v2.0."
            )

            # Call original init
            original_init(self, *args, **kwargs)

        # Replace init method
        cls.__init__ = new_init

        return cls

    return decorator


def log_deprecation_warning(message: str, stacklevel: int = 2) -> None:
    """Log a deprecation warning with consistent formatting."""
    _deprecation_logger.warning(message)
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


# Example usage:
# @track_deprecated_class("OldClassName", "NewClassName")
# class OldClassName(NewClassName):
#     pass
