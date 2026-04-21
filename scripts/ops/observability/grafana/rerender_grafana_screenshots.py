"""Rerender Grafana dashboard screenshots through the Grafana render API."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:3000"
SEARCH_URL = f"{BASE_URL}/api/search?type=dash-db"
OUTPUT_DIR = Path("reports/observability/grafana/screenshots")
WIDTH = 1600
HEIGHT = 2200


def _auth_header(username: str = "admin", secret_value: str = "admin") -> str:
    token = base64.b64encode(f"{username}:{secret_value}".encode()).decode("ascii")
    return f"Basic {token}"


def _fetch_json(url: str) -> object:
    request = Request(url, headers={"Authorization": _auth_header()})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_binary(url: str) -> bytes:
    request = Request(url, headers={"Authorization": _auth_header()})
    with urlopen(request, timeout=120) as response:
        return response.read()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dashboards = _fetch_json(SEARCH_URL)
    if not isinstance(dashboards, list):
        raise RuntimeError("Grafana search API returned unexpected payload")

    dashboard_items = cast(list[object], dashboards)
    for item in dashboard_items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        uid = item.get("uid")
        if not isinstance(url, str) or not isinstance(uid, str):
            continue

        render_path = "/render" + url
        query = urlencode({"width": WIDTH, "height": HEIGHT, "tz": "UTC"})
        render_url = f"{BASE_URL}{render_path}?{query}"
        target = OUTPUT_DIR / f"{uid}.png"
        print(f"Rendering {uid} -> {target}")
        try:
            target.write_bytes(_download_binary(render_url))
        except HTTPError as exc:
            print(f"HTTP error for {uid}: {exc.code} {exc.reason}")
            return 1
        except URLError as exc:
            print(f"URL error for {uid}: {exc.reason}")
            return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
