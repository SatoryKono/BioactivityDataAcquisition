---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-12'
---

# Neo4j Project Memory - Example Q&A Pairs

## Architecture Questions

**Q: What architecture does BioETL use?**
A: BioETL uses Hexagonal Architecture with Ports and Adapters, Medallion Architecture (Bronze→Silver→Gold layers), and follows a Local-Only runtime policy with five layers: domain, application, infrastructure, composition, and interfaces.

**Q: What are the architectural invariants in BioETL?**
A: Key invariants:
- Domain must not perform I/O
- Application must not import infrastructure
- Composition is the composition root
- Interfaces are boundary entrypoints
- Infrastructure may implement domain ports

## Runtime & Bootstrap

**Q: How does PipelineRunner orchestrate execution?**
A: PipelineRunner manages the pipeline lifecycle with PreflightService (validates infrastructure/medallion policy), PostrunService (handles DQ, reports, compaction, vacuum), and PipelineService (injected service bundle).

**Q: Where is the main runtime bootstrap entrypoint?**
A: `composition/bootstrap/runtime/pipeline.py` is the main entrypoint. `runtime_builders` prepares runner inputs, observability, and control-plane attachments.

## Neo4j Memory Setup

**Q: How to connect to Neo4j memory backend from WSL?**
A: Use `bolt://host.docker.internal:7687` in WSL. The Docker container name is `bioetl-neo4j`.

**Q: What are the default Neo4j credentials?**
A: Username: `neo4j`, Password: `bioetl_secure_password` (from `NEO4J_AUTH=neo4j/bioetl_secure_password`).

**Q: How to verify Neo4j MCP setup?**
A: Run:
```bash
codex mcp get neo4j-memory
bash scripts/memory/mcp/check.sh
```

## Provider Knowledge

**Q: What providers does BioETL support?**
A: ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, Semantic Scholar.

**Q: What are ChEMBL's characteristics?**
A: Public auth, offset pagination, CHEMBL identifiers, primary source for activity, assay, molecule, target, and publication entities.

**Q: How does PubMed handle fallback semantics?**
A: PubMed uses API key + email auth, offset pagination, PMID identity, and supports PMID or title fallback.

## Configuration

**Q: Where are provider entity configs located?**
A: `configs/entities/{provider}/{entity}.yaml`

**Q: Where are composite configs stored?**
A: `configs/composites/{entity}.yaml`

**Q: What handles YAML loading?**
A: `infrastructure.config` is the canonical owner for YAML loading and normalization.

## Operational Memory

**Q: How to start Neo4j backend?**
A:
```bash
docker run -d --name bioetl-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bioetl_secure_password \
  neo4j:5.15-community
```

**Q: How to access Neo4j Browser?**
A: http://localhost:7474/browser/ with credentials neo4j/bioetl_secure_password

**Q: What environment variables does the MCP wrapper use?**
A:
- `NEO4J_URI` (default: bolt://localhost:7687)
- `NEO4J_USERNAME` (parsed from NEO4J_AUTH)
- `NEO4J_PASSWORD` (parsed from NEO4J_AUTH)
- `NEO4J_DATABASE` (default: neo4j)

## Domain Model

**Q: What are the main domain families?**
A: Ports, value_objects, entities, aggregates, services, schemas, validation, mapping, config, types, exceptions, registry, filtering, transformations, control_plane, composite, lineage.

**Q: What are the core aggregates?**
A:
- PipelineRun (execution lifecycle)
- RunManifest (immutable provenance)
- RunLedgerEntry (control-plane events)
- QuarantineEntry (quarantined data)
- PipelineConfig (immutable config)

**Q: What are canonical identifiers?**
A: ChemblId, DOI, PubMedId, OpenAlexId, SemanticScholarId, PubChemCid, UniProtId, InChIKey, SMILES, TaxonomyId.

## Validation & Retrieval

**Q: How to test Neo4j memory retrieval?**
A: Example prompts:
```
@neo4j-memory что ты знаешь про архитектуру BioETL?
@neo4j-memory как в BioETL собирается runtime для PipelineRunner?
@neo4j-memory как подключаться к Neo4j memory backend из WSL?
@neo4j-memory какие domain families и core aggregates определены?
```

**Q: What are the memory update rules?**
A:
- Save only long-lived facts
- Don't store transient logs/errors
- Update memory after merge, not during experiments
- Fix source if fact contradicts agent-memory.md/RULES.md/ADRs
