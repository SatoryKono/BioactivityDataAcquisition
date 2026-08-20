# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Deterministic Run Explorer request snapshots (V5 R-C).

No secrets, no absolute hosts. Lives under tests/ so scripts/ active-count
does not grow. Invoke: python -m tests.integration._run_explorer_request_fixtures
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

CONTRACT = "run_explorer_request_snapshot_v1"
CATALOG_PATH = Path(
    "docs/03-guides/dashboards/contracts/run-explorer-http-catalog.yaml"
)
DEFAULT_OUT = Path("tests/fixtures/grafana/run_explorer")
FIRST_SCREEN_IDS = (3010, 9402)
_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::csv)?\}")

SELECTED = {
    "workflow": "chembl_baseline",
    "pipeline": "chembl_assay",
    "run_type": "backfill",
    "run_id": "00000000-0000-4000-8000-000000000942",
}
EMPTY_SELECTION = {
    **SELECTED,
    "run_id": "-",
}


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"catalog must be a mapping: {path}")
    return payload


def materialize_ops_url(template: str, selectors: dict[str, str]) -> str:
    """Expand Grafana ${var} / ${var:csv} into a host-free Ops path."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in selectors:
            raise KeyError(f"selector {key!r} missing for {template}")
        return selectors[key]

    url = _VAR_RE.sub(_replace, template)
    if "$" in url:
        raise ValueError(f"unexpanded selector remains in {url}")
    if url.startswith(("http://", "https://", "//")):
        raise ValueError(f"absolute host is forbidden: {url}")
    if not url.startswith("/ops/"):
        raise ValueError(f"Ops path required: {url}")
    return url


def _panel_by_id(catalog: dict[str, Any], panel_id: int) -> dict[str, Any]:
    for entry in catalog["panels"]:
        if int(entry["id"]) == panel_id:
            return entry
    raise KeyError(f"catalog missing panel {panel_id}")


def _snapshot(
    *,
    scenario: str,
    panel: dict[str, Any],
    selectors: dict[str, str],
    response_state: str,
) -> dict[str, Any]:
    url = materialize_ops_url(str(panel["url"]), selectors)
    return {
        "contract": CONTRACT,
        "scenario": scenario,
        "panel_id": int(panel["id"]),
        "title": panel["title"],
        "endpoint": panel["endpoint"],
        "method": "GET",
        "url": url,
        "url_template": panel["url"],
        "root_selector": panel["root_selector"],
        "selectors": dict(selectors),
        "expected_empty_copy_tokens": list(panel["no_value_tokens"]),
        "response_state": response_state,
    }


def build_matrix(catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    catalog = catalog or load_catalog()
    browse = _panel_by_id(catalog, 3010)
    identity = _panel_by_id(catalog, 9402)
    records = _panel_by_id(catalog, 9403)
    scenarios = {
        "selected_recent_runs": _snapshot(
            scenario="selected_recent_runs",
            panel=browse,
            selectors=SELECTED,
            response_state="ok",
        ),
        "selected_identity": _snapshot(
            scenario="selected_identity",
            panel=identity,
            selectors=SELECTED,
            response_state="ok",
        ),
        "selected_processed_records": _snapshot(
            scenario="selected_processed_records",
            panel=records,
            selectors=SELECTED,
            response_state="ok",
        ),
        "empty_selection": _snapshot(
            scenario="empty_selection",
            panel=identity,
            selectors=EMPTY_SELECTION,
            response_state="select_run",
        ),
        "valid_empty": _snapshot(
            scenario="valid_empty",
            panel=browse,
            selectors=SELECTED,
            response_state="valid_empty",
        ),
        "backend_error": _snapshot(
            scenario="backend_error",
            panel=records,
            selectors=SELECTED,
            response_state="query_error",
        ),
    }
    return {
        "contract": CONTRACT,
        "catalog_path": CATALOG_PATH.as_posix(),
        "dashboard_uid": catalog["dashboard_uid"],
        "first_screen_panel_ids": list(FIRST_SCREEN_IDS),
        "scenarios": {
            name: {"path": f"{name}.json", "panel_id": payload["panel_id"]}
            for name, payload in scenarios.items()
        },
        "payloads": scenarios,
    }


def write_matrix(out: Path = DEFAULT_OUT) -> dict[str, Any]:
    matrix = build_matrix()
    out.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, Any] = matrix.pop("payloads")
    for name, payload in payloads.items():
        target = out / f"{name}.json"
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    index_path = out / "INDEX.json"
    index_path.write_text(
        json.dumps(matrix, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    matrix["payloads"] = payloads
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    write_matrix(args.output_dir)
    print(f"INDEX -> {args.output_dir / 'INDEX.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
