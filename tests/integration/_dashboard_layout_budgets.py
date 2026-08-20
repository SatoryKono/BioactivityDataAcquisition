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

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

LAYOUT_BUDGETS_PATH = Path("docs/03-guides/dashboards/contracts/layout-budgets.yaml")
_TOPK_RE = re.compile(r"topk\(\s*(\d+)\s*,", re.IGNORECASE)
_LIMIT_RE = re.compile(r"[?&]limit=(\d+)")
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


def _named_panel_set(
    payload: dict[str, Any], key: str
) -> dict[tuple[str, int], dict[str, str]]:
    """Load a top-level dashboard+id list that requires governance metadata."""
    entries = payload.get(key)
    if not isinstance(entries, list):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:{key} must be a list")
    out: dict[tuple[str, int], dict[str, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{LAYOUT_BUDGETS_PATH}:{key} entries must be maps")
        dashboard = entry.get("dashboard")
        panel_id = entry.get("id")
        if not isinstance(dashboard, str) or not isinstance(panel_id, int):
            raise ValueError(f"{LAYOUT_BUDGETS_PATH}:{key} needs dashboard+int id")
        meta = {item: str(entry.get(item) or "") for item in _REQUIRED_ALLOWLIST_KEYS}
        if any(not meta[item].strip() for item in _REQUIRED_ALLOWLIST_KEYS):
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:{key} {dashboard}:{panel_id} "
                "needs owner, rationale, and retire_when"
            )
        out[(dashboard, panel_id)] = meta
    return out


def _allowlist(
    payload: dict[str, Any], key: str
) -> dict[tuple[str, int], dict[str, str]]:
    allowlists = payload.get("allowlists")
    if not isinstance(allowlists, dict):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:allowlists must be a mapping")
    entries = allowlists.get(key)
    if not isinstance(entries, list):
        raise ValueError(f"{LAYOUT_BUDGETS_PATH}:allowlists.{key} must be a list")
    out: dict[tuple[str, int], dict[str, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:allowlists.{key} entries must be maps"
            )
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
FIRST_SCREEN_SHELL_PANELS = _named_panel_set(_PAYLOAD, "first_screen_shell_panels")

CANONICAL_ACTION_VERBS = _string_set(_PAYLOAD, "canonical_action_verbs")
PENDING_ACTION_VERBS = _string_set(_PAYLOAD, "pending_action_verbs")
SHELL_TITLES = _string_set(_PAYLOAD, "shell_titles")
BANNED_TITLE_TOKENS = frozenset(
    token.lower() for token in _string_set(_PAYLOAD, "banned_title_tokens")
)
DATA_PANEL_TYPES = _string_set(_PAYLOAD, "data_panel_types")

STRADDLE_ALLOWLIST = _allowlist(_PAYLOAD, "straddle")
MIN_HEIGHT_ALLOWLIST = _allowlist(_PAYLOAD, "min_height")
FIRST_WINDOW_OVERFLOW_ALLOWLIST = _allowlist(_PAYLOAD, "first_window_overflow")
HORIZONTAL_SCROLL_ALLOWLIST = _allowlist(_PAYLOAD, "horizontal_scroll")
PANEL_CONTAINMENT_TOLERANCE_PX = _require_int(
    _PAYLOAD, "panel_containment_tolerance_px"
)
FIRST_WINDOW_CONTAINMENT_TYPES = _string_set(_PAYLOAD, "first_window_containment_types")

# DASH-DENSITY-002: scalar information density (values/area).
SCALAR_DENSITY_TYPES = _string_set(_PAYLOAD, "scalar_density_types")
SCALAR_DENSITY_ENFORCED_UIDS = _string_set(_PAYLOAD, "scalar_density_enforced_uids")
SCALAR_DENSITY_ALLOWLIST = _allowlist(_PAYLOAD, "scalar_density")
SYNTHETIC_ZERO_ALLOWLIST = _allowlist(_PAYLOAD, "synthetic_zero")


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


def first_window_summary_tables() -> tuple[dict[str, Any], ...]:
    entries = _PAYLOAD.get("first_window_summary_tables")
    if not isinstance(entries, list):
        raise ValueError(
            f"{LAYOUT_BUDGETS_PATH}:first_window_summary_tables must be a list"
        )
    out: list[dict[str, Any]] = []
    required = ("dashboard", "id", "max_rows", "owner", "bind")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:first_window_summary_tables entries must be maps"
            )
        missing = [key for key in required if entry.get(key) in (None, "")]
        if missing:
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:first_window_summary_tables missing {missing}"
            )
        dashboard = entry.get("dashboard")
        panel_id = entry.get("id")
        max_rows = entry.get("max_rows")
        bind = entry.get("bind")
        owner = entry.get("owner")
        if not isinstance(dashboard, str) or not isinstance(panel_id, int):
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:first_window_summary_tables needs dashboard+int id"
            )
        if not isinstance(max_rows, int) or isinstance(max_rows, bool) or max_rows < 1:
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:first_window_summary_tables {dashboard}:{panel_id} "
                "max_rows must be a positive int"
            )
        if not isinstance(bind, str) or not isinstance(owner, str):
            raise ValueError(
                f"{LAYOUT_BUDGETS_PATH}:first_window_summary_tables {dashboard}:{panel_id} "
                "needs bind and owner"
            )
        out.append(
            {
                "dashboard": dashboard,
                "id": panel_id,
                "max_rows": max_rows,
                "owner": owner,
                "bind": bind,
            }
        )
    return tuple(out)


def is_first_window_panel(
    panel: dict[str, Any], *, first_window_y: int | None = None
) -> bool:
    """Root-style first-window test: non-row and ``gridPos.y < FIRST_WINDOW_Y``."""
    if panel.get("type") == "row":
        return False
    fold = FIRST_WINDOW_Y if first_window_y is None else first_window_y
    grid = panel.get("gridPos")
    if not isinstance(grid, dict):
        return False
    y = grid.get("y")
    return isinstance(y, int) and y < fold


def is_navigation_panel(panel: dict[str, Any]) -> bool:
    """Navigation bus: panel id 1000 or a Navigate* title."""
    if panel.get("id") == 1000:
        return True
    title = panel.get("title")
    return isinstance(title, str) and title.startswith("Navigate")


def is_first_screen_shell_panel(dashboard: str, panel: dict[str, Any]) -> bool:
    """Named empty-title text rail excluded from first_screen_max_panels."""
    panel_id = panel.get("id")
    if not isinstance(panel_id, int):
        return False
    return (dashboard, panel_id) in FIRST_SCREEN_SHELL_PANELS


def is_first_screen_budget_panel(
    dashboard: str, panel: dict[str, Any], *, first_window_y: int | None = None
) -> bool:
    """Root first-window panel that counts toward first_screen_max_panels."""
    if not is_first_window_panel(panel, first_window_y=first_window_y):
        return False
    if is_navigation_panel(panel):
        return False
    return not is_first_screen_shell_panel(dashboard, panel)


def select_first_screen_budget_panels(
    dashboard: str,
    panels: list[Any],
    *,
    first_window_y: int | None = None,
) -> list[dict[str, Any]]:
    """Select root panels counted by first_screen_max_panels."""
    selected: list[dict[str, Any]] = []
    for panel in panels or []:
        if isinstance(panel, dict) and is_first_screen_budget_panel(
            dashboard, panel, first_window_y=first_window_y
        ):
            selected.append(panel)
    return selected


def collapsed_row_above_fold(
    panel: dict[str, Any], *, first_window_y: int | None = None
) -> bool:
    """True when a collapsed row header sits strictly above the visual fold."""
    if panel.get("type") != "row" or panel.get("collapsed") is not True:
        return False
    fold = FIRST_WINDOW_Y if first_window_y is None else first_window_y
    grid = panel.get("gridPos")
    if not isinstance(grid, dict):
        return False
    y = grid.get("y")
    return isinstance(y, int) and y < fold


def select_first_window_panels(
    panels: list[Any], *, first_window_y: int | None = None
) -> list[dict[str, Any]]:
    """Select root non-row panels that intersect the first window."""
    selected: list[dict[str, Any]] = []
    for panel in panels or []:
        if isinstance(panel, dict) and is_first_window_panel(
            panel, first_window_y=first_window_y
        ):
            selected.append(panel)
    return selected


def panel_declared_row_cap(panel: dict[str, Any]) -> int | None:
    """Return the tightest declared first-screen row cap, if any."""
    caps: list[int] = []
    for target in panel.get("targets") or []:
        if not isinstance(target, dict):
            continue
        expr = target.get("expr")
        if isinstance(expr, str):
            caps.extend(int(match.group(1)) for match in _TOPK_RE.finditer(expr))
        url = target.get("url")
        if isinstance(url, str):
            caps.extend(int(match.group(1)) for match in _LIMIT_RE.finditer(url))
    for transform in panel.get("transformations") or []:
        if not isinstance(transform, dict):
            continue
        transform_id = transform.get("id")
        options = transform.get("options")
        if not isinstance(options, dict):
            continue
        if transform_id == "limit":
            for key in ("limitField", "limit"):
                value = options.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                    caps.append(value)
        if transform_id == "filterByValue" and options.get("type") == "include":
            filters = options.get("filters")
            if isinstance(filters, list) and filters:
                regex_values = []
                equal_count = 0
                for item in filters:
                    if not isinstance(item, dict):
                        continue
                    config = item.get("config")
                    if not isinstance(config, dict):
                        continue
                    config_options = config.get("options")
                    if not isinstance(config_options, dict):
                        continue
                    value = config_options.get("value")
                    if config.get("id") == "regex" and isinstance(value, str):
                        regex_values.append(value)
                    elif config.get("id") == "equal":
                        equal_count += 1
                if equal_count:
                    caps.append(equal_count)
                for pattern in regex_values:
                    alternatives = [
                        part for part in pattern.strip("^$").split("|") if part
                    ]
                    if alternatives:
                        caps.append(len(alternatives))
    return min(caps) if caps else None


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
