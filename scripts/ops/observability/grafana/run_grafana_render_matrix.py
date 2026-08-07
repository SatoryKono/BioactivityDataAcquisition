"""Run the canonical multi-viewport Grafana browser-render evidence matrix."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.engineering.common.repo_paths import resolve_output_path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[4]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_text
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender,
)

DEFAULT_OUTPUT_DIR = Path("reports/observability/grafana/render-matrix")
STANDARD_VIEWPORTS = ((1366, 768), (1440, 900), (1920, 1080))
KIOSK_VIEWPORTS = ((2560, 1440), (3840, 2160))
THEMES = ("dark", "light")


@dataclass(frozen=True)
class RenderProfile:
    name: str
    width: int
    height: int
    theme: str
    capture_surface: str = "viewport"
    kiosk_mode: str = "off"
    expand_collapsed_rows: bool = False


def build_profiles(*, include_kiosk: bool = True) -> tuple[RenderProfile, ...]:
    """Return the required standard, full-surface, kiosk, and repeat groups."""
    profiles = [
        RenderProfile(
            name=f"{width}x{height}-{theme}",
            width=width,
            height=height,
            theme=theme,
        )
        for width, height in STANDARD_VIEWPORTS
        for theme in THEMES
    ]
    profiles.append(
        RenderProfile(
            name="1440x900-dark-full",
            width=1440,
            height=900,
            theme="dark",
            capture_surface="full",
            expand_collapsed_rows=True,
        )
    )
    profiles.append(
        RenderProfile(
            name="1440x900-dark-repeat",
            width=1440,
            height=900,
            theme="dark",
        )
    )
    if include_kiosk:
        profiles.extend(
            RenderProfile(
                name=f"{width}x{height}-{theme}-kiosk",
                width=width,
                height=height,
                theme=theme,
                kiosk_mode="full",
            )
            for width, height in KIOSK_VIEWPORTS
            for theme in THEMES
        )
    return tuple(profiles)


def _profile_argv(
    profile: RenderProfile,
    *,
    output_dir: Path,
    timeout_seconds: float,
    uids: tuple[str, ...],
) -> list[str]:
    argv = [
        "--output-dir",
        str(output_dir / profile.name),
        "--width",
        str(profile.width),
        "--height",
        str(profile.height),
        "--theme",
        profile.theme,
        "--fallback",
        "playwright",
        "--timeout-seconds",
        str(timeout_seconds),
        "--capture-surface",
        profile.capture_surface,
        "--kiosk-mode",
        profile.kiosk_mode,
        "--browser-zoom",
        "100",
    ]
    argv.append(
        "--expand-collapsed-rows"
        if profile.expand_collapsed_rows
        else "--no-expand-collapsed-rows"
    )
    if uids:
        argv.extend(["--uids", *uids])
    return argv


def _read_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return payload


def _geometry_by_uid(manifest: dict[str, object]) -> dict[str, object]:
    dashboards = manifest.get("dashboards")
    if not isinstance(dashboards, list):
        return {}
    return {
        str(item["uid"]): item.get("layoutGeometry")
        for item in dashboards
        if isinstance(item, dict) and isinstance(item.get("uid"), str)
    }


def compare_repeat_geometry(
    baseline: dict[str, object], repeat: dict[str, object]
) -> dict[str, object]:
    """Compare stable layout geometry while ignoring live panel values."""
    baseline_geometry = _geometry_by_uid(baseline)
    repeat_geometry = _geometry_by_uid(repeat)
    differences: list[str] = []
    for uid in sorted(set(baseline_geometry) | set(repeat_geometry)):
        if baseline_geometry.get(uid) != repeat_geometry.get(uid):
            differences.append(uid)
    return {
        "status": "ok" if not differences else "error",
        "baseline_group": "1440x900-dark",
        "repeat_group": "1440x900-dark-repeat",
        "different_dashboard_uids": differences,
        "comparison": "exact stable geometry; live values excluded",
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--uids", nargs="*", default=())
    parser.add_argument(
        "--include-kiosk",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = resolve_output_path(Path(args.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    profiles = build_profiles(include_kiosk=bool(args.include_kiosk))
    results: list[dict[str, object]] = []

    for profile in profiles:
        code = rerender.main(
            _profile_argv(
                profile,
                output_dir=output_dir,
                timeout_seconds=float(args.timeout_seconds),
                uids=tuple(str(uid) for uid in args.uids),
            )
        )
        manifest_path = output_dir / profile.name / "render-manifest.json"
        results.append(
            {
                "name": profile.name,
                "exit_code": code,
                "manifest": str(manifest_path),
            }
        )
        if code != 0:
            break

    consistency: dict[str, object] = {
        "status": "not-checked",
        "reason": "required repeat groups did not both complete",
    }
    baseline_path = output_dir / "1440x900-dark" / "render-manifest.json"
    repeat_path = output_dir / "1440x900-dark-repeat" / "render-manifest.json"
    if baseline_path.exists() and repeat_path.exists():
        consistency = compare_repeat_geometry(
            _read_manifest(baseline_path),
            _read_manifest(repeat_path),
        )

    status = (
        "ok"
        if len(results) == len(profiles)
        and all(item["exit_code"] == 0 for item in results)
        and consistency.get("status") == "ok"
        else "error"
    )
    matrix_manifest = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": status,
        "profiles": results,
        "consistency": consistency,
        "backend_applicability": {
            "quarantine_explorer": {
                "state": "NOT_APPLICABLE",
                "reason": "Quarantine Explorer HTTP/UI surface is retired from shipping.",
            }
        },
    }
    atomic_write_text(
        output_dir / "matrix-manifest.json",
        json.dumps(matrix_manifest, indent=2) + "\n",
    )
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
