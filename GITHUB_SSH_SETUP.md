# GitHub SSH Setup Configuration

**Generated:** 2026-07-31  
**Purpose:** GitHub SSH access configuration for branch cleanup and git operations

---

## SSH Key Information

### Public Key (Add to GitHub)

**Add this key at:** https://github.com/settings/keys

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKwCl/LfRbnPnR065EhV2bV/QRCfDN+A9+sFHlrBVK2o bioetl-devin@github.com
```

**Key Title:** `BioETL Devin AI`

### Private Key Location

**Path:** `~/.ssh/bioetl_github`

**Permissions:** 600 (read/write for owner only)

**SSH Config:** Added to `~/.ssh/config`

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/bioetl_github
    IdentitiesOnly yes
```

---

## Git Configuration

### Global Git Config

```bash
git config --global user.name "Devin AI"
git config --global user.email "158243242+devin-ai-integration[bot]@users.noreply.github.com"
```

### Current Status

```bash
git config --global user.name
# Output: Devin AI

git config --global user.email
# Output: 158243242+devin-ai-integration[bot]@users.noreply.github.com
```

---

## SSH Agent Setup

### Add Key to SSH Agent

```bash
# Start SSH agent
eval "$(ssh-agent -s)"

# Add private key
ssh-add ~/.ssh/bioetl_github
```

### Verify SSH Agent

```bash
# List keys in agent
ssh-add -l

# Expected output:
# 256 SHA256:eeTnSn/E8OvlsZ3iIMlQ2Dui7Vgw+KlTtk/BzukmwN4 bioetl-devin@github.com (ED25519)
```

---

## GitHub Remote Configuration

### Current Remote

```bash
git remote -v
# origin  git@github.com:SatoryKono/BioactivityDataAcquisition.git (fetch)
# origin  git@github.com:SatoryKono/BioactivityDataAcquisition.git (push)
```

**Status:** ✅ Already configured for SSH

---

## Setup Instructions

### Step 1: Add SSH Key to GitHub

1. Go to: https://github.com/settings/keys
2. Click "New SSH key" or "Add SSH key"
3. Enter title: `BioETL Devin AI`
4. Paste public key:
   ```
   ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKwCl/LfRbnPnR065EhV2bV/QRCfDN+A9+sFHlrBVK2o bioetl-devin@github.com
   ```
5. Click "Add SSH key"

### Step 2: Test SSH Connection

```bash
ssh -T git@github.com
```

**Expected output:** `Hi SatoryKono! You've successfully authenticated...`

### Step 3: Verify Git Configuration

```bash
git config --global user.name
git config --global user.email
```

### Step 4: Add Key to SSH Agent (if not already)

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/bioetl_github
```

---

## Branch Cleanup Commands

### Delete Remote Branches

After SSH key is added to GitHub, run these commands to delete remote branches:

```bash
# Recent branches (2026-07-31)
git push origin --delete fix/memory-blockers-7341-7344-v2
git push origin --delete codex/ai-memory-five-cycle-audit-20260730
git push origin --delete codex/ci-audit-20260727
git push origin --delete codex/ci-audit-20260727-v2
git push origin --delete codex/ci-audit-20260727-v3
git push origin --delete fix/memory-blockers-7341-7344
git push origin --delete fix/sonar-w1-w3-remediation
git push origin --delete fix/resolve-merge-conflicts-20260731
git push origin --delete audit/docs-architecture-3-cycles
git push origin --delete fix/full-suite-green-20260731-final
git push origin --delete fix/unit-fast-adr-matrix-20260731
git push origin --delete fix/full-test-suite-green-20260730-r2

# Older branches (2026-07-27 to 2026-07-30)
git push origin --delete fix/full-test-suite-green-20260730
git push origin --delete fix/issue-7254-semantic-debt-audit
git push origin --delete audit/ci-actions-3-cycles
git push origin --delete fix/issue-6776-vcr-slimming
git push origin --delete audit/test-quality-5-cycles
git push origin --delete codex/test-system-five-cycle-audit-20260730
git push origin --delete fix/scenes-parity-ledger-drift
git push origin --delete fix/issue-6473-phased-migration-facade
git push origin --delete fix/issue-6611-root-hygiene-closeout
git push origin --delete audit/technical-debt-10-cycle-20260730-v3
git push origin --delete master_20260730
git push origin --delete audit/technical-debt-10-cycle-20260730-v2
git push origin --delete fix/issue-6611-root-governance-regression
git push origin --delete audit/technical-debt-10-cycle-20260729
git push origin --delete master_20260729-1
git push origin --delete codex/ai-memory-7174-clean
git push origin --delete codex/ai-memory-7174
git push origin --delete fix/pd-diagnostics-cycle10-v2
git push origin --delete fix/pd-diagnostics-cycle-10x
git push origin --delete arch/stage3-residual-2026-07-29
git push origin --delete docs/residual-cleanup-a-h
git push origin --delete codex/ci-audit-final
git push origin --delete fix/ci-main-gates-green
git push origin --delete chore/cr-residual-6716-6719
git push origin --delete fix/observability-audit-6686-6691
git push origin --delete ci-cd-audit-fix
git push origin --delete agent/chembl-activity-dataflow-diagrams-consol
git push origin --delete codex/issue-6324-observability-closure
git push origin --delete agent/close-6355-audit-repin
git push origin --delete agent/close-6355-final-drift
git push origin --delete agent/close-6349-mypy-typechecking
git push origin --delete codex/pr6380-rebase
git push origin --delete agent/close-6351-6352-followup
git push origin --delete agent/close-6351-6352-clean
git push origin --delete agent/close-6351-6352-evidence-compatibility
git push origin --delete codex/docker-stability-6293-6300
git push origin --delete codex/close-6288-6289-grafana-isolated
git push origin --delete agent/ai-runtime-6281-6282
git push origin --delete codex/issues-6259-6266
git push origin --delete master
```

---

## Environment Variables (Reference)

These parameters are stored in `.env.local` (not committed to git):

```bash
# Git configuration for commits
GIT_AUTHOR_NAME=Devin AI
GIT_AUTHOR_EMAIL=158243242+devin-ai-integration[bot]@users.noreply.github.com

# SSH Key configuration for GitHub
SSH_PRIVATE_KEY_PATH=~/.ssh/bioetl_github
SSH_PUBLIC_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKwCl/LfRbnPnR065EhV2bV/QRCfDN+A9+sFHlrBVK2o bioetl-devin@github.com
```

---

## Troubleshooting

### SSH Permission Denied

**Error:** `git@github.com: Permission denied (publickey)`

**Solution:**
1. Verify SSH key is added to GitHub
2. Check SSH agent has the key: `ssh-add -l`
3. Test connection: `ssh -T git@github.com`

### SSH Key Not in Agent

**Error:** `Could not open a connection to your authentication agent`

**Solution:**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/bioetl_github
```

### Git Config Not Set

**Error:** Git commits show wrong author

**Solution:**
```bash
git config --global user.name "Devin AI"
git config --global user.email "158243242+devin-ai-integration[bot]@users.noreply.github.com"
```

---

## Security Notes

- **Private key location:** `~/.ssh/bioetl_github` (600 permissions)
- **Public key:** Safe to share (added to this file)
- **SSH config:** Added to `~/.ssh/config`
- **Environment variables:** Stored in `.env.local` (gitignored)

---

## Related Files

- Branch Cleanup Plan: `reports/branch-cleanup-plan-2026-07-31.md`
- Branch Cleanup Results: `reports/branch-cleanup-results-2026-07-31.md`
- Branch Cleanup Issue: #7350
