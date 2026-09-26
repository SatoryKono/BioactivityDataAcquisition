# ChEMBL public observations: contract version 2

The `chembl.assay_parameters` and `chembl.publication_similarity` write contracts
advance to 2.0.0. Existing run reports, Bronze files and v1 published contracts
are retained. Do not rewrite historical evidence or replay a v1 manifest as v2.
New source-bound runs use the new contract identity. Rollback requires the matching
v1 code/configuration and its existing storage snapshot; do not merge v2 rows into
a v1 table merely by changing the version label.

## Assay parameter observations

The public assay API returns an `assay_parameters` list within each assay.
Expand that list before transformation. An empty list means no observations;
an absent or malformed list is invalid evidence and reaches quarantine.
Input CSV filtering selects parent `assay_id` values, not nonexistent API
`assay_param_id` values. The output limit applies after expansion; a separate
50,000-parent / 180-second source-I/O budget bounds sparse scans. Exhausting it
fails explicitly as an incomplete scan.

When no native parameter key exists, derive the local positive int64 key from
`deterministic_uuid("chembl.assay_parameter.observation.v1", row)`, masking to
63 bits (zero maps to one). The row is the parameter payload plus the parent
assay ID. Missing parent/type does not get a generated key. Canonical mapping
serialization makes key order irrelevant. Identical observations deduplicate;
a value change creates a distinct observation, not a claim about the provider's
internal row identity. As with any truncated hash, collisions are theoretically
possible; retain source payloads for diagnosis and never describe this key as a
ChEMBL database surrogate.

Gold uses canonical `parameter_type`, `parameter_relation`, and `parameter_value`
names and validates the key as int64. Float64 coercion could corrupt low bits.

## Publication similarity

The API's `document_1_chembl_id` and `document_2_chembl_id` map to
`publication_id1` and `publication_id2`. Never infer internal `doc_1`/`doc_2`
database foreign keys from their numeric suffixes. A complete legacy internal
pair remains accepted, but a missing pair, half pair or self-pair is rejected.

For a valid public pair without `sim_id`, sort its two identifiers and derive
the positive 63-bit key from the `chembl.publication_similarity.public_pair.v1`
UUID namespace and `{first, second}` payload. Reversing pair order or changing
scores does not change identity. Keep source endpoint orientation in the fields.
Gold keeps the full integer key, and both Silver and Gold enforce complete pairs.
Upstream deduplication uses the actual public pair fields.

## Acceptance

Validate real-shape transformations, empty lists, malformed records, repeated
observations, reversed pairs, offsets/limits, closed source iterators and integer
precision above 2^53. Regenerate published contracts and Silver snapshots using
the canonical generators. Verify physical Silver/Gold, run report and ledger
against a fresh bounded run before closing E06. Local regression success alone
does not satisfy that live acceptance.
