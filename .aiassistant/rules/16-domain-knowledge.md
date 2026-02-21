# 16. Bioinformatics Domain Knowledge (Skill: Bioinformatics Domain)

## Overview
This document formalizes the domain knowledge required for the BioETL project. All agents must adhere to these definitions and relationships when implementing logic, naming variables, or designing schemas.

## Core Entities

### 1. Target (Мишень)
A biological molecule (usually a protein) to which a drug binds.
-   **Identifiers**: UniProt ID (Primary), ChEMBL Target ID, Gene Name.
-   **Relationships**: Has many Bioactivities. Can belong to a Protein Family.
-   **Key Attributes**: Organism, Sequence, Type (Single Protein, Protein Complex).

### 2. Compound (Соединение)
A chemical substance being tested.
-   **Identifiers**: ChEMBL Molecule ID (Primary), PubChem CID, InChIKey (Critical for deduplication).
-   **Structure**: SMILES (Simplified Molecular Input Line Entry System), InChI.
-   **Key Attributes**: Molecular Weight, LogP, Num Ro5 Violations.
-   **Normalization**: All SMILES must be canonicalized using RDKit before storage.

### 3. Bioactivity (Биоактивность)
The quantitative measure of the interaction between a Compound and a Target.
-   **Types**: IC50 (Inhibitory Concentration), EC50 (Effective Concentration), Ki (Inhibition Constant), Kd (Dissociation Constant).
-   **Units**: nM (nanomolar) is the standard unit. All values (uM, mM) must be converted to nM.
-   **pChembl Value**: -log10(molar IC50/EC50/Ki/Kd). Used for normalization. Values > 6 are generally considered active.
-   **Context**: Must include Assay details (Conditions, Organism).

### 4. Assay (Анализ/Тест)
The experimental procedure used to measure Bioactivity.
-   **Attributes**: Description, Type (Binding, Functional), Organism, Tissue/Cell Line.
-   **Confidence Score**: ChEMBL confidence score (0-9). Only assays with score >= 7 should be used for high-quality models.

### 5. Publication (Публикация)
The source of the data.
-   **Identifiers**: PubMed ID (PMID), DOI.
-   **Attributes**: Title, Abstract, Year, Journal, Authors.

## Domain Logic & Validation Rules

1.  **Activity Conversion**:
    -   If unit is `uM`, multiply value by 1000 to get `nM`.
    -   If unit is `mM`, multiply by 1,000,000.
    -   If operator is `>` (greater than), the value is censored (inactive/low potency).

2.  **Target Mapping**:
    -   Always prefer UniProt ID for targets.
    -   Map ChEMBL Target ID -> UniProt ID using the mapping file/API.

3.  **Compound Standardization**:
    -   Use InChIKey as the primary deduplication key for compounds.
    -   Salt stripping is required (remove HCl, Na+, etc. from SMILES).

## Common Acronyms
-   **SAR**: Structure-Activity Relationship.
-   **ADME**: Absorption, Distribution, Metabolism, Excretion.
-   **HTS**: High-Throughput Screening.
-   **MOA**: Mechanism of Action.
