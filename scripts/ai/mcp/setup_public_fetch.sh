#!/usr/bin/env bash
# Isolated, hash-locked public-fetch-v1 runtime for Linux orbs only.
set -euo pipefail
umask 077
[[ "$HOME" == /* && "$HOME" != / ]] || { echo 'public-fetch: physical home required' >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo 'public-fetch: Linux is required' >&2; exit 64; }
case "$(uname -m)" in x86_64|aarch64|arm64) ;; *) echo 'public-fetch: unsupported architecture' >&2; exit 64 ;; esac
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
requirements="$SCRIPT_DIR/support/public-fetch-requirements.txt"
fingerprint="$(sha256sum "$requirements")"
fingerprint="${fingerprint%% *}"
runtime="$HOME/.local/share/bioetl/public-fetch-v1/$fingerprint"
ancestor="$runtime"
while [[ ! -e "$ancestor" && ! -L "$ancestor" ]]; do ancestor="$(dirname -- "$ancestor")"; done
[[ ! -L "$ancestor" && "$(realpath -e -- "$ancestor")" == "$ancestor" ]] || {
  echo 'public-fetch: linked runtime ancestor refused' >&2; exit 1;
}
mkdir -p -- "$(dirname -- "$runtime")"
[[ ! -L "$runtime" ]] || { echo 'public-fetch: linked runtime refused' >&2; exit 1; }
uv venv --python 3.13 --allow-existing "$runtime"
uv pip sync --python "$runtime/bin/python" --require-hashes --only-binary :all: --link-mode copy "$requirements"
