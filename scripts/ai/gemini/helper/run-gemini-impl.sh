#!/usr/bin/env bash
# Helper: Launch Gemini
# Called by: run-gemini.sh/run-gemini.ps1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2}"

# Load environment
ENV_FILE="${ROOT_DIR}/.env.gemini"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

# Load proxy if available
if [[ -f "${REPO_ROOT}/.wsl_proxy_env.sh" ]]; then
    source "${REPO_ROOT}/.wsl_proxy_env.sh" 2>/dev/null || true
fi

# Verify API key
if [[ -z "${GEMINI_API_KEY:-}" ]] || [[ "${GEMINI_API_KEY}" == "your-api-key-here" ]]; then
    echo "[ERROR] GEMINI_API_KEY not set or invalid in ${ENV_FILE}" >&2
    echo "[INFO] Please edit .env.gemini and add your API key from: https://aistudio.google.com/app/apikeys" >&2
    exit 1
fi

# Verify Python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found" >&2
    echo "[INFO] Install with: sudo apt-get install python3 python3-pip" >&2
    exit 1
fi

# Try to find Python with google-generativeai
PYTHON_BIN="python3"

# Check if venv exists and use it
VENV_DIR="${HOME}/.cache/tools/gemini-venv"
if [[ -f "${VENV_DIR}/bin/python" ]]; then
    PYTHON_BIN="${VENV_DIR}/bin/python"
fi

# Verify google-generativeai package
if ! "${PYTHON_BIN}" -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('google.genai') or importlib.util.find_spec('google.generativeai') else 1)" 2>/dev/null; then
    echo "[ERROR] Gemini Python SDK not installed" >&2
    echo "[INFO] Run setup: run-gemini.ps1 setup" >&2
    exit 1
fi

# Export API key for Python
export GEMINI_API_KEY
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"

# Create temporary Python file to run Gemini
GEMINI_SCRIPT=$(mktemp)
trap 'rm -f "${GEMINI_SCRIPT}"' EXIT

cat > "${GEMINI_SCRIPT}" <<'PYEOF'
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY not set")
    sys.exit(1)

preferred_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

try:
    from google import genai as genai_sdk

    client = genai_sdk.Client(api_key=api_key)
    backend = "google-genai"

    def list_candidate_models():
        candidates = [preferred_model, "gemini-2.0-flash-001", "gemini-2.0-flash"]
        try:
            for model in client.models.list():
                model_name = getattr(model, "name", "")
                if "gemini" in model_name and "flash" in model_name:
                    candidates.append(model_name)
        except Exception:
            pass
        deduped = []
        for candidate in candidates:
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped

    def generate(prompt, selected_model=None):
        last_error = None
        for candidate in ([selected_model] if selected_model else []) + list_candidate_models():
            if not candidate:
                continue
            try:
                response = client.models.generate_content(model=candidate, contents=prompt)
                return candidate, getattr(response, "text", "").strip()
            except Exception as exc:
                last_error = exc
        raise last_error or RuntimeError("No suitable Gemini model found")

except ImportError:
    import google.generativeai as genai_legacy

    backend = "google-generativeai"
    genai_legacy.configure(api_key=api_key)

    def list_candidate_models():
        candidates = [preferred_model, "gemini-2.0-flash", "gemini-1.5-flash"]
        try:
            for model in genai_legacy.list_models():
                model_name = getattr(model, "name", "")
                methods = getattr(model, "supported_generation_methods", [])
                if "generateContent" in methods and "gemini" in model_name:
                    candidates.append(model_name)
        except Exception:
            pass
        deduped = []
        for candidate in candidates:
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped

    def generate(prompt, selected_model=None):
        last_error = None
        for candidate in ([selected_model] if selected_model else []) + list_candidate_models():
            if not candidate:
                continue
            try:
                response = genai_legacy.GenerativeModel(candidate).generate_content(prompt)
                return candidate, getattr(response, "text", "").strip()
            except Exception as exc:
                last_error = exc
        raise last_error or RuntimeError("No suitable Gemini model found")

current_model = None

# If prompt provided as argument
if len(sys.argv) > 1:
    prompt = " ".join(sys.argv[1:])
    try:
        current_model, response_text = generate(prompt, current_model)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"\n[Gemini] Backend: {backend}")
    print(f"[Gemini] Model: {current_model}")
    print(f"[Gemini] Prompt: {prompt}\n")
    print(response_text)
else:
    # Interactive mode
    print("\n" + "="*50)
    print("  Google Gemini - Interactive Mode")
    print("="*50 + "\n")
    print("Type 'exit' or 'quit' to exit\n")
    
    while True:
        try:
            prompt = input(">>> ").strip()
            if prompt.lower() in ["exit", "quit"]:
                print("\nGoodbye!")
                break
            if not prompt:
                continue

            current_model, response_text = generate(prompt, current_model)
            print(f"\n[{current_model}] {response_text}\n")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
PYEOF

# Run Gemini with the correct Python, passing all arguments
"${PYTHON_BIN}" "${GEMINI_SCRIPT}" "$@"
