"""ARCH-REF-04 / #7705: mixin host depth gate (advisory config, hard max checks)."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

CONFIG = Path("configs/quality/mixin_collaborator_metrics.yaml")


@pytest.mark.architecture
def test_mixin_host_direct_base_budgets() -> None:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    hosts = payload.get("hosts", [])
    assert hosts, "mixin_collaborator_metrics.yaml must define hosts"

    failures: list[str] = []
    for row in hosts:
        assert isinstance(row, dict)
        module_name = str(row["module"])
        class_name = str(row["name"])
        max_bases = int(row["max_direct_mixin_bases"])
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        # Count direct bases excluding object
        bases = [b for b in cls.__bases__ if b is not object]
        if len(bases) > max_bases:
            failures.append(
                f"{class_name}: direct bases {len(bases)} > max {max_bases} "
                f"({[b.__name__ for b in bases]})"
            )
    assert failures == [], "Mixin host budgets exceeded:\n" + "\n".join(failures)
