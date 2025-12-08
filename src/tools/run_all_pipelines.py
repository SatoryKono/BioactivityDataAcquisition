from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from bioetl.interfaces.observability import LoggingPortABC
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.interfaces.cli.app import app

# Pipeline dependency order
PIPELINES = [
    "assay_chembl",
    "activity_chembl",
    "target_chembl",
    "document_chembl",
    "molecule_chembl",
]


def run_pipeline(name: str, limit: int, logger: LoggingPortABC) -> dict:
    start_time = datetime.now(timezone.utc)
    entity = name.split("_")[0]
    pipeline_logger = logger.apply_bind(pipeline=name, entity=entity, stage="run")

    pipeline_logger.info("Starting pipeline")

    # Mock args
    # Assume config path: {entity}_chembl -> configs/pipelines/chembl/{entity}.yaml
    config_path = f"configs/pipelines/chembl/{entity}.yaml"
    output_path = f"data/output/{entity}"

    sys.argv = [
        "bioetl",
        "run",
        name,
        "--config",
        config_path,
        "--output",
        output_path,
        "--limit",
        str(limit),
    ]

    success = False
    error = None

    try:
        app()
        success = True
    except SystemExit as e:
        if e.code != 0:
            success = False
            error = f"Exit code {e.code}"
        else:
            success = True
    except Exception as e:
        success = False
        error = str(e)

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    pipeline_logger.info(
        "Pipeline finished",
        success=success,
        duration_sec=duration,
        error=error,
        finished_at=end_time.isoformat(),
    )

    return {
        "name": name,
        "success": success,
        "duration_sec": duration,
        "error": error,
        "timestamp": end_time.isoformat(),
    }


def main():
    logger = default_logger().apply_bind(
        pipeline="chembl_all", entity="chembl", stage="runner"
    )

    # Ensure report dir
    report_dir = Path("reports/chembl_all")
    report_dir.mkdir(parents=True, exist_ok=True)

    limit = 100
    results = []
    batch_start = datetime.now(timezone.utc)

    logger.info(
        "Running all ChEMBL pipelines", limit=limit, started_at=batch_start.isoformat()
    )

    for name in PIPELINES:
        res = run_pipeline(name, limit, logger)
        results.append(res)
        if not res["success"]:
            logger.error(
                "Pipeline failed, stopping sequence",
                pipeline=name,
                entity=name.split("_")[0],
                stage="run",
                error=res.get("error"),
            )
            break

    # Generate report
    summary_path = report_dir / "summary.md"
    qc_path = report_dir / "qc.json"
    batch_end = datetime.now(timezone.utc)
    batch_duration = (batch_end - batch_start).total_seconds()

    summary_metrics = {
        "started_at": batch_start.isoformat(),
        "finished_at": batch_end.isoformat(),
        "duration_sec": batch_duration,
        "pipelines_total": len(results),
        "pipelines_succeeded": sum(1 for r in results if r["success"]),
        "pipelines_failed": sum(1 for r in results if not r["success"]),
        "report_path": str(summary_path),
    }

    # Write QC JSON
    with open(qc_path, "w") as f:
        json.dump({"metrics": summary_metrics, "pipelines": results}, f, indent=2)

    # Write Summary MD
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# ChEMBL Pipelines Execution Report\n\n")
        f.write(f"**Date:** {batch_start.isoformat()}\n")
        f.write(f"**Limit:** {limit}\n\n")
        f.write("| Pipeline | Status | Duration (s) | Error |\n")
        f.write("|----------|--------|--------------|-------|\n")
        for r in results:
            status = "OK" if r["success"] else "FAIL"
            err = r["error"] if r["error"] else "-"
            f.write(f"| {r['name']} | {status} | {r['duration_sec']:.2f} | {err} |\n")

    logger.info(
        "Batch finished",
        stage="report",
        **summary_metrics,
        summary_path=str(summary_path),
        qc_path=str(qc_path),
    )


if __name__ == "__main__":
    main()
