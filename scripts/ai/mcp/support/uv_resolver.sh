#!/usr/bin/env bash
# Shared uv/uvx resolution for MCP wrappers.

bioetl_enable_uvx_network_bypass() {
  # Bypass broken system HTTP proxies for PyPI (direct HTTPS works on this host).
  export NO_PROXY='*'
  export no_proxy='*'
  unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy || true
}

bioetl_resolve_uvx_bin() {
  if command -v uvx >/dev/null 2>&1; then
    command -v uvx
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    local uv_bin uv_dir
    uv_bin="$(command -v uv)"
    uv_dir="$(dirname -- "${uv_bin}")"
    if [[ -x "${uv_dir}/uvx" ]]; then
      printf '%s\n' "${uv_dir}/uvx"
      return 0
    fi
  fi
  local candidate
  for candidate in \
    "${LOCALAPPDATA:-}/Programs/Python/Python313/Scripts/uvx.exe" \
    "${LOCALAPPDATA:-}/Programs/Python/Python312/Scripts/uvx.exe" \
    "${HOME}/.local/bin/uvx" \
    "${HOME}/.cargo/bin/uvx"
  do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  printf '%s\n' "uvx"
  return 1
}
