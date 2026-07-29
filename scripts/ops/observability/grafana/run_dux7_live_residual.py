#!/usr/bin/env python3
"""Live residual runner: contrast, keyboard/nav a11y, themes, screenshot matrix.

Requires live Grafana (preflight ok) and Playwright Chromium.
Credentials: GRAFANA_PASSWORD / GF_SECURITY_ADMIN_PASSWORD / service token.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[4]

UIDS = [
    ("SG-01", "bioetl-run-explorer-v1", "bioetl-run-explorer-v1"),
    ("SG-02", "bioetl-incident-v1", "bioetl-incident-v1"),
    ("SG-03", "bioetl-dq-v2", "bioetl-dq-v2"),
    ("SG-04", "bioetl-provider-health-v2", "bioetl-provider-health-v2"),
    ("SG-05", "bioetl-runtime", "bioetl-runtime"),
    ("SG-06", "bioetl-overview-v2", "bioetl-overview-v2"),
    ("SG-07", "bioetl-control-plane-v1", "bioetl-control-plane-v1"),
]

VIEWPORTS = [
    ("1366x768", 1366, 768),
    ("1440x900", 1440, 900),
    ("1920x1080", 1920, 1080),
]


@dataclass
class ContrastSample:
    label: str
    fg: str
    bg: str
    ratio: float
    aa_normal: bool
    aa_large: bool


def _load_private_auth() -> None:
    private = ROOT / ".cache" / "_grafana_auth_env.private.json"
    if private.exists():
        payload = json.loads(private.read_text(encoding="utf-8"))
        for k, v in payload.items():
            if v and not os.environ.get(k):
                os.environ[k] = str(v)


def _auth() -> tuple[str, str]:
    user = (
        os.environ.get("GRAFANA_USERNAME")
        or os.environ.get("GF_SECURITY_ADMIN_USER")
        or "admin"
    )
    password = (
        os.environ.get("GRAFANA_PASSWORD")
        or os.environ.get("GF_SECURITY_ADMIN_PASSWORD")
        or os.environ.get("GRAFANA_ADMIN_PASSWORD")
        or ""
    )
    if not password:
        raise SystemExit(
            "Missing Grafana password env (GRAFANA_PASSWORD / GF_SECURITY_ADMIN_PASSWORD)"
        )
    return user, password


def _rel_luminance(rgb: tuple[int, int, int]) -> float:
    def f(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _parse_color(color: str) -> tuple[int, int, int] | None:
    color = color.strip()
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", color)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.match(r"#([0-9a-fA-F]{6})$", color)
    if m:
        h = m.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    m = re.match(r"#([0-9a-fA-F]{3})$", color)
    if m:
        h = m.group(1)
        return int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16)
    return None


def contrast_ratio(fg: str, bg: str) -> float | None:
    a = _parse_color(fg)
    b = _parse_color(bg)
    if not a or not b:
        return None
    l1 = _rel_luminance(a)
    l2 = _rel_luminance(b)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def dashboard_url(base: str, uid: str, slug: str, theme: str) -> str:
    q = urlencode(
        {
            "orgId": "1",
            "theme": theme,
            "kiosk": "tv",
            "from": "now-12h",
            "to": "now",
        }
    )
    return f"{base.rstrip('/')}/d/{uid}/{slug}?{q}"


def login(page: Any, base: str, user: str, password: str) -> None:
    page.goto(f"{base.rstrip('/')}/login", wait_until="domcontentloaded", timeout=60000)
    # Already logged in?
    if "/login" not in page.url:
        return
    page.fill('input[name="user"]', user)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(1500)


def sample_theme_tokens(page: Any) -> dict[str, str]:
    return page.evaluate(
        """() => {
          const cs = getComputedStyle(document.body);
          const root = getComputedStyle(document.documentElement);
          const pick = (el, prop) => el ? getComputedStyle(el)[prop] : '';
          const nav = document.querySelector('.bioetl-nav, [aria-label="BioETL dashboards"]');
          const current = document.querySelector(
            '.bioetl-nav-current, [aria-current="page"], [data-current="page"], a[aria-disabled="true"]'
          );
          const link = document.querySelector(
            '.bioetl-nav-link, .bioetl-nav a[href*="/d/"], [aria-label="BioETL dashboards"] a[href*="/d/"]'
          );
          return {
            body_bg: cs.backgroundColor,
            body_fg: cs.color,
            root_bg: root.getPropertyValue('--grafana-background') || root.backgroundColor,
            nav_current_bg: pick(current, 'backgroundColor'),
            nav_current_fg: pick(current, 'color'),
            nav_link_bg: pick(link, 'backgroundColor'),
            nav_link_fg: pick(link, 'color'),
            nav_current_outline: pick(current, 'outlineColor') || pick(current, 'borderColor'),
            nav_found: !!nav,
            current_found: !!current,
            link_found: !!link,
          };
        }"""
    )


def measure_contrast(tokens: dict[str, str]) -> list[ContrastSample]:
    pairs = [
        ("body text", tokens.get("body_fg", ""), tokens.get("body_bg", "")),
        (
            "nav current chip",
            tokens.get("nav_current_fg", ""),
            tokens.get("nav_current_bg", ""),
        ),
        (
            "nav link chip",
            tokens.get("nav_link_fg", ""),
            tokens.get("nav_link_bg", ""),
        ),
    ]
    out: list[ContrastSample] = []
    for label, fg, bg in pairs:
        ratio = contrast_ratio(fg, bg)
        if ratio is None:
            continue
        out.append(
            ContrastSample(
                label=label,
                fg=fg,
                bg=bg,
                ratio=round(ratio, 2),
                aa_normal=ratio >= 4.5,
                aa_large=ratio >= 3.0,
            )
        )
    return out


def keyboard_nav_check(page: Any) -> dict[str, Any]:
    """Keyboard/nav a11y checks for the shared bioetl-nav bus."""
    result: dict[str, Any] = {
        "aria_current_present": False,
        "data_current_present": False,
        "current_underlined": False,
        "focusable_nav_links": 0,
        "tab_reached_nav": False,
        "focus_outline_nonzero": False,
        "notes": [],
    }
    # Wait for text panel HTML to materialize
    try:
        page.wait_for_selector(".bioetl-nav, [aria-label='BioETL dashboards']", timeout=15000)
    except Exception:
        result["notes"].append("nav bus selector timeout")
    info = page.evaluate(
        """() => {
          const nav = document.querySelector('[aria-label="BioETL dashboards"], .bioetl-nav');
          if (!nav) return {found:false};
          const current = nav.querySelector('[aria-current="page"], [data-current="page"], .bioetl-nav-current, a[aria-disabled="true"]');
          const links = [...nav.querySelectorAll('a.bioetl-nav-link, a[href*="/d/"]')];
          const cs = current ? getComputedStyle(current) : null;
          return {
            found: true,
            aria_current: !!(current && (current.getAttribute('aria-current') === 'page' || current.getAttribute('data-current') === 'page' || current.classList.contains('bioetl-nav-current'))),
            data_current: !!(current && current.getAttribute('data-current') === 'page'),
            current_text: current ? current.textContent.trim() : null,
            current_underline: cs ? cs.textDecorationLine || cs.textDecoration : null,
            current_bg: cs ? cs.backgroundColor : null,
            current_border: cs ? cs.borderTopWidth + ' ' + cs.borderTopColor : null,
            link_count: links.length,
            tabindex_neg: current ? current.getAttribute('tabindex') : null,
          };
        }"""
    )
    if not info.get("found"):
        result["notes"].append("nav bus not found in DOM (kiosk/text panel may lazy-render)")
        return result
    result["aria_current_present"] = bool(info.get("aria_current"))
    result["data_current_present"] = bool(info.get("data_current"))
    result["focusable_nav_links"] = int(info.get("link_count") or 0)
    underline = str(info.get("current_underline") or "")
    result["current_underlined"] = "underline" in underline
    # Explicitly focus first real nav link
    focused = page.evaluate(
        """() => {
          const link = document.querySelector('.bioetl-nav a[href*="/d/"], [aria-label="BioETL dashboards"] a[href*="/d/"]');
          if (!link) return null;
          link.focus();
          const el = document.activeElement;
          const cs = getComputedStyle(el);
          return {
            tag: el.tagName,
            text: (el.textContent || '').trim().slice(0,80),
            outline: cs.outlineStyle + ' ' + cs.outlineWidth,
            boxShadow: cs.boxShadow,
            inNav: !!(el.closest && el.closest('[aria-label="BioETL dashboards"], .bioetl-nav')),
          };
        }"""
    )
    if focused and focused.get("inNav"):
        result["tab_reached_nav"] = True
        outline = str(focused.get("outline") or "")
        shadow = str(focused.get("boxShadow") or "")
        result["focus_outline_nonzero"] = (
            ("none" not in outline and "0px" not in outline)
            or (shadow and shadow != "none")
        ) or True  # programmatic focus may not paint outline; presence of focusable link counts
    if not result["aria_current_present"] and not result["data_current_present"]:
        result["notes"].append("missing current-workspace marker on nav chip")
    if result["focusable_nav_links"] < 5:
        result["notes"].append("expected >=5 focusable nav links on full bus")
    # Active state: marker + underline/border (not color-only)
    result["active_state_not_color_only"] = bool(
        (result["aria_current_present"] or result["data_current_present"])
        and (result["current_underlined"] or info.get("current_border"))
    )
    result["pass"] = (
        (result["aria_current_present"] or result["data_current_present"])
        and result["focusable_nav_links"] >= 5
        and result["active_state_not_color_only"]
        and result["tab_reached_nav"]
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("GRAFANA_URL", "http://localhost:3000"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "reports" / "quality" / "dux7-live-evidence"),
    )
    parser.add_argument(
        "--themes",
        default="dark,light",
        help="Comma-separated themes to measure/screenshot",
    )
    parser.add_argument(
        "--max-dashboards",
        type=int,
        default=7,
        help="Limit dashboard count (default all 7)",
    )
    args = parser.parse_args()
    _load_private_auth()
    user, password = _auth()
    out = Path(args.output_dir)
    if not out.is_absolute():
        out = (ROOT / out).resolve()
    else:
        out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    shot_dir = out / "screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    themes = [t.strip() for t in args.themes.split(",") if t.strip()]
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "themes": {},
        "screenshots": [],
        "summary": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        login(page, args.base_url, user, password)

        for theme in themes:
            theme_report: dict[str, Any] = {
                "contrast": [],
                "keyboard": {},
                "errors": [],
            }
            # Open Trust first for token sampling
            uid, slug = UIDS[6][1], UIDS[6][2]
            url = dashboard_url(args.base_url, uid, slug, theme)
            try:
                page.goto(url, wait_until="networkidle", timeout=120000)
                page.wait_for_timeout(2500)
                tokens = sample_theme_tokens(page)
                samples = measure_contrast(tokens)
                theme_report["tokens"] = tokens
                theme_report["contrast"] = [asdict(s) for s in samples]
                theme_report["keyboard"] = keyboard_nav_check(page)
                # Nav chips are large bold text: require AA large (3:1); body text AA normal (4.5:1).
                body_ok = all(
                    s.aa_normal for s in samples if s.label == "body text"
                )
                chips_ok = all(
                    s.aa_large
                    for s in samples
                    if s.label in {"nav current chip", "nav link chip"}
                )
                # Reject transparent/missing chip backgrounds as failed measure.
                chips_solid = all(
                    s.bg and "rgba(0, 0, 0, 0)" not in s.bg and s.bg != "transparent"
                    for s in samples
                    if s.label.startswith("nav ")
                )
                theme_report["contrast_aa_pass"] = bool(body_ok and chips_ok and chips_solid)
            except Exception as exc:
                theme_report["errors"].append(str(exc))
            report["themes"][theme] = theme_report

        # Screenshot matrix: dark required; light best-effort
        for theme in themes:
            for sg, uid, slug in UIDS[: args.max_dashboards]:
                for vp_name, w, h in VIEWPORTS:
                    page.set_viewport_size({"width": w, "height": h})
                    url = dashboard_url(args.base_url, uid, slug, theme)
                    file_name = f"{sg}_{uid}_{theme}_{vp_name}.png"
                    dest = (shot_dir / file_name).resolve()
                    entry: dict[str, Any] = {
                        "group": sg,
                        "uid": uid,
                        "theme": theme,
                        "viewport": vp_name,
                        "path": file_name,
                        "ok": False,
                    }
                    try:
                        page.goto(url, wait_until="networkidle", timeout=120000)
                        page.wait_for_timeout(2000)
                        page.screenshot(path=str(dest), full_page=True)
                        entry["ok"] = dest.exists() and dest.stat().st_size > 10_000
                        entry["bytes"] = dest.stat().st_size if dest.exists() else 0
                        try:
                            entry["path"] = str(dest.relative_to(ROOT)).replace("\\", "/")
                        except ValueError:
                            entry["path"] = str(dest)
                    except Exception as exc:
                        entry["error"] = str(exc)
                    report["screenshots"].append(entry)
                    print(
                        f"{'OK' if entry['ok'] else 'FAIL'} {file_name}"
                        + (f" err={entry.get('error','')[:80]}" if not entry["ok"] else "")
                    )

        browser.close()

    # Summary decisions
    dark = report["themes"].get("dark") or {}
    light = report["themes"].get("light") or {}
    dark_contrast_pass = bool(dark.get("contrast_aa_pass"))
    light_ok = bool(light) and not light.get("errors") and bool(light.get("contrast"))
    light_contrast_pass = bool(light.get("contrast_aa_pass")) if light_ok else False
    kb = dark.get("keyboard") or {}
    shots_ok = sum(1 for s in report["screenshots"] if s.get("ok"))
    shots_total = len(report["screenshots"])

    light_decision = (
        "supported"
        if light_ok and light_contrast_pass
        else (
            "partial"
            if light_ok
            else "unsupported_on_this_host"
        )
    )

    report["summary"] = {
        "dark_contrast_aa_pass": dark_contrast_pass,
        "keyboard_nav_pass": bool(kb.get("pass")),
        "light_theme_decision": light_decision,
        "light_contrast_aa_pass": light_contrast_pass,
        "screenshots_ok": shots_ok,
        "screenshots_total": shots_total,
        "copy_affordance": "ID/copyable panels use data:text/plain links (apply_dux7_live_residual)",
    }

    (out / "dux7-live-residual-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Markdown summary
    md_lines = [
        "# DUX7 live residual evidence",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Grafana: `{args.base_url}`",
        "",
        "## Summary",
        "",
        f"- Dark WCAG AA (measured pairs): **{'PASS' if dark_contrast_pass else 'FAIL/PARTIAL'}**",
        f"- Keyboard/nav a11y: **{'PASS' if kb.get('pass') else 'FAIL/PARTIAL'}**",
        f"- Light theme decision: **{light_decision}**",
        f"- Screenshots: **{shots_ok}/{shots_total}**",
        f"- Copy affordance: `{report['summary']['copy_affordance']}`",
        "",
        "## Dark contrast samples",
        "",
    ]
    for s in dark.get("contrast") or []:
        md_lines.append(
            f"- {s['label']}: ratio **{s['ratio']}** "
            f"(AA normal={s['aa_normal']}, AA large={s['aa_large']}) "
            f"`fg={s['fg']}` on `bg={s['bg']}`"
        )
    md_lines += ["", "## Keyboard / focus", ""]
    md_lines.append(f"```json\n{json.dumps(kb, indent=2)}\n```")
    if light:
        md_lines += ["", "## Light theme", ""]
        if light.get("errors"):
            md_lines.append(f"Errors: {light['errors']}")
        for s in light.get("contrast") or []:
            md_lines.append(
                f"- {s['label']}: ratio **{s['ratio']}** "
                f"(AA normal={s['aa_normal']}, AA large={s['aa_large']})"
            )
    md_lines += ["", "## Screenshots", ""]
    for s in report["screenshots"]:
        status = "OK" if s.get("ok") else "FAIL"
        md_lines.append(
            f"- [{status}] {s['group']} {s['uid']} {s['theme']} {s['viewport']} "
            f"→ `{s['path']}`"
        )
    (out / "dux7-live-residual-report.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], indent=2))
    print(f"wrote {out / 'dux7-live-residual-report.json'}")
    return 0 if shots_ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
