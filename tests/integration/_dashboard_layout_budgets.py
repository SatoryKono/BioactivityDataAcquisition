# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
"""Load named layout/geometry budgets for dashboard geometry contracts.

SSOT: ``docs/03-guides/dashboards/contracts/layout-budgets.yaml``.
``first_load_y_max`` MUST stay equal to
``performance-budgets.yaml:first_screen_y_max``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

LAYOUT_BUDGETS_PATH = Path(
    "docs/03-guides/dashboards/contracts/layout-budgets.yaml"
)
PERFORMANCE_BUDGETS_PATH = Path(
    "docs/03-guides/dashboards/contracts/performance-budgets.yaml"
)

_REQUIRED_ALLOWLIST_KEYS = ("owner", "rationale", "retire_when")


@lru_cache(maxsize=1)
def load_layout_budgets() -> dict[str, Any]:
    payload = yaml.safe_load(LAYOUT_BUDGETS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH} must be a mapping")
    return payload


def _require_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:{key} must be an int")
    return value


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:{key} must be an int or null")
    return value


def _string_set(payload: dict[str, Any], key: str) -> frozenset[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:{key} must be a list of strings")
    return frozenset(value)


def _allowlist(payload: dict[str, Any], key: str) -> dict[tuple[str, int], dict[str, str]]:
    allowlists = payload.get("allowlists")
    if not isinstance(allowlists, dict):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:allowlists must be a mapping")
    entries = allowlists.get(key)
    if not isinstance(entries, list):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:allowlists.{key} must be a list")
    out: dict[tuple[str, int], dict[str, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{LAYOUT_BUDGETS_PATH}:allowlists.{key} entries must be maps")
        dashboard = entry.get("dashboard")
        panel_id = entry.get("id")
        if not isinstance(dashboard, str) or not isinstance(panel_id, int):
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:allowlists.{key} needs dashboard+int id"
            )
        meta = {item: str(entry.get(item) or "") for item in _REQUIRED_ALLOWLIST_KEYS}
        if any(not meta[item].strip() for item in _REQUIRED_ALLOWLIST_KEYS):
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:allowlists.{key} {dashboard}:{panel_id} "
                "needs owner, rationale, and retire_when"
            )
        out[(dashboard, panel_id)] = meta
    return out


_PAYLOAD = load_layout_budgets()

FIRST_WINDOW_Y = _require_int(_PAYLOAD, "first_window_y")
FIRST_LOAD_Y_MAX = _require_int(_PAYLOAD, "first_load_y_max")
VIEWPORT_ROWS = _optional_int(_PAYLOAD, "viewport_rows")
FIRST_SCREEN_MAX_PANELS = _require_int(_PAYLOAD, "first_screen_max_panels")

CANONICAL_ACTION_VERBS = _string_set(_PAYLOAD, "canonical_action_verbs")
PENDING_ACTION_VERBS = _string_set(_PAYLOAD, "pending_action_verbs")
SHELL_TITLES = _string_set(_PAYLOAD, "shell_titles")
BANNED_TITLE_TOKENS = frozenset(
    token.lower() for token in _string_set(_PAYLOAD, "banned_title_tokens")
)
DATA_PANEL_TYPES = _string_set(_PAYLOAD, "data_panel_types")

STRADDLE_ALLOWLIST = _allowlist(_PAYLOAD, "straddle")
MIN_HEIGHT_ALLOWLIST = _allowlist(_PAYLOAD, "min_height")

# DASH-DENSITY-002: scalar information density (values/area).
SCALAR_DENSITY_TYPES = _string_set(_PAYLOAD, "scalar_density_types")
SCALAR_DENSITY_ENFORCED_UIDS = _string_set(_PAYLOAD, "scalar_density_enforced_uids")
SCALAR_DENSITY_ALLOWLIST = _allowlist(_PAYLOAD, "scalar_density")


def min_height_for(panel_type: str, *, nested: bool) -> int | None:
    floors = _PAYLOAD.get("min_height")
    if not isinstance(floors, dict):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:min_height must be a mapping")
    scope = floors.get("nested" if nested else "root")
    if not isinstance(scope, dict):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:min_height scope missing")
    value = scope.get(panel_type)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:min_height.{panel_type} must be int")
    return value


def answer_panels() -> dict[str, list[dict[str, Any]]]:
    mapping = _PAYLOAD.get("answer_panels")
    if not isinstance(mapping, dict):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:answer_panels must be a mapping")
    return mapping


def trust_gate_keys() -> frozenset[tuple[str, int]]:
    entries = _PAYLOAD.get("trust_gate_panels")
    if not isinstance(entries, list):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:trust_gate_panels must be a list")
    keys: set[tuple[str, int]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        dashboard = entry.get("dashboard")
        panel_id = entry.get("id")
        if isinstance(dashboard, str) and isinstance(panel_id, int):
            keys.add((dashboard, panel_id))
    return frozenset(keys)


def title_leading_verb(title: str) -> str:
    """Colon-tolerant leading verb: ``Monitor: Foo`` and ``Monitor Foo``."""
    head = title.strip().split(":", 1)[0].strip()
    if not head:
        return ""
    return head.split()[0]


def mapping_texts(panel: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    mappings = defaults.get("mappings") or []
    if not isinstance(mappings, list):
        return texts
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        options = mapping.get("options")
        if isinstance(options, dict):
            for value in options.values():
                if isinstance(value, dict):
                    texts.append(str(value.get("text") or ""))
                else:
                    texts.append(str(value))
        elif isinstance(options, list):
            for value in options:
                if isinstance(value, dict):
                    result = value.get("result")
                    if isinstance(result, dict):
                        texts.append(str(result.get("text") or ""))
                    else:
                        texts.append(str(value.get("text") or ""))
    return texts


def is_first_window_verdict_card(panel: dict[str, Any]) -> bool:
    """Background stat whose mappings encode the OK/WARN/CRIT palette."""
    if panel.get("type") != "stat":
        return False
    if (panel.get("options") or {}).get("colorMode") != "background":
        return False
    blob = " ".join(mapping_texts(panel)).upper()
    return "OK" in blob and ("CRIT" in blob or "WARN" in blob)
