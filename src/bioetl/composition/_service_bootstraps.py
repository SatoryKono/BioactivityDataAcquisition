"""Lazy bootstrap compatibility shims for composition service accessors."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import cast


def resolve_bootstrap_attr(name: str) -> object:
    """Resolve one bootstrap export lazily without invoking it."""
    bootstrap = import_module("bioetl.composition.bootstrap")
    return getattr(bootstrap, name)


def _call_bootstrap(name: str, *args: object, **kwargs: object) -> object:
    """Resolve one bootstrap export lazily and invoke it as a callable."""
    bootstrap_fn = cast(Callable[..., object], resolve_bootstrap_attr(name))
    return bootstrap_fn(*args, **kwargs)


def bootstrap_checkpoint_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_checkpoint_service", *args, **kwargs)


def bootstrap_quarantine_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_quarantine_service", *args, **kwargs)


def bootstrap_bronze_cleanup_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_bronze_cleanup_service", *args, **kwargs)


def bootstrap_vacuum_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_vacuum_service", *args, **kwargs)


def bootstrap_export_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_export_service", *args, **kwargs)


def bootstrap_lock_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_lock_service", *args, **kwargs)


def bootstrap_pipeline_runner_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_pipeline_runner_service", *args, **kwargs)


def bootstrap_config_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_config_service", *args, **kwargs)


def bootstrap_health_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_health_service", *args, **kwargs)


def bootstrap_health_server_dependencies(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_health_server_dependencies", *args, **kwargs)


def bootstrap_metrics_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_metrics_service", *args, **kwargs)


def bootstrap_adr_service(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_adr_service", *args, **kwargs)


def bootstrap_quarantine_port(*args: object, **kwargs: object) -> object:
    return _call_bootstrap("bootstrap_quarantine_port", *args, **kwargs)
