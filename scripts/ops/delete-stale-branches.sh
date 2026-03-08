#!/usr/bin/env bash
# Delete stale and duplicate remote branches
# Generated: 2026-02-20
# Run with: bash scripts/delete-stale-branches.sh
#
# Part 1: 62 branches on outdated base (6000+ commits ahead of main)
# Part 2: 31 duplicate codex branches (keeping canonical version of each task)
# Total: 93 branches to delete

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

deleted=0
failed=0

delete_branch() {
  local branch="$1"
  local reason="$2"
  printf "${YELLOW}Deleting${NC} %-75s [%s] ... " "$branch" "$reason"
  if git push origin --delete "$branch" 2>/dev/null; then
    printf "${GREEN}OK${NC}\n"
    ((deleted++))
  else
    printf "${RED}FAILED${NC}\n"
    ((failed++))
  fi
}

echo "============================================="
echo " Deleting stale and duplicate remote branches"
echo "============================================="
echo ""

# -------------------------------------------------------
# Part 1: Branches on outdated base (6000+ commits ahead)
# -------------------------------------------------------
echo "--- Part 1: Outdated base branches (62) ---"
echo ""

# bolt branches (6 branches)
delete_branch "bolt-optimize-pubmed-date-3789117081982362004" "outdated-base"
delete_branch "bolt-perf-pubmed-date-parsing-12532949572236019825" "outdated-base"
delete_branch "bolt-pubmed-optimization-11776621839494351834" "outdated-base"
delete_branch "bolt-silver-writer-optimization-4078771543740170219" "outdated-base"
delete_branch "bolt/optimize-silver-serialization-17048994287352894847" "outdated-base"
delete_branch "bolt/pubmed-transformer-optimization-1564101723275582547" "outdated-base"

# jules branches (2 branches)
delete_branch "jules-11173321112583947796-657b8aa8" "outdated-base"
delete_branch "jules-17546412591644239142-44ec5546" "outdated-base"

# claude branches on outdated base (35 branches)
delete_branch "claude/analyze-validation-matrix-kFck8" "outdated-base"
delete_branch "claude/audit-analysis-fixes-u9EkK" "outdated-base"
delete_branch "claude/audit-documentation-2U4OL" "outdated-base"
delete_branch "claude/audit-documentation-9AYo8" "outdated-base"
delete_branch "claude/audit-documentation-MJcVu" "outdated-base"
delete_branch "claude/audit-documentation-PM9XH" "outdated-base"
delete_branch "claude/audit-documentation-jCzxu" "outdated-base"
delete_branch "claude/bioetl-architecture-audit-nttXM" "outdated-base"
delete_branch "claude/chembl-activity-silver-layer-NUL41" "outdated-base"
delete_branch "claude/code-inventory-audit-prompt-WYRi3" "outdated-base"
delete_branch "claude/collect-publication-types-dmJuX" "outdated-base"
delete_branch "claude/consolidate-architecture-audits-EyVt3" "outdated-base"
delete_branch "claude/consolidate-data-paths-fixes-PH1x6" "outdated-base"
delete_branch "claude/debug-uniprot-idmapping-byhJj" "outdated-base"
delete_branch "claude/document-pipeline-validation-cZ1Ai" "outdated-base"
delete_branch "claude/fix-bioactivity-import-Z4YR2" "outdated-base"
delete_branch "claude/fix-bioetl-audit-NnpMx" "outdated-base"
delete_branch "claude/fix-bronze-dependencies-api-gYTeE" "outdated-base"
delete_branch "claude/fix-cli-command-example-Zn8yy" "outdated-base"
delete_branch "claude/fix-data-paths-guides-LM3On" "outdated-base"
delete_branch "claude/fix-data-paths-guides-rRanJ" "outdated-base"
delete_branch "claude/fix-factory-type-mismatch-Gycy6" "outdated-base"
delete_branch "claude/fix-mypy-strict-errors-Nn92N" "outdated-base"
delete_branch "claude/fix-pubmed-pii-security-NtpcU" "outdated-base"
delete_branch "claude/inventory-code-duplication-z4DSx" "outdated-base"
delete_branch "claude/inventory-duplicate-detection-k8gol" "outdated-base"
delete_branch "claude/publication-validation-analysis-QG4pB" "outdated-base"
delete_branch "claude/publication-validation-analysis-QUOBW" "outdated-base"
delete_branch "claude/publication-validation-analysis-olBBu" "outdated-base"
delete_branch "claude/refactor-bioetl-config-f14LT" "outdated-base"
delete_branch "claude/remove-dead-events-BEFKQ" "outdated-base"
delete_branch "claude/replace-executor-classes-VHoxN" "outdated-base"
delete_branch "claude/schema-drift-documentation-cnkdv" "outdated-base"
delete_branch "claude/standardize-publication-types-Ti3Vm" "outdated-base"
delete_branch "claude/update-code-audit-report-aOveE" "outdated-base"

# codex branches on outdated base (19 branches)
delete_branch "codex/align-code-to-rules-or-update-documentation" "outdated-base"
delete_branch "codex/audit-bioetl-configuration-structure" "outdated-base"
delete_branch "codex/audit-bioetl-configuration-structure-9sa4bf" "outdated-base"
delete_branch "codex/audit-bioetl-configuration-structure-shrax7" "outdated-base"
delete_branch "codex/audit-composite-target-and-fix-errors" "outdated-base"
delete_branch "codex/audit-recent-branches-for-correctness-and-errors" "outdated-base"
delete_branch "codex/conduct-comprehensive-documentation-audit" "outdated-base"
delete_branch "codex/fix-data-paths-in-guides" "outdated-base"
delete_branch "codex/fix-data-paths-in-guides-c2u4ii" "outdated-base"
delete_branch "codex/fix-data-paths-in-guides-izi1v9" "outdated-base"
delete_branch "codex/refactor-lookup_methods-in-openalex.py" "outdated-base"
delete_branch "codex/refactor-semanticscholar-and-pubchem-constants" "outdated-base"
delete_branch "codex/refactor-semanticscholar-extractors" "outdated-base"
delete_branch "codex/remove-dead-event-classes-from-events.py" "outdated-base"
delete_branch "codex/remove-dead-event-classes-from-events.py-xtyvm3" "outdated-base"
delete_branch "codex/remove-duplicate-pipeline-classes" "outdated-base"
delete_branch "codex/remove-openalexpublicationrecord-and-clean-up-imports" "outdated-base"
delete_branch "codex/remove-unused-classes-from-dq_report.py" "outdated-base"
delete_branch "codex/review-recent-branches-and-merge-changes" "outdated-base"
delete_branch "codex/review-recent-branches-and-merge-changes-vayd82" "outdated-base"

echo ""

# -------------------------------------------------------
# Part 2: Duplicate codex branches (keeping canonical)
# -------------------------------------------------------
echo "--- Part 2: Duplicate codex branches (31) ---"
echo "(Keeping the canonical/base version of each task)"
echo ""

# conduct-architectural-audit-for-bioetl: keep base, delete 9 duplicates
delete_branch "codex/conduct-architectural-audit-for-bioetl-0d72iw" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-267bw6" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-a9um58" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-bjpj6f" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-ek16yo" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-ekp0my" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-jciscn" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-px0bxe" "dup:audit"
delete_branch "codex/conduct-architectural-audit-for-bioetl-t4pr4g" "dup:audit"

# conduct-code-inventory-and-duplication-audit: keep base, delete 3
delete_branch "codex/conduct-code-inventory-and-duplication-audit-3c56mh" "dup:inventory"
delete_branch "codex/conduct-code-inventory-and-duplication-audit-7h7iyr" "dup:inventory"
delete_branch "codex/conduct-code-inventory-and-duplication-audit-b4wzwo" "dup:inventory"

# conduct-data-schema-audit-for-bioetl-pipelines: keep base, delete 2
delete_branch "codex/conduct-data-schema-audit-for-bioetl-pipelines-oaswve" "dup:schema-audit"
delete_branch "codex/conduct-data-schema-audit-for-bioetl-pipelines-pbn8h6" "dup:schema-audit"

# conduct-data-schema-audit-for-pipelines: keep base, delete 3
delete_branch "codex/conduct-data-schema-audit-for-pipelines-e8duku" "dup:schema-audit"
delete_branch "codex/conduct-data-schema-audit-for-pipelines-hqg4s2" "dup:schema-audit"
delete_branch "codex/conduct-data-schema-audit-for-pipelines-wkhju1" "dup:schema-audit"

# create-architectural-change-plan-for-bioetl: keep base, delete 3
delete_branch "codex/create-architectural-change-plan-for-bioetl-6v6zla" "dup:arch-plan"
delete_branch "codex/create-architectural-change-plan-for-bioetl-8x3vzl" "dup:arch-plan"
delete_branch "codex/create-architectural-change-plan-for-bioetl-f7msdt" "dup:arch-plan"

# refactor-bioetl-configuration-structure: keep base, delete 4
delete_branch "codex/refactor-bioetl-configuration-structure-3i5df9" "dup:config-refactor"
delete_branch "codex/refactor-bioetl-configuration-structure-3znbpy" "dup:config-refactor"
delete_branch "codex/refactor-bioetl-configuration-structure-dwe5go" "dup:config-refactor"
delete_branch "codex/refactor-bioetl-configuration-structure-jl7hsb" "dup:config-refactor"

# unify-dto-field-names-in-chembl.py: keep base, delete 6
delete_branch "codex/unify-dto-field-names-in-chembl.py-1ikmoz" "dup:dto-unify"
delete_branch "codex/unify-dto-field-names-in-chembl.py-6s96sh" "dup:dto-unify"
delete_branch "codex/unify-dto-field-names-in-chembl.py-8j7752" "dup:dto-unify"
delete_branch "codex/unify-dto-field-names-in-chembl.py-by4p6i" "dup:dto-unify"
delete_branch "codex/unify-dto-field-names-in-chembl.py-ix6wjf" "dup:dto-unify"
delete_branch "codex/unify-dto-field-names-in-chembl.py-mwmn9z" "dup:dto-unify"

# conduct-comprehensive-documentation-audit: keep nothing (base in outdated), delete suffix
delete_branch "codex/conduct-comprehensive-documentation-audit-h810m4" "dup:doc-audit"

echo ""
echo "============================================="
printf "Done. ${GREEN}Deleted: %d${NC}, ${RED}Failed: %d${NC}\n" "$deleted" "$failed"
echo "============================================="
