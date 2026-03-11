#!/bin/bash

# Dev setup script

# Function to print information
print_info() {
    echo "INFO: $1"
}

# Project root
REPO_ROOT="
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"

# Entering the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

print_info "cd \"$REPO_ROOT\""
