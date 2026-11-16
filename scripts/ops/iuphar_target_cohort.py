"""Freeze an explicit normalized target conversion or role-aware Stage-0 bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bioetl.infrastructure.adapters.iuphar.cohort_builder import (
    ARROW_SOURCE_FORMAT,
    CSV_SOURCE_FORMAT,
    NORMALIZED_TARGET_SCHEMA,
    CohortExportRequest,
    export_canonical_cohort,
)
from iuphar_target_class.stage0.models import ProvenanceClaim
from iuphar_target_class.stage0.v2 import (
    Stage0MaterialV2,
    Stage0V2Request,
    publish_stage0_v2,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    export = actions.add_parser(
        "export", help="Convert a confirmed normalized Silver snapshot"
    )
    export.add_argument("--source", type=Path, required=True)
    export.add_argument("--source-sha256", required=True)
    export.add_argument(
        "--source-format",
        choices=(CSV_SOURCE_FORMAT, ARROW_SOURCE_FORMAT),
        required=True,
    )
    export.add_argument(
        "--source-schema-version", choices=(NORMALIZED_TARGET_SCHEMA,), required=True
    )
    export.add_argument("--mapping-approval-reference", required=True)
    export.add_argument("--environment", required=True)
    export.add_argument("--direct-iuphar-id-column")
    export.add_argument("--output-dir", type=Path, required=True)
    stage = actions.add_parser(
        "stage0", help="Publish a new V2 cohort/evidence occurrence"
    )
    stage.add_argument("--request", type=Path, required=True)
    stage.add_argument("--repo-root", type=Path, required=True)
    stage.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "export":
        result = export_canonical_cohort(
            CohortExportRequest(
                args.source,
                args.source_sha256,
                args.source_format,
                args.source_schema_version,
                args.mapping_approval_reference,
                args.environment,
                direct_iuphar_id_column=args.direct_iuphar_id_column,
            ),
            output_dir=args.output_dir,
        )
        print(
            json.dumps(
                {
                    "canonical_sha256": result.canonical_sha256,
                    "raw_sha256": result.raw_sha256,
                    "conversion_ledger_sha256": result.conversion_ledger_sha256,
                    "rows": len(result.row_ids),
                    "biological_accuracy_accepted": False,
                }
            )
        )
    else:
        _publish_stage_request(args)
    return 0


def _publish_stage_request(args: argparse.Namespace) -> None:
    # The strict dataclass constructors and publisher validate the JSON boundary.
    document = json.loads(args.request.read_bytes())
    request = Stage0V2Request(
        document["cohort_id"],
        document["approval_reference"],
        document["environment"],
        tuple(Stage0MaterialV2(**row) for row in document["materials"]),
        tuple(ProvenanceClaim(**row) for row in document.get("provenance_claims", [])),
    )
    path = publish_stage0_v2(
        request, repo_root=args.repo_root, output_dir=args.output_dir
    )
    print(
        json.dumps(
            {
                "stage0_manifest": str(path),
                "schema_version": 2,
                "biological_accuracy_accepted": False,
            }
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
