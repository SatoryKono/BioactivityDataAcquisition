"""Lazy bootstrap compatibility shims for composition service accessors."""

from __future__ import annotations

from importlib import import_module


def resolve_bootstrap_attr(name: str) -> object:
    """Resolve one bootstrap export lazily to keep CLI imports light."""
    bootstrap = import_module("bioetl.composition.bootstrap")
    return getattr(bootstrap, name)


def bootstrap_checkpoint_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_checkpoint_service")(*args, **kwargs)


def bootstrap_quarantine_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_quarantine_service")(*args, **kwargs)


def bootstrap_bronze_cleanup_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_bronze_cleanup_service")(*args, **kwargs)


def bootstrap_vacuum_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_vacuum_service")(*args, **kwargs)


def bootstrap_export_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_export_service")(*args, **kwargs)


def bootstrap_lock_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_lock_service")(*args, **kwargs)


def bootstrap_pipeline_runner_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_pipeline_runner_service")(*args, **kwargs)


def bootstrap_config_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_config_service")(*args, **kwargs)


def bootstrap_health_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_health_service")(*args, **kwargs)


def bootstrap_health_server_dependencies(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_health_server_dependencies")(
        *args, **kwargs
    )


def bootstrap_metrics_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_metrics_service")(*args, **kwargs)


def bootstrap_adr_service(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_adr_service")(*args, **kwargs)


def bootstrap_quarantine_port(*args: object, **kwargs: object) -> object:
    return resolve_bootstrap_attr("bootstrap_quarantine_port")(*args, **kwargs)
