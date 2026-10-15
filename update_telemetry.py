import subprocess
import json

out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
sha = out.stdout.strip()
print(f"HEAD is {sha}")

out = subprocess.run([
    "uv", "run", "python", "-m", "scripts.engineering.ci.update_test_telemetry_baseline",
    "--source-commit", sha,
    "--source-run-id", "0"
], capture_output=True, text=True)
print(out.stdout)
print(out.stderr)
