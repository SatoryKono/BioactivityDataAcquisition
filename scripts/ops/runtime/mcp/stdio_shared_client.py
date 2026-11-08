"""Transport-only Windows/WSL client of the fixed shared Context7 owner."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    if sys.argv[1:] != ["context7"]:
        raise RuntimeError("Specify the reviewed shared service")
    if os.name == "nt":
        node = Path("C:/Program Files/nodejs/node.exe")
    elif os.environ.get("WSL_INTEROP"):
        node = Path("/mnt/c/Program Files/nodejs/node.exe")
    else:
        raise RuntimeError("This local shared profile requires Windows or WSL interop; no fallback backend")
    if not node.is_file():
        raise RuntimeError("Windows transport adapter unavailable; no fallback backend")
    return subprocess.call([str(node), "D:/pc-agent/tools/shared-mcp/service-adapter.mjs", "context7"],
        stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


if __name__ == "__main__":
    try: sys.exit(main())
    except Exception:
        sys.stderr.write("Shared Context7 client unavailable; no private backend was started.\n")
        sys.exit(1)
