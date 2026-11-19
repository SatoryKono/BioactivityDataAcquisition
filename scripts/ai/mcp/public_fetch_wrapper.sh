#!/usr/bin/env bash
# Keep the registered Windows Fetch owner on its existing independent path.
set -euo pipefail
[[ "$(uname -s)" == Linux ]] || { echo 'public-fetch: Linux is required' >&2; exit 64; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fingerprint="$(sha256sum "$SCRIPT_DIR/support/public-fetch-requirements.txt")"
fingerprint="${fingerprint%% *}"
runtime="$HOME/.local/share/bioetl/public-fetch-v1/$fingerprint"
[[ -x "$runtime/bin/python" && "$(realpath -e -- "$runtime")" == "$runtime" ]] || {
  echo 'public-fetch: run the approved Linux setup first' >&2; exit 1;
}
exec env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 \
  "$runtime/bin/python" -I -S -B "$SCRIPT_DIR/support/public_fetch_stdio.py"
