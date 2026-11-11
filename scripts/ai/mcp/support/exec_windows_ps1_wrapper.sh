#!/usr/bin/env bash
# Shared Windows interop for MCP wrappers that must fail closed to a host owner.
# shellcheck shell=bash

mcp_exec_windows_ps1_wrapper() {
  local wrapper_ps1_name="$1"
  local missing_owner_message="$2"
  local missing_powershell_message="${3:-$missing_owner_message}"
  local wrapper=""

  if command -v cygpath >/dev/null 2>&1; then
    wrapper="$(cygpath -aw "${SCRIPT_DIR}/${wrapper_ps1_name}")"
  elif command -v wslpath >/dev/null 2>&1; then
    wrapper="$(wslpath -aw "${SCRIPT_DIR}/${wrapper_ps1_name}")"
  else
    printf '%s\n' "${missing_owner_message}" >&2
    exit 1
  fi
  if ! command -v powershell.exe >/dev/null 2>&1; then
    printf '%s\n' "${missing_powershell_message}" >&2
    exit 1
  fi
  exec powershell.exe -NoProfile -NonInteractive -File "${wrapper}"
}
