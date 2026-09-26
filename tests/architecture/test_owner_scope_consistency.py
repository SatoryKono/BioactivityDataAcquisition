# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture test: exemption owner must match file layer scope.

Validates that path-based exemption entries (file_size_limits) have an owner
consistent with the layer→subsystem mapping defined in debt_scorecard.yaml.
"""

from __future__ import annotations

import pytest

import re

from bioetl.infrastructure.quality import load_debt_scorecard, load_exemptions_registry


pytestmark = pytest.mark.architecture


def _layer_from_path(path: str) -> str | None:
    """Extract the architectural layer from a source file path."""
    match = re.search(r"src/bioetl/(\w+)", path)
    return match.group(1) if match else None


def _build_layer_to_owner_map(scorecard: dict) -> dict[str, str]:  # type: ignore[type-arg]
    """Build mapping from layer keyword to expected owner."""
    governance = scorecard.get("governance", {})
    subsystems = governance.get("owner_registry_q3_subsystems", {})

    layer_to_owner: dict[str, str] = {}
    for _subsystem_key, config in subsystems.items():
        owner = config.get("owner", "")
        for scope_item in config.get("scope", []):
            layer_to_owner[scope_item] = owner
    return layer_to_owner


_LAYER_TO_SCOPES: dict[str, list[str]] = {
    "domain": ["domain-model", "domain-schemas", "domain-mapping"],
    "application": ["application"],
    "infrastructure": ["infrastructure"],
    "composition": ["composition"],
    "interfaces": ["interfaces"],
}


def _expected_owner_for_layer(layer: str, layer_to_owner: dict[str, str]) -> str | None:
    """Resolve the expected owner for an architectural layer."""
    scopes = _LAYER_TO_SCOPES.get(layer, [])
    owners = {layer_to_owner[s] for s in scopes if s in layer_to_owner}
    if len(owners) == 1:
        return owners.pop()
    return None


def test_file_size_limits_owner_matches_layer_scope() -> None:
    """Each file_size_limits entry owner must match its file layer scope."""
    registry = load_exemptions_registry()
    scorecard = load_debt_scorecard()
    layer_to_owner = _build_layer_to_owner_map(scorecard)

    registries = registry.get("registries", {})
    file_size_entries = registries.get("file_size_limits", {})
    assert isinstance(file_size_entries, dict)

    mismatches: list[str] = []
    for path, entry in file_size_entries.items():
        if not isinstance(entry, dict):
            continue
        actual_owner = entry.get("owner", "")
        layer = _layer_from_path(path)
        if layer is None:
            continue
        expected = _expected_owner_for_layer(layer, layer_to_owner)
        if expected is None:
            continue
        if actual_owner != expected:
            mismatches.append(
                f"{path}: owner={actual_owner!r}, expected={expected!r} (layer={layer})"
            )

    assert not mismatches, "Owner↔scope mismatches in file_size_limits:\n" + "\n".join(
        f"  - {m}" for m in mismatches
    )
