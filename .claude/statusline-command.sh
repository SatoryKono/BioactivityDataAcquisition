#!/usr/bin/env bash
# Claude Code status line for Warp terminal
# Located at: .claude/statusline-command.sh

input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Shorten the working directory: replace HOME with ~
home_dir="$HOME"
if [ -n "$cwd" ] && [ -n "$home_dir" ]; then
    cwd="${cwd/#$home_dir/~}"
fi

parts=()

if [ -n "$cwd" ]; then
    parts+=("$cwd")
fi

if [ -n "$model" ]; then
    parts+=("$model")
fi

if [ -n "$used" ]; then
    used_int=$(printf "%.0f" "$used")
    parts+=("ctx: ${used_int}%")
fi

# Join parts with separator
result=""
for part in "${parts[@]}"; do
    if [ -z "$result" ]; then
        result="$part"
    else
        result="$result | $part"
    fi
done

printf "%s" "$result"