#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/memory/prompts/print_seed.sh [all|architecture|runtime|providers|operations|domain]

Prints ready-to-paste @neo4j-memory prompts for seeding BioETL project memory.
EOF
}

phase="${1:-all}"

print_architecture() {
  cat <<'EOF'
@neo4j-memory создай базовую память проекта BioETL и сохрани факты:
- BioETL is a Python ETL framework for bioactivity data acquisition.
- BioETL uses Hexagonal Architecture with Ports and Adapters.
- BioETL uses Medallion Architecture with Bronze, Silver, and Gold layers.
- BioETL follows a Local-Only runtime policy.
- BioETL has five runtime layers: domain, application, infrastructure, composition, interfaces.
- Silver layer must use Delta Lake.
- Pandera is used for dataframe validation.

Свяжи эти факты с проектом BioETL и покажи краткое summary сохранённого.
EOF
}

print_runtime() {
  cat <<'EOF'
@neo4j-memory сохрани execution and bootstrap memory для BioETL:
- PipelineRunner orchestrates pipeline lifecycle.
- PreflightService validates infrastructure and medallion policy before execution.
- PostrunService handles DQ, reports, compaction, and vacuum.
- PipelineService is the injected service bundle for runtime execution.
- composition/bootstrap/runtime/pipeline.py is the main runtime bootstrap entrypoint.
- runtime_builders prepares runner inputs, observability, and control-plane attachments.
- composition/bootstrap/runtime/composite.py bootstraps composite execution.
- runner_assembly builds composite runner dependency bundles.

Свяжи bootstrap entrypoints, runtime builders, and execution services.
EOF
}

print_providers() {
  cat <<'EOF'
@neo4j-memory сохрани provider and config facts for BioETL:
- BioETL providers are ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, and Semantic Scholar.
- ProviderRegistry keeps deterministic provider and pipeline registration state.
- ensure_providers_loaded is the canonical provider loading boundary.
- provider entity configs live under configs/entities/{provider}/{entity}.yaml.
- composite configs live under configs/composites/{entity}.yaml.
- infrastructure.config is the canonical owner for YAML loading and normalization.

Создай связи между provider inventory, config surface, and runtime registration.
EOF
}

print_operations() {
  cat <<'EOF'
@neo4j-memory сохрани operational facts for BioETL:
- neo4j-memory MCP is registered in Codex through scripts/memory/mcp/wrapper.sh.
- the wrapper runs @knowall-ai/mcp-neo4j-agent-memory@0.2.5.
- in WSL, Neo4j is accessed via bolt://host.docker.internal:7687.
- Docker container name is bioetl-neo4j.
- .env provides base local overrides.
- .env.local provides machine-specific overrides.
- shell-provided env vars override repo env files.
- docs/00-project/ai/memory/agent-memory.md is the human project memory entry point.

Свяжи эти факты как operational memory for BioETL.
EOF
}

print_domain() {
  cat <<'EOF'
@neo4j-memory сохрани domain model and provider semantics for BioETL:
- the domain layer contains the semantic model and must remain pure with no concrete I/O.
- main domain families are ports, value_objects, entities, aggregates, services, schemas, validation, mapping, config, types, exceptions, registry, filtering, transformations, control_plane, composite, and lineage.
- PipelineRun is the aggregate root for pipeline execution lifecycle tracking.
- RunManifest is the immutable provenance snapshot for one launched run.
- RunLedgerEntry is the append-only control-plane event linked to one manifest/run pair.
- QuarantineEntry is the aggregate for quarantined data and its resolution lifecycle.
- PipelineConfig is the immutable pipeline configuration object.
- MedallionPolicy and LoadingStrategy are domain policy objects.
- canonical identifier concepts include ChemblId, DOI, PubMedId, OpenAlexId, SemanticScholarId, PubChemCid, UniProtId, InChIKey, SMILES, and TaxonomyId.
- ChEMBL uses public auth with offset pagination and CHEMBL identifiers as primary upstream identity.
- PubChem uses public auth with offset pagination and PubChem CID identity for compound enrichment.
- PubMed uses api_key plus email auth with offset pagination and PMID identity.
- CrossRef uses email auth with cursor pagination and DOI identity.
- OpenAlex uses email auth with cursor pagination and OpenAlexId identity.
- Semantic Scholar uses api_key auth with offset pagination and SemanticScholarId identity.
- UniProt uses api_key auth with offset pagination and UniProt accession identity.

Свяжи domain families, core concepts, canonical identifiers, and provider semantics с проектом BioETL.
EOF
}

case "$phase" in
  all)
    print_architecture
    printf '\n\n'
    print_runtime
    printf '\n\n'
    print_providers
    printf '\n\n'
    print_operations
    printf '\n\n'
    print_domain
    ;;
  architecture)
    print_architecture
    ;;
  runtime)
    print_runtime
    ;;
  providers)
    print_providers
    ;;
  operations)
    print_operations
    ;;
  domain)
    print_domain
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
