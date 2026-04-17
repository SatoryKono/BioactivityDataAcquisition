#!/bin/bash

# lib/utils.sh - Shared utility functions for Gemini

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Print functions
print_header() {
  clear
  echo -e "${CYAN}"
  echo "╔════════════════════════════════════════════════════════════════════════════════╗"
  echo "║                         🧬 GEMINI - BioETL AI Assistant 🧬                    ║"
  echo "╚════════════════════════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
}

print_section() {
  echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
  echo -e "${CYAN}ℹ $1${NC}"
}

# Get project root - Must be passed from caller
get_project_root() {
  if [ -n "$PROJECT_ROOT" ]; then
    echo "$PROJECT_ROOT"
  else
    # Fallback: try to find .gemini folder
    local current="$(pwd)"
    while [ "$current" != "/" ] && [ "$current" != "" ]; do
      if [ -d "$current/.gemini" ]; then
        echo "$current"
        return 0
      fi
      current="$(dirname "$current")"
    done
    echo "$current"
  fi
}

# Get Gemini home
get_gemini_home() {
  echo "${GEMINI_HOME:=$(get_project_root)/.gemini}"
}

# Get config file
get_config_file() {
  echo "$(get_gemini_home)/config.toml"
}

# Get MCP settings file
get_mcp_settings() {
  echo "$(get_gemini_home)/settings.json"
}

# Get memory file
get_memory_file() {
  echo "${GEMINI_MEMORY_FILE:=$(get_project_root)/docs/00-project/ai/memory/gemini-memory.json}"
}

# Get sessions directory
get_sessions_dir() {
  echo "${GEMINI_SESSIONS_DIR:=$(get_project_root)/docs/00-project/ai/sessions}"
}

# Check if environment is ready
check_environment() {
  local gemini_home=$(get_gemini_home)
  local config_file=$(get_config_file)
  local mcp_settings=$(get_mcp_settings)
  
  local ready=true
  
  if [ ! -d "$gemini_home" ]; then
    print_error "Gemini home not found: $gemini_home"
    ready=false
  fi
  
  if [ ! -f "$config_file" ]; then
    print_error "Config not found: $config_file"
    ready=false
  fi
  
  if [ ! -f "$mcp_settings" ]; then
    print_error "MCP settings not found: $mcp_settings"
    ready=false
  fi
  
  if [ "$ready" = false ]; then
    return 1
  fi
  
  return 0
}

# List available profiles
list_profiles() {
  local gemini_home=$(get_gemini_home)
  local agents_dir="${gemini_home}/agents"
  
  if [ ! -d "$agents_dir" ]; then
    print_warning "No agents directory found"
    return
  fi
  
  echo ""
  local count=0
  for profile in "$agents_dir"/py-*.md; do
    if [ -f "$profile" ]; then
      local basename=$(basename "$profile" .md)
      local desc=$(head -3 "$profile" | grep -E "^#" | head -1 | sed 's/^[# ]*//g')
      printf "  %2d. %-30s  %s\n" $((++count)) "$basename" "$desc"
    fi
  done
  echo ""
}

# Create session file
create_session_file() {
  local type="$1"
  local sessions_dir=$(get_sessions_dir)
  
  mkdir -p "$sessions_dir"
  
  local session_file="${sessions_dir}/${type}-$(date +%s).${type##*-}"
  echo "$session_file"
}

# Sanitize input
sanitize_path() {
  echo "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

export -f print_header print_section print_success print_error print_warning print_info
export -f get_project_root get_gemini_home get_config_file get_mcp_settings get_memory_file
export -f get_sessions_dir check_environment list_profiles create_session_file sanitize_path
