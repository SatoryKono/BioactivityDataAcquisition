"""Probe Ops HTTP URLs referenced by Grafana dashboard panels."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = "http://127.0.0.1:8000"


def walk(panels: list | None):
    for panel in panels or []:
        if panel.get("type") == "row":
            yield from walk(panel.get("panels"))
            continue
        yield panel
        yield from walk(panel.get("panels"))


def resolve(url: str) -> str:
    out = url
    for token, value in {
        "${pipeline}": "chembl_activity",
        "${run_type:csv}": "backfill",
        "${run_type}": "backfill",
        "${run_id}": "-",
        "${workflow}": "all",
        "${provider}": "chembl",
        "${stage}": "unknown",
    }.items():
        out = out.replace(token, value)
    return out


def main() -> None:
    results: list[dict] = []
    for path in sorted((ROOT / "grafana" / "dashboards").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for panel in walk(data.get("panels")):
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                url = target.get("url")
                if not isinstance(url, str) or not url.startswith("/"):
                    continue
                full = BASE + resolve(url)
                status = None
                detail = ""
                try:
                    with urllib.request.urlopen(full, timeout=12) as resp:
                        status = resp.status
                        detail = resp.read(60).decode("utf-8", errors="replace")
                except urllib.error.HTTPError as exc:
                    status = exc.code
                    detail = exc.reason
                except Exception as exc:  # noqa: BLE001
                    status = "ERR"
                    detail = str(exc)
                item = {
                    "dash": path.name,
                    "id": panel.get("id"),
                    "title": panel.get("title"),
                    "url": url,
                    "resolved": resolve(url),
                    "status": status,
                    "detail": detail[:80],
                }
                results.append(item)
                flag = "OK" if status in (200, 204) else "BAD"
                print(
                    flag,
                    path.name,
                    panel.get("id"),
                    panel.get("title"),
                    status,
                    resolve(url)[:100],
                )

    bad = [r for r in results if r["status"] not in (200, 204)]
    out = (
        ROOT
        / "reports"
        / "observability"
        / "grafana-3cycle-20260805-r2"
        / "iteration-02"
        / "query-results"
        / "ops-http-probe.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"total": len(results), "bad": bad, "all": results}, indent=2),
        encoding="utf-8",
    )
    print("total", len(results), "bad", len(bad))


if __name__ == "__main__":
    main()
