from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

STRICT_TYPE_GATE_TARGETS = ("src/bioetl", "src/memory", "scripts/engineering/quality")
MYPY_COMMAND = (
    "uv",
    "run",
    "--frozen",
    "--no-build",
    "--no-sync",
    "mypy",
    "--config-file",
    "pyproject.toml",
    "--incremental",
    "--strict",
)


def normalize_diagnostics(output: str) -> list[str]:
    """Normalize mypy diagnostics for comparison, ignoring line numbers and times."""
    lines = output.splitlines()
    normalized = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Success:") or stripped.startswith("Found "):
            continue
        # Override-section notes drift between cold/warm incremental runs and
        # are not type errors; drop them from the equality digest.
        if "note: unused section(s):" in stripped:
            continue
        # Remove line/column numbers
        stripped = re.sub(r":\d+(:\d+)?:", ":", stripped)
        normalized.append(stripped)
    return sorted(normalized)


def diagnostics_digest(normalized: list[str]) -> str:
    """Stable SHA-256 over a canonical serialization of normalized diagnostics."""
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_directory_content(directory: str) -> str:
    """Creates a basic content manifest hash for a directory."""
    if not os.path.exists(directory):
        return "not_found"

    hasher = hashlib.sha256()
    for root, _, files in sorted(os.walk(directory)):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            # Hash path
            hasher.update(Path(filepath).relative_to(directory).as_posix().encode())
            # Hash file content
            try:
                with open(filepath, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                pass
    return hasher.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _timeout_text(output: bytes | str | None) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output or ""


def run_mypy(cache_dir: str, iteration: str) -> dict[str, Any]:
    """Run strict mypy and record diagnostics, timing, and cache contents."""
    start = time.time()

    # Explicit --incremental overrides pyproject `incremental = false` so the
    # cold/warm pair actually exercises mypy's module cache for this experiment
    # without changing the protective type-gate setting.
    cmd = [*MYPY_COMMAND, "--cache-dir", cache_dir, *STRICT_TYPE_GATE_TARGETS]

    timeout_seconds = 180
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds
        )
        end = time.time()
        stdout_data = result.stdout
        stderr_data = result.stderr
        returncode = result.returncode
    except subprocess.TimeoutExpired as e:
        end = time.time()
        stdout_data = _timeout_text(e.stdout)
        stderr_data = _timeout_text(e.stderr)
        returncode = -1
        print(f"[{iteration}] Mypy run timed out after {timeout_seconds} seconds")

    # Save raw stdout to analyze cache hits or failures
    _atomic_write_text(
        Path(f"reports/mypy_run_{iteration}.log"),
        stdout_data + "\n" + stderr_data,
    )

    normalized = normalize_diagnostics(stdout_data + "\n" + stderr_data)

    # Generate content manifest for cache
    cache_manifest = hash_directory_content(cache_dir)

    return {
        "iteration": iteration,
        "time_s": end - start,
        "returncode": returncode,
        "stdout_lines": len(stdout_data.splitlines()),
        "stderr_lines": len(stderr_data.splitlines()),
        "normalized_diagnostics": normalized,
        "diagnostics_hash": diagnostics_digest(normalized),
        "cache_manifest": cache_manifest,
    }


def main() -> None:
    """Measure a cold and warm mypy run with one fresh, isolated cache."""
    os.makedirs("reports", exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="bioetl-mypy-eval-") as cache_dir:
        print("Running cold mypy...")
        cold_result = run_mypy(cache_dir, "cold")
        print("Running warm mypy...")
        warm_result = run_mypy(cache_dir, "warm")

    # Compare
    diagnostics_match = (
        cold_result["diagnostics_hash"] == warm_result["diagnostics_hash"]
    )

    data = {
        "producer": "local",
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "command": [
            *MYPY_COMMAND,
            "--cache-dir",
            "<temporary-cache>",
            *STRICT_TYPE_GATE_TARGETS,
        ],
        "cache_state": {
            "cold": "empty",
            "warm": "reused locally",
            "remote_restore": "not measured",
        },
        "targets": STRICT_TYPE_GATE_TARGETS,
        "cold": cold_result,
        "warm": warm_result,
        "comparison": {
            "diagnostics_match": diagnostics_match,
            "cold_time": cold_result["time_s"],
            "warm_time": warm_result["time_s"],
            "speedup": cold_result["time_s"] / max(warm_result["time_s"], 0.1),
        },
    }

    _atomic_write_text(
        Path("reports/mypy_eval.json"),
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
    )

    print("Mypy evaluation done.")


if __name__ == "__main__":
    main()
