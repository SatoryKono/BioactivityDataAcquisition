#!/usr/bin/env bash
set -e

echo "=== Git / Git LFS auth repair ==="

git rev-parse --show-toplevel >/dev/null

CURRENT_BRANCH="$(git branch --show-current)"
echo "Current branch: $CURRENT_BRANCH"

if [ -z "$CURRENT_BRANCH" ]; then
  echo "ERROR: Cannot detect current branch."
  exit 1
fi

echo
echo "Remote:"
git remote -v

echo
echo "Install Git LFS hooks"
git lfs install

echo
echo "Erase cached GitHub HTTPS credentials"
printf "protocol=https\nhost=github.com\n\n" | git credential reject || true
printf "protocol=https\nhost=github.com\npath=SatoryKono/BioactivityDataAcquisition.git\n\n" | git credential reject || true

echo
echo "Force GitHub auth prompt on next operation"
git config --global credential.helper manager-core || git config --global credential.helper manager || true
git config --global credential.useHttpPath true

echo
echo "Check LFS"
git lfs fsck

echo
echo "Push LFS objects for current branch"
git lfs push --all origin "$CURRENT_BRANCH"

echo
echo "Push current branch to remote main"
git push origin "$CURRENT_BRANCH:main"

echo
echo "=== DONE ==="
