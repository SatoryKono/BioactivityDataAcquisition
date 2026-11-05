import subprocess
import time
import json
import os
import re
import hashlib
from typing import Any


def normalize_diagnostics(output: str) -> list[str]:
    """Normalize mypy diagnostics for comparison, ignoring line numbers and times."""
    lines = output.splitlines()
    normalized = []
    for line in lines:
        if line.startswith("Success:") or line.startswith("Found "):
            continue
        # Remove line/column numbers
        line = re.sub(r":\d+(:\d+)?:", ":", line)
        normalized.append(line.strip())
    return sorted(normalized)


def hash_directory_content(directory: str) -> str:
    """Creates a basic content manifest hash for a directory."""
    if not os.path.exists(directory):
        return "not_found"

    hasher = hashlib.sha256()
    for root, _, files in sorted(os.walk(directory)):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            # Hash path
            hasher.update(filepath.encode())
            # Hash file content
            try:
                with open(filepath, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                pass
    return hasher.hexdigest()


def run_mypy(cache_dir: str, iteration: str) -> dict[str, Any]:
    start = time.time()

    # We use strict and precise flags per instructions
    cmd = [
        "uv",
        "run",
        "--frozen",
        "--no-sync",
        "mypy",
        "--strict",
        "--cache-dir",
        cache_dir,
        "src/bioetl",
    ]
    if os.path.exists("src/memory"):
        cmd.append("src/memory")

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
        stdout_data = e.stdout.decode("utf-8") if e.stdout else ""
        stderr_data = e.stderr.decode("utf-8") if e.stderr else ""
        returncode = -1
        print(f"[{iteration}] Mypy run timed out after {timeout_seconds} seconds")

    # Save raw stdout to analyze cache hits or failures
    with open(f"reports/mypy_run_{iteration}.log", "w") as f:
        f.write(stdout_data)
        f.write("\n")
        f.write(stderr_data)

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
        "diagnostics_hash": hash(tuple(normalized)),
        "cache_manifest": cache_manifest,
    }


def main() -> None:
    os.makedirs("reports", exist_ok=True)
    cache_dir = ".mypy_cache_eval2"

    subprocess.run(["rm", "-rf", cache_dir])

    print("Running cold mypy...")
    cold_result = run_mypy(cache_dir, "cold")

    print("Running warm mypy...")
    warm_result = run_mypy(cache_dir, "warm")

    # Compare
    diagnostics_match = (
        cold_result["diagnostics_hash"] == warm_result["diagnostics_hash"]
    )

    data = {
        "cold": cold_result,
        "warm": warm_result,
        "comparison": {
            "diagnostics_match": diagnostics_match,
            "cold_time": cold_result["time_s"],
            "warm_time": warm_result["time_s"],
            "speedup": cold_result["time_s"] / max(warm_result["time_s"], 0.1),
        },
    }

    with open("reports/mypy_eval.json", "w") as f:
        json.dump(data, f, indent=2)

    print("Mypy evaluation done.")


if __name__ == "__main__":
    main()
