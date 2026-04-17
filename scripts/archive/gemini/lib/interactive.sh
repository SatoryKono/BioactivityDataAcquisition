#!/bin/bash

# gemini-interactive.sh
# Interactive Gemini launcher for BioETL project in WSL
# Provides menu-driven interface for agent selection, role assignment, and task modes

# Use PROJECT_ROOT from environment, or calculate it
if [[ -z "$PROJECT_ROOT" ]]; then
  PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fi

GEMINI_HOME="${PROJECT_ROOT}/.gemini"
GEMINI_CONFIG="${GEMINI_HOME}/config.toml"
GEMINI_MCP_SETTINGS="${GEMINI_HOME}/settings.json"
GEMINI_MEMORY_FILE="${PROJECT_ROOT}/docs/00-project/ai/memory/gemini-memory.json"
GEMINI_SESSIONS_DIR="${PROJECT_ROOT}/docs/00-project/ai/sessions"
MENU_BACK_LABEL="  0. << Back to Main Menu"
PRESS_ENTER_PROMPT="Press Enter to continue..."

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Create sessions directory
mkdir -p "${GEMINI_SESSIONS_DIR}"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

print_header() {
  clear
  echo -e "${CYAN}"
  echo "╔════════════════════════════════════════════════════════════════════════════════╗"
  echo "║                                                                                ║"
  echo "║                    🧬 GEMINI INTERACTIVE LAUNCHER - BioETL 🧬                 ║"
  echo "║                                                                                ║"
  echo "╚════════════════════════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
  return 0
}

print_section() {
  local message="$1"
  echo -e "\n${BLUE}▶ ${message}${NC}"
  return 0
}

print_success() {
  local message="$1"
  echo -e "${GREEN}✓ ${message}${NC}"
  return 0
}

print_error() {
  local message="$1"
  echo -e "${RED}✗ ${message}${NC}"
  return 0
}

print_warning() {
  local message="$1"
  echo -e "${YELLOW}⚠ ${message}${NC}"
  return 0
}

print_info() {
  local message="$1"
  echo -e "${CYAN}ℹ ${message}${NC}"
  return 0
}

# Check if environment is ready
check_environment() {
  print_section "Checking Environment"
  
  local ready=true
  
  # Check Gemini directories
  if [[ ! -d "${GEMINI_HOME}" ]]; then
    print_error "Gemini home not found: ${GEMINI_HOME}"
    ready=false
  else
    print_success "Gemini home: ${GEMINI_HOME}"
  fi
  
  # Check config files
  if [[ ! -f "${GEMINI_CONFIG}" ]]; then
    print_error "Config not found: ${GEMINI_CONFIG}"
    ready=false
  else
    print_success "Config: $(basename "${GEMINI_CONFIG}")"
  fi
  
  if [[ ! -f "${GEMINI_MCP_SETTINGS}" ]]; then
    print_error "MCP settings not found: ${GEMINI_MCP_SETTINGS}"
    ready=false
  else
    print_success "MCP settings: $(basename "${GEMINI_MCP_SETTINGS}")"
  fi
  
  # Check memory file
  if [[ ! -f "${GEMINI_MEMORY_FILE}" ]]; then
    print_warning "Memory file not found, will be created"
  else
    print_success "Memory file: $(basename "${GEMINI_MEMORY_FILE}")"
  fi
  
  # Check Node.js
  if ! command -v node &> /dev/null; then
    print_warning "Node.js not found in PATH"
  else
    print_success "Node.js: $(node --version)"
  fi
  
  # Check UV
  if ! command -v uvx &> /dev/null; then
    print_warning "UV not found in PATH (fetch MCP may fail)"
  else
    print_success "UV: $(uvx --version 2>&1 | head -1)"
  fi
  
  if [[ "$ready" == false ]]; then
    print_error "\nEnvironment check failed. Run setup first:"
    echo "  bash scripts/ai/setup-gemini-wsl.sh"
    return 1
  fi
  
  print_success "\nEnvironment check passed!"
  return 0
}

# Show available profiles
show_profiles() {
  print_section "Available Agent Profiles"
  
  if [[ ! -d "${GEMINI_HOME}/agents" ]]; then
    print_warning "No agents directory found"
    return
  fi
  
  local count=0
  echo ""
  for profile in "${GEMINI_HOME}"/agents/py-*.md; do
    if [[ -f "$profile" ]]; then
      local basename=$(basename "$profile" .md)
      local desc=$(head -3 "$profile" | grep -E "^#" | head -1 | sed 's/^[# ]*//g')
      printf "  %2d. %-30s  %s\n" $((++count)) "$basename" "$desc"
    fi
  done
  
  if [[ $count -eq 0 ]]; then
    print_warning "No profiles found. Run sync:"
    echo "  bash scripts/ai/sync-agents-codex-to-gemini.sh"
  fi
}

# Display main menu
main_menu() {
  print_header
  
  print_section "Main Menu"
  echo ""
  echo "  1. 💬 Interactive Chat Mode"
  echo "  2. 📋 Task/Work Mode"
  echo "  3. 🔍 Code Review Mode"
  echo "  4. 📊 Analysis Mode"
  echo "  5. ⚙️  Configuration & Maintenance"
  echo "  6. 📚 Help & Documentation"
  echo "  7. 🚪 Exit"
  echo ""
  read -p "Select option [1-7]: " main_choice
  return 0
}

# ============================================================================
# MODE 1: INTERACTIVE CHAT
# ============================================================================

mode_chat() {
  print_header
  print_section "Interactive Chat Mode"
  
  show_profiles
  
  echo ""
  echo "${MENU_BACK_LABEL}"
  read -p "Select profile [0-9]: " profile_idx
  
  if [[ "$profile_idx" == "0" ]]; then
    return
  fi
  
  local profiles=("${GEMINI_HOME}"/agents/py-*.md)
  if [[ ! -f "${profiles[$profile_idx - 1]}" ]]; then
    print_error "Invalid selection"
    sleep 2
    return
  fi
  
  local selected_profile=$(basename "${profiles[$profile_idx - 1]}" .md)
  
  print_section "Chat Mode - $selected_profile"
  echo ""
  print_info "Starting interactive chat session..."
  echo ""
  
  # Create session file
  local session_file="${GEMINI_SESSIONS_DIR}/chat-$(date +%s).log"
  
  echo "=== GEMINI CHAT SESSION ===" > "$session_file"
  echo "Profile: $selected_profile" >> "$session_file"
  echo "Started: $(date)" >> "$session_file"
  echo "Project Root: ${PROJECT_ROOT}" >> "$session_file"
  echo "" >> "$session_file"
  
  print_success "Session log: $session_file"
  print_info "Type 'exit' or 'quit' to end session"
  echo ""
  echo "----------------------------------------"
  echo ""
  
  # Interactive chat loop
  while true; do
    read -p "You> " user_input
    
    if [[ "$user_input" == "exit" ]] || [[ "$user_input" == "quit" ]]; then
      break
    fi
    
    if [[ -z "$user_input" ]]; then
      continue
    fi
    
    echo "$user_input" >> "$session_file"
    
    # Simulate Gemini response (placeholder)
    echo ""
    echo -e "${MAGENTA}Gemini ($selected_profile)>${NC}"
    echo "  [Processing with profile: $selected_profile]"
    echo "  [Using MCP: $GEMINI_MCP_SETTINGS]"
    echo "  [Query: $user_input]"
    echo ""
  done
  
  echo "=== SESSION ENDED ===" >> "$session_file"
  echo "Ended: $(date)" >> "$session_file"
  
  print_success "\nSession saved to: $session_file"
  sleep 2
  return 0
}

# ============================================================================
# MODE 2: TASK/WORK MODE
# ============================================================================

mode_task() {
  print_header
  print_section "Task/Work Mode"
  
  echo ""
  echo "  1. Code Review (py-review-orchestrator)"
  echo "  2. Configuration Audit (py-config-bot)"
  echo "  3. Test Generation (py-test-swarm)"
  echo "  4. Architecture Analysis (py-architecture-debt-bot)"
  echo "  5. Data Engineering (py-debug-bot)"
  echo "  6. Custom Profile"
  echo "${MENU_BACK_LABEL}"
  echo ""
  read -p "Select task [0-6]: " task_choice
  
  case "$task_choice" in
    1) task_review ;;
    2) task_config ;;
    3) task_test ;;
    4) task_architecture ;;
    5) task_debug ;;
    6) task_custom ;;
    0) return ;;
    *) print_error "Invalid selection"; sleep 2 ;;
  esac
  return 0
}

task_review() {
  print_header
  print_section "Code Review Task"
  
  echo ""
  echo "Scope options:"
  echo "  1. Staged changes (git diff --staged)"
  echo "  2. Specific file"
  echo "  3. Directory"
  echo "  4. Entire project"
  echo ""
  read -p "Select scope [1-4]: " scope_choice
  
  case "$scope_choice" in
    1)
      echo "Scope: Staged changes"
      read -p "Review focus (architecture/tests/style/all) [all]: " focus
      focus=${focus:-all}
      ;;
    2)
      read -p "File path: " file_path
      echo "Scope: $file_path"
      ;;
    3)
      read -p "Directory path: " dir_path
      echo "Scope: $dir_path"
      ;;
    4)
      echo "Scope: Entire project"
      ;;
    *)
      print_error "Invalid selection"
      sleep 2
      return 1
      ;;
  esac
  
  print_info "Creating review task..."
  local session_file="${GEMINI_SESSIONS_DIR}/review-$(date +%s).md"
  
  cat > "$session_file" << EOF
# Code Review Task

**Profile:** py-review-orchestrator  
**Role:** default (orchestration)  
**Started:** $(date)  
**Scope:** ${scope_choice}  

## Task Description

Review code against BioETL standards defined in GEMINI.md:
- Architecture compliance (hexagonal pattern)
- Test coverage (≥85%)
- Type hints and mypy strictness
- Logging (structlog, no print)
- Error handling patterns

## Focus Areas
- $([ "$focus" != "all" ] && echo "$focus" || echo "Complete review")

## Context Files
- GEMINI.md (project constraints)
- .gemini/agents/py-review-orchestrator.md (agent profile)
- .codex/agents/CODEX-RUNTIME.md (reference)

---

## Review Results

[Gemini output will be appended here]

EOF
  
  print_success "Task file created: $session_file"
  print_info "Ready to run code review. Profile loaded: py-review-orchestrator"
  sleep 2
  return 0
}

task_config() {
  print_header
  print_section "Configuration Audit Task"
  
  echo ""
  read -p "Audit scope (configs/all/specific) [all]: " audit_scope
  audit_scope=${audit_scope:-all}
  
  local session_file="${GEMINI_SESSIONS_DIR}/config-audit-$(date +%s).md"
  
  cat > "$session_file" << EOF
# Configuration Audit Task

**Profile:** py-config-bot  
**Role:** implementation  
**Started:** $(date)  
**Scope:** ${audit_scope}  

## Task Description

Audit configuration files for BioETL project:
- YAML syntax and structure
- Medallion architecture alignment
- Data loading strategies (null vs full_scan_only)
- Parameter validation

## Scope: $audit_scope

## Context
- GEMINI.md (section 2: Data Flow - Medallion Architecture)
- .gemini/agents/py-config-bot.md

---

## Audit Results

[Gemini output will be appended here]

EOF
  
  print_success "Task file created: $session_file"
  print_info "Ready to audit configs/. Profile loaded: py-config-bot"
  sleep 2
  return 0
}

task_test() {
  print_header
  print_section "Test Generation Task"
  
  echo ""
  read -p "Target coverage (%) [85]: " target_cov
  target_cov=${target_cov:-85}
  
  read -p "Scope (src/bioetl/application, src/bioetl/domain, all) [application]: " test_scope
  test_scope=${test_scope:-src/bioetl/application}
  
  local session_file="${GEMINI_SESSIONS_DIR}/test-gen-$(date +%s).md"
  
  cat > "$session_file" << EOF
# Test Generation Task

**Profile:** py-test-swarm  
**Role:** default (orchestration)  
**Started:** $(date)  
**Target Coverage:** ${target_cov}%  
**Scope:** ${test_scope}  

## Task Description

Generate missing unit and integration tests using pytest:
- Unit tests for domain logic
- Integration tests for adapters
- VCR cassettes for HTTP calls
- Fixtures with in-memory fakes

## Requirements
- Achieve ${target_cov}% coverage in $test_scope
- All tests in tests/ directory
- Fixtures in tests/fixtures/
- HTTP cassettes in tests/fixtures/vcr/{provider}/

## Context
- GEMINI.md (section 5: Testing & Validation)
- .gemini/agents/py-test-swarm.md
- pytest.ini (test configuration)

---

## Generated Tests

[Gemini output will be appended here]

EOF
  
  print_success "Task file created: $session_file"
  print_info "Ready to generate tests for $test_scope. Target: ${target_cov}%"
  sleep 2
  return 0
}

task_architecture() {
  print_header
  print_section "Architecture Analysis Task"
  
  echo ""
  echo "Analysis focus:"
  echo "  1. Technical debt"
  echo "  2. Dependency violations"
  echo "  3. Layer isolation"
  echo "  4. Port coverage"
  echo ""
  read -p "Select focus [1-4]: " arch_focus
  
  local focus_name=""
  case "$arch_focus" in
    1) focus_name="Technical Debt" ;;
    2) focus_name="Dependency Violations" ;;
    3) focus_name="Layer Isolation" ;;
    4) focus_name="Port Coverage" ;;
    *)
      print_error "Invalid selection"
      sleep 2
      return 1
      ;;
  esac
  
  local session_file="${GEMINI_SESSIONS_DIR}/arch-analysis-$(date +%s).md"
  
  cat > "$session_file" << EOF
# Architecture Analysis Task

**Profile:** py-architecture-debt-bot  
**Role:** default (orchestration)  
**Started:** $(date)  
**Focus:** $focus_name  

## Task Description

Analyze BioETL architecture against hexagonal/ports-adapters pattern:
- Layer isolation: domain → application → infrastructure
- Port contracts: all external deps abstracted via Protocols
- Dependency injection: no concrete instantiation in domain/app
- Domain purity: no I/O in domain layer

## Focus: $focus_name

## Constraints (from GEMINI.md)
- Domain MUST NOT import infrastructure
- ALL I/O via Ports (e.g., LoggerPort, StoragePort, HTTPPort)
- Dependency injection via __init__ only
- Assembly logic in src/bioetl/composition/

## Context
- GEMINI.md (section 1: Core Architecture)
- .gemini/agents/py-architecture-debt-bot.md
- src/bioetl/domain/ports/ (existing contracts)

---

## Analysis Results

[Gemini output will be appended here]

EOF
  
  print_success "Task file created: $session_file"
  print_info "Ready to analyze architecture. Focus: $focus_name"
  sleep 2
  return 0
}

task_debug() {
  print_header
  print_section "Debug/Fix Task"
  
  echo ""
  read -p "Issue/Bug description: " issue_desc
  
  echo ""
  read -p "Affected file/module (optional): " affected_file
  
  local session_file="${GEMINI_SESSIONS_DIR}/debug-$(date +%s).md"
  
  cat > "$session_file" << EOF
# Debug/Fix Task

**Profile:** py-debug-bot  
**Role:** implementation  
**Started:** $(date)  
**Issue:** $issue_desc  
**Affected:** ${affected_file:-N/A}  

## Problem Statement

$issue_desc

## Constraints
- Follow GEMINI.md standards
- Maintain test coverage ≥85%
- Use structlog for logging (no print)
- Type hints required

## Context
- GEMINI.md (sections 1-4)
- .gemini/agents/py-debug-bot.md
- Affected file: $affected_file

---

## Fix Implementation

[Gemini output will be appended here]

EOF
  
  print_success "Task file created: $session_file"
  print_info "Ready to debug issue. Type: $issue_desc"
  sleep 2
  return 0
}

task_custom() {
  print_header
  print_section "Custom Task"
  
  show_profiles
  
  echo ""
  read -p "Select profile (by number): " custom_profile_idx
  
  read -p "Task description: " task_desc
  
  local profiles=("${GEMINI_HOME}"/agents/py-*.md)
  if [[ ! -f "${profiles[$custom_profile_idx - 1]}" ]]; then
    print_error "Invalid selection"
    sleep 2
    return 1
  fi
  local selected_profile=$(basename "${profiles[$custom_profile_idx - 1]}" .md)
  
  local session_file="${GEMINI_SESSIONS_DIR}/custom-$(date +%s).md"
  
  cat > "$session_file" << EOF
# Custom Task

**Profile:** $selected_profile  
**Started:** $(date)  
**Description:** $task_desc  

## Task

$task_desc

---

## Results

[Gemini output will be appended here]

EOF
  
  print_success "Task file created: $session_file"
  print_info "Ready to execute custom task with profile: $selected_profile"
  sleep 2
  return 0
}

# ============================================================================
# MODE 3: CODE REVIEW MODE (QUICK)
# ============================================================================

mode_review() {
  print_header
  print_section "Code Review Mode (Quick)"
  
  echo ""
  echo "  1. Review staged changes"
  echo "  2. Review specific file"
  echo "  3. Review directory"
  echo "${MENU_BACK_LABEL}"
  echo ""
  read -p "Select [0-3]: " review_choice
  
  case "$review_choice" in
    1)
      print_info "Staged changes review with py-review-orchestrator"
      local session_file="${GEMINI_SESSIONS_DIR}/quick-review-$(date +%s).md"
      echo "# Quick Review: Staged Changes" > "$session_file"
      echo "Profile: py-review-orchestrator" >> "$session_file"
      echo "Time: $(date)" >> "$session_file"
      print_success "Session: $(basename $session_file)"
      ;;
    2)
      read -p "File path: " file_path
      print_info "Reviewing: $file_path"
      ;;
    3)
      read -p "Directory path: " dir_path
      print_info "Reviewing: $dir_path"
      ;;
    0) return ;;
    *)
      print_error "Invalid selection"
      sleep 2
      return 1
      ;;
  esac
  
  sleep 2
  return 0
}

# ============================================================================
# MODE 4: ANALYSIS MODE
# ============================================================================

mode_analysis() {
  print_header
  print_section "Analysis Mode"
  
  echo ""
  echo "  1. Data Flow Analysis (medallion architecture)"
  echo "  2. Dependency Analysis"
  echo "  3. Test Coverage Analysis"
  echo "  4. Performance Analysis"
  echo "${MENU_BACK_LABEL}"
  echo ""
  read -p "Select [0-4]: " analysis_choice
  
  case "$analysis_choice" in
    1)
      print_info "Analyzing medallion data architecture..."
      ;;
    2)
      print_info "Analyzing project dependencies..."
      ;;
    3)
      print_info "Analyzing test coverage..."
      ;;
    4)
      print_info "Analyzing performance..."
      ;;
    0) return ;;
    *)
      print_error "Invalid selection"
      sleep 2
      return 1
      ;;
  esac
  
  sleep 2
  return 0
}

# ============================================================================
# MODE 5: MAINTENANCE
# ============================================================================

mode_maintenance() {
  print_header
  print_section "Configuration & Maintenance"
  
  echo ""
  echo "  1. Initialize Gemini Environment"
  echo "  2. Sync Agent Profiles from Codex"
  echo "  3. View Environment Status"
  echo "  4. Clear Memory & Reset"
  echo "  5. Update MCP Servers"
  echo "${MENU_BACK_LABEL}"
  echo ""
  read -p "Select [0-5]: " maint_choice
  
  case "$maint_choice" in
    1)
      print_info "Running setup..."
      bash scripts/ai/setup-gemini-wsl.sh
      read -p "${PRESS_ENTER_PROMPT}" _
      ;;
    2)
      print_info "Syncing profiles..."
      bash scripts/ai/sync-agents-codex-to-gemini.sh
      read -p "${PRESS_ENTER_PROMPT}" _
      ;;
    3)
      print_section "Environment Status"
      echo ""
      echo "Gemini Home: $GEMINI_HOME"
      echo "Config: $([ -f $GEMINI_CONFIG ] && echo '✓' || echo '✗') $GEMINI_CONFIG"
      echo "MCP Settings: $([ -f $GEMINI_MCP_SETTINGS ] && echo '✓' || echo '✗') $GEMINI_MCP_SETTINGS"
      echo "Memory File: $([ -f $GEMINI_MEMORY_FILE ] && echo '✓' || echo '✗') $GEMINI_MEMORY_FILE"
      echo ""
      echo "Sessions dir: $GEMINI_SESSIONS_DIR"
      echo "Total sessions: $(ls -1 ${GEMINI_SESSIONS_DIR}/*.{log,md} 2>/dev/null | wc -l)"
      echo ""
      read -p "Press Enter to continue..."
      ;;
    4)
      print_warning "This will clear all memory and reset Gemini environment."
      read -p "Continue? (yes/no): " confirm
      if [[ "$confirm" == "yes" ]]; then
        rm -f "$GEMINI_MEMORY_FILE"
        print_success "Memory cleared"
        bash scripts/ai/setup-gemini-wsl.sh
        read -p "${PRESS_ENTER_PROMPT}" _
      fi
      ;;
    5)
      print_info "Edit .gemini/settings.json to update MCP servers"
      echo "File: $GEMINI_MCP_SETTINGS"
      read -p "Open in editor? (yes/no): " edit_confirm
      if [[ "$edit_confirm" == "yes" ]]; then
        ${EDITOR:-nano} "$GEMINI_MCP_SETTINGS"
      fi
      ;;
    0) return ;;
    *)
      print_error "Invalid selection"
      sleep 2
      return 1
      ;;
  esac
  return 0
}

# ============================================================================
# MODE 6: HELP
# ============================================================================

mode_help() {
  print_header
  print_section "Help & Documentation"
  
  echo ""
  echo "  1. View Setup Guide"
  echo "  2. View Agent Profiles"
  echo "  3. View Project Constraints (GEMINI.md)"
  echo "  4. View MCP Configuration"
  echo "  5. List Recent Sessions"
  echo "${MENU_BACK_LABEL}"
  echo ""
  read -p "Select [0-5]: " help_choice
  
  case "$help_choice" in
    1)
      if [[ -f "scripts/ai/GEMINI-WSL-SETUP.md" ]]; then
        less "scripts/ai/GEMINI-WSL-SETUP.md"
      else
        print_error "Setup guide not found"
        sleep 2
      fi
      ;;
    2)
      print_section "Available Profiles"
      ls -1 "${GEMINI_HOME}"/agents/py-*.md 2>/dev/null | xargs -I{} basename {} .md | sed 's/^/  - /'
      read -p "${PRESS_ENTER_PROMPT}" _
      ;;
    3)
      if [[ -f "GEMINI.md" ]]; then
        less "GEMINI.md"
      else
        print_error "GEMINI.md not found"
        sleep 2
      fi
      ;;
    4)
      if [[ -f "$GEMINI_MCP_SETTINGS" ]]; then
        less "$GEMINI_MCP_SETTINGS"
      else
        print_error "MCP settings not found"
        sleep 2
      fi
      ;;
    5)
      print_section "Recent Sessions"
      ls -1t "${GEMINI_SESSIONS_DIR}"/*.{log,md} 2>/dev/null | head -10 | xargs -I{} basename {} | sed 's/^/  - /'
      echo ""
      read -p "Open session file? Enter filename or press Enter to skip: " session_name
      if [[ -n "$session_name" ]]; then
        less "${GEMINI_SESSIONS_DIR}/$session_name" 2>/dev/null || print_error "Session not found"
      fi
      read -p "${PRESS_ENTER_PROMPT}" _
      ;;
    0) return ;;
    *)
      print_error "Invalid selection"
      sleep 2
      return 1
      ;;
  esac
  return 0
}

# ============================================================================
# MAIN LOOP
# ============================================================================

main() {
  # Check environment once at startup
  if ! check_environment; then
    print_error "\nSetup required. Run:"
    echo "  bash scripts/ai/setup-gemini-wsl.sh"
    exit 1
  fi
  
  sleep 2
  
  # Main menu loop
  while true; do
    main_menu
    
    case "$main_choice" in
      1) mode_chat ;;
      2) mode_task ;;
      3) mode_review ;;
      4) mode_analysis ;;
      5) mode_maintenance ;;
      6) mode_help ;;
      7)
        print_header
        print_success "Goodbye! 👋"
        echo ""
        exit 0
        ;;
      *)
        print_error "Invalid selection"
        sleep 2
        ;;
    esac
  done
}

# Run main
main "$@"
