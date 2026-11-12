"""Derive the opt-in responsive profile without changing the accepted native one."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from scripts.ops.observability.grafana._adaptive_tables import apply_adaptive_tables

ROOT = Path(__file__).resolve().parents[4]


def normalized_hash(path: Path) -> str:
    """Keep generated provenance stable across LF/CRLF checkouts."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()


def generate(root: Path = ROOT, *, check: bool = False) -> bool:
    """Retain all queries/fields and write only the fixed adaptive output tree."""
    root = root.resolve()
    destination = root / "grafana/dashboards-adaptive"
    if not destination.resolve().is_relative_to(root):
        raise ValueError("Adaptive dashboard output escapes the checkout")
    inputs = sorted((root / "grafana/dashboards").glob("*.json"))
    if len(inputs) != 5:
        raise ValueError("Expected exactly five native dashboard sources")
    provenance = {
        "profile": "adaptive",
        "inputs_sha256_lf": {},
        "outputs_sha256_lf": {},
    }
    ok = True
    if not check:
        destination.mkdir(parents=True, exist_ok=True)
    for source in inputs:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if source.name != f"{payload['uid']}.json":
            raise ValueError("Dashboard filename must match its UID")
        derived = deepcopy(payload)
        apply_adaptive_tables(derived)
        serialized = json.dumps(derived, ensure_ascii=False, indent=2) + "\n"
        target = destination / source.name
        provenance["inputs_sha256_lf"][source.relative_to(root).as_posix()] = (
            normalized_hash(source)
        )
        provenance["outputs_sha256_lf"][target.relative_to(root).as_posix()] = (
            hashlib.sha256(serialized.encode()).hexdigest()
        )
        if check:
            ok &= target.is_file() and target.read_text(encoding="utf-8") == serialized
        else:
            target.write_text(serialized, encoding="utf-8", newline="\n")
    manifest = root / "grafana/adaptive-profile.json"
    provider_source = root / "grafana/provisioning/dashboards/bioetl.yaml"
    provider_target = root / "grafana/provisioning/dashboards-adaptive/bioetl.yaml"
    provider = provider_source.read_text(encoding="utf-8").replace(
        "/var/lib/grafana/dashboards/", "/var/lib/grafana/dashboards-adaptive/"
    )
    provenance["inputs_sha256_lf"][provider_source.relative_to(root).as_posix()] = (
        normalized_hash(provider_source)
    )
    provenance["outputs_sha256_lf"][provider_target.relative_to(root).as_posix()] = (
        hashlib.sha256(provider.encode()).hexdigest()
    )
    if check:
        ok &= (
            provider_target.is_file()
            and provider_target.read_text(encoding="utf-8") == provider
        )
    else:
        provider_target.parent.mkdir(parents=True, exist_ok=True)
        provider_target.write_text(provider, encoding="utf-8", newline="\n")
    serialized = json.dumps(provenance, ensure_ascii=False, indent=2) + "\n"
    if check:
        ok &= manifest.is_file() and manifest.read_text(encoding="utf-8") == serialized
    else:
        manifest.write_text(serialized, encoding="utf-8", newline="\n")
    return bool(ok)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return 0 if generate(check=args.check) else 1


if __name__ == "__main__":
    raise SystemExit(main())
